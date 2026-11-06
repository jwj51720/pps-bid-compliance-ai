"""Decompose EXP172 dev-200 errors into pass, merge, and frozen-rule effects.

This is an offline diagnostic only: it reads an already completed prediction
checkpoint and gold labels.  It makes no pipeline policy change and must not
be used to choose a submission output.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.schema import ABSENCE_ITEMS, ITEMS

FROZEN_ITEMS = frozenset({"v2", "v3", "v21"})


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def read_csv(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {row["id"]: row for row in csv.DictReader(handle)}


def metric(gold: list[int], pred: list[int]) -> dict[str, float | int]:
    tp = sum(g == 1 and p == 1 for g, p in zip(gold, pred))
    fp = sum(g == 0 and p == 1 for g, p in zip(gold, pred))
    fn = sum(g == 1 and p == 0 for g, p in zip(gold, pred))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "gold_positive": sum(gold), "predicted_positive": sum(pred),
        "tp": tp, "fp": fp, "fn": fn, "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
    }


def labels_for(row: dict[str, Any], mode: str) -> dict[str, int]:
    passes = row["pass_judgments"]
    if not passes:
        raise ValueError(f"{row['id']}: no pass judgments")
    result: dict[str, int] = {}
    for item in ITEMS:
        values = [int(value[item]["위반여부"]) for value in passes]
        if mode == "first":
            result[item] = values[0]
        elif mode == "or":
            result[item] = int(any(values))
        elif mode == "and":
            result[item] = int(all(values))
        elif mode == "policy_raw":
            result[item] = int(all(values)) if item in ABSENCE_ITEMS else int(any(values))
        elif mode == "actual":
            result[item] = int(row["judgment"][item]["위반여부"])
        else:
            raise ValueError(mode)
    return result


def macro(gold_by_id: dict[str, dict[str, str]], predictions: dict[str, dict[str, int]]) -> tuple[float, dict[str, dict[str, float | int]]]:
    rows: dict[str, dict[str, float | int]] = {}
    for item in ITEMS:
        gold = [int(gold_by_id[record_id][item]) for record_id in predictions]
        pred = [predictions[record_id][item] for record_id in predictions]
        rows[item] = metric(gold, pred)
    return sum(float(row["f1"]) for row in rows.values()) / len(ITEMS), rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    predicted_rows = read_jsonl(args.predictions)
    gold_by_id = read_csv(args.labels)
    records_by_id = {row["id"]: row for row in read_jsonl(args.records)}
    if {row["id"] for row in predicted_rows} != set(records_by_id):
        raise ValueError("prediction and record IDs differ")

    prediction_sets = {
        mode: {row["id"]: labels_for(row, mode) for row in predicted_rows}
        for mode in ("first", "or", "and", "policy_raw", "actual")
    }
    # Hold the frozen replacements fixed while changing only the direct model's
    # pack selector.  This is the valid comparison for merge impact in EXP172.
    first_with_frozen = {
        record_id: {
            item: prediction_sets["actual"][record_id][item] if item in FROZEN_ITEMS
            else prediction_sets["first"][record_id][item]
            for item in ITEMS
        }
        for record_id in prediction_sets["actual"]
    }
    prediction_sets["first_with_frozen"] = first_with_frozen
    macro_scores = {}
    per_item = {}
    for mode, values in prediction_sets.items():
        macro_scores[mode], per_item[mode] = macro(gold_by_id, values)

    pack_counts = Counter(len(row["pass_judgments"]) for row in predicted_rows)
    document_counts = Counter(len(records_by_id[row["id"]]["docs"]) for row in predicted_rows)
    changed_by_policy_merge: Counter[str] = Counter()
    changed_by_frozen: Counter[str] = Counter()
    overflow_error_cells: Counter[str] = Counter()
    single_error_cells: Counter[str] = Counter()
    overflow_details: list[dict[str, Any]] = []
    total = Counter()
    per_item_pass_pattern: dict[str, Counter[str]] = defaultdict(Counter)
    item_location_errors: dict[str, Counter[str]] = defaultdict(Counter)
    evidence_quality: dict[str, Counter[str]] = defaultdict(Counter)

    for row in predicted_rows:
        record_id = row["id"]
        packs = len(row["pass_judgments"])
        first = prediction_sets["first"][record_id]
        raw = prediction_sets["policy_raw"][record_id]
        actual = prediction_sets["actual"][record_id]
        gold = gold_by_id[record_id]
        changed_items: list[str] = []
        for item in ITEMS:
            truth = int(gold[item])
            total["cells"] += 1
            total[f"gold_{truth}"] += 1
            total[f"actual_{actual[item]}"] += 1
            if actual[item] == truth:
                total["correct"] += 1
                if truth == 1:
                    total["tp"] += 1
            elif actual[item] == 1:
                total["fp"] += 1
            else:
                total["fn"] += 1
            values = [int(value[item]["위반여부"]) for value in row["pass_judgments"]]
            per_item_pass_pattern[item]["".join(map(str, values))] += 1
            if actual[item] == 1 and item not in ABSENCE_ITEMS:
                evidence = str(row["judgment"][item].get("근거문구") or "")
                source = "\n".join(document["text"] for document in records_by_id[record_id]["docs"])
                evidence_quality[item]["positive"] += 1
                evidence_quality[item]["empty"] += int(not evidence)
                evidence_quality[item]["invalid"] += int(bool(evidence) and evidence not in source)
            if first[item] != raw[item]:
                changed_by_policy_merge[item] += 1
                changed_items.append(item)
            if raw[item] != actual[item]:
                changed_by_frozen[item] += 1
            error_key = "fp" if actual[item] == 1 and truth == 0 else "fn" if actual[item] == 0 and truth == 1 else "correct"
            (single_error_cells if packs == 1 else overflow_error_cells)[error_key] += 1
            item_location_errors[item][f"{'single' if packs == 1 else 'overflow'}_{error_key}"] += 1
        if packs > 1:
            overflow_details.append({
                "id": record_id, "packs": packs, "documents": len(records_by_id[record_id]["docs"]),
                "merge_changed_items": changed_items,
                "actual_fp": [item for item in ITEMS if int(gold[item]) == 0 and actual[item] == 1],
                "actual_fn": [item for item in ITEMS if int(gold[item]) == 1 and actual[item] == 0],
            })

    error_by_item = []
    for item in ITEMS:
        row = dict(per_item["actual"][item])
        row.update({
            "item": item,
            "predicted_minus_gold": int(row["predicted_positive"]) - int(row["gold_positive"]),
            "raw_policy_minus_actual_cells": sum(
                prediction_sets["policy_raw"][record_id][item] != prediction_sets["actual"][record_id][item]
                for record_id in prediction_sets["actual"]
            ),
            "first_to_policy_merge_cells": changed_by_policy_merge[item],
            "pass_patterns": dict(sorted(per_item_pass_pattern[item].items())),
            "single_fp": item_location_errors[item]["single_fp"],
            "single_fn": item_location_errors[item]["single_fn"],
            "overflow_fp": item_location_errors[item]["overflow_fp"],
            "overflow_fn": item_location_errors[item]["overflow_fn"],
            "positive_empty_evidence": evidence_quality[item]["empty"],
            "positive_invalid_evidence": evidence_quality[item]["invalid"],
        })
        error_by_item.append(row)

    report = {
        "scope": "EXP172 completed direct complete-source dev200 checkpoint; offline diagnostic only",
        "records": len(predicted_rows),
        "calls": sum(len(row["pass_judgments"]) for row in predicted_rows),
        "pack_count_distribution": dict(sorted(pack_counts.items())),
        "source_document_count_distribution": dict(sorted(document_counts.items())),
        "macro_positive_f1_counterfactual": macro_scores,
        "aggregate_actual_cells": dict(total),
        "single_pack_cells": dict(single_error_cells),
        "overflow_pack_cells": dict(overflow_error_cells),
        "merge_changed_cell_count_by_item": dict(changed_by_policy_merge),
        "frozen_override_changed_cell_count_by_item": dict(changed_by_frozen),
        "per_item_actual": error_by_item,
        "overflow_notice_details": overflow_details,
        "interpretation": {
            "merge_counterfactual_definition": "first is first tokenizer-admitted pack; policy_raw is OR for non-absence and AND for absence; actual additionally includes frozen v2/v3/v21 postprocess.",
            "caution": "A final FP after OR is a model positive in at least one pack, not proof that OR itself is semantically wrong. The first-vs-policy score delta bounds the observed output effect of merging.",
        },
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# EXP172 merge diagnostic", "",
        f"- Records / calls: {report['records']} / {report['calls']}",
        f"- Pack distribution: {report['pack_count_distribution']}",
        f"- Macro positive F1 — first with frozen fixed: {macro_scores['first_with_frozen']:.6f}; policy raw: {macro_scores['policy_raw']:.6f}; actual (incl. frozen): {macro_scores['actual']:.6f}",
        f"- Actual cells — gold positive: {total['gold_1']}; predicted positive: {total['actual_1']}; TP: {total['tp']}; FP: {total['fp']}; FN: {total['fn']}",
        "", "## Largest actual-label error imbalances", "",
        "| item | gold+ | pred+ | TP | FP | FN | P | R | F1 | merge changed | frozen changed | single FP/FN | overflow FP/FN | empty evidence |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in sorted(error_by_item, key=lambda value: int(value["fp"]) + int(value["fn"]), reverse=True):
        lines.append(
            "| {item} | {gold_positive} | {predicted_positive} | {tp} | {fp} | {fn} | {precision:.3f} | {recall:.3f} | {f1:.3f} | {first_to_policy_merge_cells} | {raw_policy_minus_actual_cells} | {single_fp}/{single_fn} | {overflow_fp}/{overflow_fn} | {positive_empty_evidence} |".format(**row)
        )
    lines += ["", "## Overflow notices", ""]
    for detail in overflow_details:
        lines.append(f"- {detail['id']}: {detail['packs']} packs, merge changed {detail['merge_changed_items']}, FP {detail['actual_fp']}, FN {detail['actual_fn']}")
    (args.output_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
