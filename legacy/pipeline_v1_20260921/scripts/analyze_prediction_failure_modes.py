#!/usr/bin/env python3
"""Post-hoc source/output failure decomposition for a saved experiment.

Gold labels and evidence are used only after prediction.  This script does not
route records, render prompts, alter cards, or emit label rules.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data import full_document_text, load_records
from src.schema import ABSENCE_ITEMS, ITEMS


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _model_label(prediction: dict[str, Any], item: str) -> int:
    provenance = prediction.get("decision_provenance") or {}
    model = provenance.get("model_judgment") or prediction.get("judgment") or {}
    value = model.get(item, {}).get("위반여부", 0)
    return int(value) if value in {0, 1} else 0


def _rendered_text(rows: list[dict[str, Any]]) -> str:
    return "\n".join(
        str(message.get("content", ""))
        for row in rows
        for message in row.get("messages", [])
    )


def _f1(tp: int, fp: int, fn: int) -> float:
    denominator = 2 * tp + fp + fn
    return 2 * tp / denominator if denominator else 0.0


def analyze(
    records: list[dict[str, Any]],
    labels: dict[str, dict[str, str]],
    submissions: dict[str, dict[str, str]],
    predictions: dict[str, dict[str, Any]],
    inputs: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    per_item = {item: Counter() for item in ITEMS}
    examples: dict[str, dict[str, list[str]]] = {
        item: {} for item in ITEMS
    }
    record_by_id = {record["id"]: record for record in records}

    for record_id, record in record_by_id.items():
        gold_row = labels[record_id]
        output_row = submissions[record_id]
        prediction = predictions[record_id]
        source = full_document_text(record)
        rendered = _rendered_text(inputs.get(record_id, []))
        multi_pack = len(inputs.get(record_id, [])) > 1
        parse_error = bool(prediction.get("parse_errors"))

        for index, item in enumerate(ITEMS, 1):
            counts = per_item[item]
            gold = int(gold_row[item])
            final = int(output_row[item])
            model = _model_label(prediction, item)
            evidence = gold_row[f"e{index}"]
            predicted_evidence = output_row[f"e{index}"]
            counts["gold_positive"] += gold
            counts["predicted_positive"] += final
            counts["tp"] += int(gold == 1 and final == 1)
            counts["fp"] += int(gold == 0 and final == 1)
            counts["fn"] += int(gold == 1 and final == 0)
            counts["postprocess_recovered_tp"] += int(gold == 1 and model == 0 and final == 1)
            counts["postprocess_removed_tp"] += int(gold == 1 and model == 1 and final == 0)
            counts["postprocess_introduced_fp"] += int(gold == 0 and model == 0 and final == 1)
            counts["postprocess_removed_fp"] += int(gold == 0 and model == 1 and final == 0)

            if gold == 1 and final == 0:
                if item in ABSENCE_ITEMS:
                    bucket = "fn_absence_requires_whole_notice"
                elif not evidence:
                    bucket = "fn_without_gold_evidence"
                elif evidence in rendered:
                    bucket = "fn_gold_evidence_in_rendered_input"
                elif evidence in source:
                    bucket = "fn_gold_evidence_in_source_not_rendered"
                else:
                    bucket = "fn_gold_evidence_unresolved"
                counts[bucket] += 1
                counts["fn_on_multi_pack_record"] += int(multi_pack)
                counts["fn_on_parse_error_record"] += int(parse_error)
                examples[item].setdefault(bucket, [])
                if len(examples[item][bucket]) < 8:
                    examples[item][bucket].append(record_id)

            if gold == 0 and final == 1:
                if predicted_evidence and predicted_evidence in source:
                    bucket = "fp_with_valid_source_substring"
                elif predicted_evidence:
                    bucket = "fp_with_invalid_evidence"
                else:
                    bucket = "fp_without_evidence"
                counts[bucket] += 1
                counts["fp_on_multi_pack_record"] += int(multi_pack)
                counts["fp_on_parse_error_record"] += int(parse_error)
                examples[item].setdefault(bucket, [])
                if len(examples[item][bucket]) < 8:
                    examples[item][bucket].append(record_id)

    item_rows = []
    totals: Counter[str] = Counter()
    for item in ITEMS:
        row = dict(per_item[item])
        row["item"] = item
        row["f1"] = _f1(row.get("tp", 0), row.get("fp", 0), row.get("fn", 0))
        item_rows.append(row)
        totals.update(per_item[item])

    return {
        "scope": {
            "records": len(records),
            "method": "post-hoc prediction/source/output decomposition; no routing or label changes",
        },
        "overall": dict(totals),
        "per_item": item_rows,
        "examples": examples,
    }


def markdown(report: dict[str, Any]) -> str:
    overall = report["overall"]
    lines = [
        "# Saved prediction failure-mode audit",
        "",
        "Gold is used only after prediction. This report must not be used as a prompt example, "
        "routing table, threshold, or Python label rule.",
        "",
        "## Overall",
        "",
        f"- TP / FP / FN: `{overall.get('tp', 0)} / {overall.get('fp', 0)} / {overall.get('fn', 0)}`",
        f"- rendered-visible-evidence FN: `{overall.get('fn_gold_evidence_in_rendered_input', 0)}`",
        f"- source-not-rendered FN: `{overall.get('fn_gold_evidence_in_source_not_rendered', 0)}`",
        f"- no-gold-evidence FN: `{overall.get('fn_without_gold_evidence', 0)}`",
        f"- absence whole-notice FN: `{overall.get('fn_absence_requires_whole_notice', 0)}`",
        f"- FN on multi-pack / parse-error records: `{overall.get('fn_on_multi_pack_record', 0)} / {overall.get('fn_on_parse_error_record', 0)}`",
        f"- FP with valid / invalid / blank evidence: `{overall.get('fp_with_valid_source_substring', 0)} / {overall.get('fp_with_invalid_evidence', 0)} / {overall.get('fp_without_evidence', 0)}`",
        "",
        "## Per item",
        "",
        "| item | F1 | TP | FP | FN | visible-e FN | no-e FN | absence FN | multi-pack FN | parse FN |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["per_item"]:
        lines.append(
            f"| {row['item']} | {row['f1']:.3f} | {row.get('tp', 0)} | "
            f"{row.get('fp', 0)} | {row.get('fn', 0)} | "
            f"{row.get('fn_gold_evidence_in_rendered_input', 0)} | "
            f"{row.get('fn_without_gold_evidence', 0)} | "
            f"{row.get('fn_absence_requires_whole_notice', 0)} | "
            f"{row.get('fn_on_multi_pack_record', 0)} | "
            f"{row.get('fn_on_parse_error_record', 0)} |"
        )
    lines.extend([
        "",
        "A visible exact span proves input observability, not the legal cause. FP source-substring "
        "validity proves only that the quoted text exists.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-dir", required=True)
    parser.add_argument("--records", default="data/raw/open/dev.jsonl.gz")
    parser.add_argument("--labels", default="data/raw/open/dev_labels.csv")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    experiment_dir = Path(args.experiment_dir)
    records = load_records(args.records)
    with Path(args.labels).open(encoding="utf-8", newline="") as handle:
        labels = {row["id"]: row for row in csv.DictReader(handle)}
    with (experiment_dir / "submission.csv").open(encoding="utf-8", newline="") as handle:
        submissions = {row["id"]: row for row in csv.DictReader(handle)}
    predictions = {
        row["id"]: row for row in _load_jsonl(experiment_dir / "predictions.jsonl")
    }
    input_rows: dict[str, list[dict[str, Any]]] = {}
    for row in _load_jsonl(experiment_dir / "inputs.jsonl"):
        input_rows.setdefault(row["id"], []).append(row)

    record_ids = {record["id"] for record in records}
    for name, ids in {
        "labels": set(labels),
        "submission": set(submissions),
        "predictions": set(predictions),
        "inputs": set(input_rows),
    }.items():
        if ids != record_ids:
            raise ValueError(f"{name} IDs do not match records")

    report = analyze(records, labels, submissions, predictions, input_rows)
    destination = Path(args.output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "failure_modes.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (destination / "failure_modes.md").write_text(markdown(report), encoding="utf-8")
    print(destination / "failure_modes.md")
    print(json.dumps(report["overall"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
