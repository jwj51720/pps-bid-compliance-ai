#!/usr/bin/env python3
"""Diagnose EXP123 errors without deriving a new decision rule.

The submitted EXP123 labels are exactly EXP120's model output with the three
versioned source-complete replacements in ``src.frozen_rules``.  This audit
reconstructs that policy, then uses gold evidence only after prediction to ask
whether an FN fact was visible in the exact 4k organizer context.

It does not emit prompt text, route a notice, or make a prediction.  The
report is an admission input for a future multi-call experiment, not a source
of item-level overrides.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data import load_decision_cards, load_item_table, load_records
from src.evaluate import evaluate_submission
from src.frozen_rules import apply_exp123_frozen_rules
from src.prompt import build_official_baseline_context
from src.prompt_observability import audit_prompt_observability
from src.schema import ITEMS, SUBMISSION_COLUMNS


def reconstruct_exp123_rows(
    model_rows: list[dict[str, str]], records_by_id: dict[str, dict[str, Any]]
) -> list[dict[str, str]]:
    """Apply only EXP123's three archived replacements to an EXP120 CSV."""
    result: list[dict[str, str]] = []
    for row in model_rows:
        judgment = {
            item: {
                "위반여부": int(row[item]),
                "근거문구": row[f"e{index}"],
            }
            for index, item in enumerate(ITEMS, 1)
        }
        corrected = apply_exp123_frozen_rules(records_by_id[row["id"]], judgment)
        output = dict(row)
        for index, item in enumerate(ITEMS, 1):
            output[item] = str(corrected[item]["위반여부"])
            output[f"e{index}"] = str(corrected[item]["근거문구"])
        result.append(output)
    return result


def audit_failure_modes(
    records: list[dict[str, Any]],
    labels: list[dict[str, str]],
    predictions: list[dict[str, str]],
    context_chars: int,
) -> dict[str, Any]:
    """Classify errors by pre-existing context observability, after scoring."""
    labels_by_id = {row["id"]: row for row in labels}
    predictions_by_id = {row["id"]: row for row in predictions}
    observability = audit_prompt_observability(records, labels_by_id, context_chars)
    positive_status = {
        (row["id"], row["item"]): row["observability"]
        for row in observability["rows"]
    }
    per_item: dict[str, Counter[str]] = {item: Counter() for item in ITEMS}
    examples: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    for record in records:
        record_id = record["id"]
        gold = labels_by_id[record_id]
        predicted = predictions_by_id[record_id]
        for item in ITEMS:
            gold_value = int(gold[item])
            predicted_value = int(predicted[item])
            if gold_value == predicted_value:
                per_item[item]["correct"] += 1
                continue
            if gold_value == 1:
                status = positive_status.get((record_id, item), "unclassified_positive")
                bucket = f"fn_{status}"
            else:
                # A negative row has no gold source span.  Do not pretend this
                # audit can establish whether an FP was caused by omitted text.
                bucket = "fp_no_gold_source_to_classify"
            per_item[item][bucket] += 1
            if len(examples[item][bucket]) < 5:
                examples[item][bucket].append(record_id)

    totals: Counter[str] = Counter()
    for values in per_item.values():
        totals.update(values)
    return {
        "scope": {
            "records": len(records),
            "context_chars": context_chars,
            "policy": "EXP120 model output plus archived EXP123 v2/v3/v21 replacements",
            "label_usage": "post-hoc error classification only",
        },
        "overall": dict(totals),
        "per_item": {item: dict(per_item[item]) for item in ITEMS},
        "examples": {item: dict(values) for item, values in examples.items()},
    }


def markdown(report: dict[str, Any], metric: float) -> str:
    lines = [
        "# EXP123 오류 형태 감사 v1",
        "",
        "이 감사는 EXP120의 dev-200 V/E 출력을 EXP123의 archived v2/v3/v21 "
        "source-complete replacement로만 교체하여 재구성한 뒤 수행했다.",
        "Gold label/evidence는 예측·routing·card·rule을 만들지 않고, 오류가 난 뒤 "
        "4,000자 context에 gold source가 보였는지를 분류하는 데만 사용했다.",
        "",
        f"- 재구성 Macro positive-F1: `{metric:.6f}` (기록된 EXP123 local `0.317797`과 일치해야 함)",
        "- `fn_source_visible`: gold evidence가 실제 4k context에 있었는데 놓친 경우다. "
        "문서 확장보다 판정/attention 분리 가설의 후보다.",
        "- `fn_source_outside_4k`: gold evidence가 실제 context 밖에 있었던 경우다. "
        "이 수치만으로 문서 split을 채택하지 않으며, runtime·품질을 별도로 검증해야 한다.",
        "- `fn_absence_requires_full_scope`: 첨부문서가 omitted 되어 whole-notice 부재를 "
        "판정할 수 없었던 경우다.",
        "- `fn_positive_without_gold_evidence`: dev gold에 location evidence가 없어 이 감사만으로 "
        "문서 가시성을 판정할 수 없는 경우다.",
        "- FP에는 gold source가 없으므로 이 감사는 원인을 단정하지 않는다.",
        "",
        "## 전체 오류 형태",
        "",
    ]
    for key, value in sorted(report["overall"].items()):
        lines.append(f"- {key}: {value}")
    lines.extend([
        "",
        "## 항목별 오류 형태",
        "",
        "| item | visible FN | outside FN | absence-scope FN | no-evidence FN | FP |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for item in ITEMS:
        row = report["per_item"][item]
        lines.append(
            f"| {item} | {row.get('fn_source_visible', 0)} | "
            f"{row.get('fn_source_outside_4k', 0)} | "
            f"{row.get('fn_absence_requires_full_scope', 0)} | "
            f"{row.get('fn_positive_without_gold_evidence', 0)} | "
            f"{row.get('fp_no_gold_source_to_classify', 0)} |"
        )
    lines.extend(["", "## 해석 경계", ""])
    lines.extend([
        "- 이 표의 v별 수치를 card 문구나 Python rule로 바꾸지 않는다.",
        "- 다중 호출 후보는 source-visible FN과 source-outside/absence-scope FN을 "
        "서로 다른 문제로 취급해야 한다.",
        "- 이후 triage/locator의 `해당없음` 종료는 이 감사의 FN coverage를 별도 "
        "측정하기 전에는 허용하지 않는다.",
    ])
    return "\n".join(lines) + "\n"


def visible_fn_review(
    records: list[dict[str, Any]],
    labels: list[dict[str, str]],
    predictions: list[dict[str, str]],
    cards: dict[str, dict[str, Any]],
    context_chars: int,
) -> str:
    """Render compact human review cases where a gold source was visible."""
    labels_by_id = {row["id"]: row for row in labels}
    predictions_by_id = {row["id"]: row for row in predictions}
    observability = audit_prompt_observability(records, labels_by_id, context_chars)
    rows = sorted(
        (
            row for row in observability["rows"]
            if row["observability"] == "source_visible"
            and int(predictions_by_id[row["id"]][row["item"]]) == 0
        ),
        key=lambda row: (int(row["item"][1:]), row["id"]),
    )
    records_by_id = {record["id"]: record for record in records}
    lines = [
        "# EXP123 4k 안 source-visible FN 검토",
        "",
        "아래 사례는 gold evidence가 실제 organizer-format 4,000자 context에 포함됐지만, "
        "EXP123 재구성 예측이 0이었던 경우다. Gold 정보는 사후 분석용이며 이 문서를 "
        "다음 prompt/card/rule 입력으로 사용하지 않는다.",
        "",
    ]
    for row in rows:
        record = records_by_id[row["id"]]
        context = build_official_baseline_context(record, context_chars)
        evidence = row["gold_evidence"]
        start = context.find(evidence)
        excerpt = context[max(0, start - 240): start + len(evidence) + 240]
        predicted = predictions_by_id[row["id"]]
        index = int(row["item"][1:])
        lines.extend([
            f"## {row['id']} / {row['item']}",
            "",
            f"- 카드: {cards[row['item']]['prompt_text']}",
            f"- gold evidence: `{evidence}`",
            f"- model prediction: v={predicted[row['item']]}, e=`{predicted[f'e{index}']}`",
            "- 실제 4k 문맥의 주변 원문:",
            "",
            "```text",
            excerpt,
            "```",
            "",
        ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model-predictions",
        default="outputs/exp-120-official-baseline-card-v6-full200/submission.csv",
    )
    parser.add_argument("--records", default="data/raw/open/dev.jsonl.gz")
    parser.add_argument("--labels", default="data/raw/open/dev_labels.csv")
    parser.add_argument("--item-table", default="data/raw/open/data/항목표.json")
    parser.add_argument("--cards", default="data/derived/decision_cards_v6.json")
    parser.add_argument("--context-chars", type=int, default=4000)
    parser.add_argument("--output-dir", default="outputs/exp123-failure-modes-v1")
    args = parser.parse_args()

    records = load_records(args.records)
    records_by_id = {record["id"]: record for record in records}
    with Path(args.model_predictions).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or tuple(rows[0]) != SUBMISSION_COLUMNS:
        raise ValueError("model predictions must be a valid organizer-format submission CSV")
    with Path(args.labels).open(encoding="utf-8", newline="") as handle:
        labels = list(csv.DictReader(handle))
    item_table = load_item_table(args.item_table)
    cards = load_decision_cards(args.cards, item_table)

    predictions = reconstruct_exp123_rows(rows, records_by_id)
    destination = Path(args.output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    prediction_path = destination / "exp123_reconstructed_submission.csv"
    with prediction_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUBMISSION_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(predictions)
    metrics, _, _ = evaluate_submission(prediction_path, args.labels, records)
    report = audit_failure_modes(records, labels, predictions, args.context_chars)
    report["metric"] = metrics["leaderboard_metric"]
    (destination / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (destination / "report.md").write_text(
        markdown(report, float(metrics["leaderboard_metric"]["macro_f1"])), encoding="utf-8"
    )
    (destination / "source_visible_fn_review.md").write_text(
        visible_fn_review(records, labels, predictions, cards, args.context_chars),
        encoding="utf-8",
    )
    print(destination / "report.md")
    print(json.dumps(report["overall"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
