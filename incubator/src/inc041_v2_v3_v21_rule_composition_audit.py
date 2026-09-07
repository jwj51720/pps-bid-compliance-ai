#!/usr/bin/env python3
"""Add frozen v2 rule to verified INC-037 CSV without changing other cells."""

from __future__ import annotations

import csv
import gzip
import json
from collections import Counter
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common
from inc040_v2_below_notice_performance_predicate_audit import classify


ROOT = Path(__file__).resolve().parents[2]


def load_records(filename: str) -> list[dict[str, Any]]:
    with gzip.open(ROOT / "data/raw/open" / filename, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def evidence_valid(record: dict[str, Any], result: dict[str, Any]) -> bool:
    return not result["prediction_diagnostic_only"] or (
        bool(result["evidence"])
        and any(result["evidence"] in document["text"] for document in record["docs"])
    )


def main() -> None:
    output = ROOT / "incubator/runs/inc041_v2_v3_v21_rule_composition_audit"
    output.mkdir(parents=True, exist_ok=True)
    dev = load_records("dev.jsonl.gz")
    unlabeled = load_records("train_unlabeled.jsonl.gz")
    dev_rule = {record["id"]: classify(record) for record in dev}
    unlabeled_rule = {record["id"]: classify(record) for record in unlabeled}
    labels = {row["id"]: row for row in common.read_csv(ROOT / "data/raw/open/dev_labels.csv")}
    baseline_path = ROOT / "incubator/runs/inc037_v3_v21_rule_composition_audit/dev_composed_predictions.csv"
    with baseline_path.open(encoding="utf-8", newline="") as handle:
        baseline_rows = list(csv.DictReader(handle))
    baseline = {row["id"]: row for row in baseline_rows}
    if set(baseline) != set(dev_rule):
        raise ValueError("INC-037 IDs do not exactly match dev IDs")
    composed_by_id: dict[str, dict[str, Any]] = {}
    unchanged = True
    changed_pairs = 0
    for record in dev:
        row = baseline[record["id"]].copy()
        result = dev_rule[record["id"]]
        before = row["v2"], row["e2"]
        row["v2"] = str(result["prediction_diagnostic_only"])
        row["e2"] = result["evidence"]
        changed_pairs += before != (row["v2"], row["e2"])
        unchanged &= all(row[key] == baseline[record["id"]][key] for key in row if key not in ("v2", "e2"))
        for item in common.ITEMS:
            row[item] = int(row[item])
        composed_by_id[record["id"]] = row
    composed = [composed_by_id[row["id"]] for row in baseline_rows]
    metrics, per_item = common.evaluate(composed, labels)
    tp = sum(int(labels[record_id]["v2"]) and result["prediction_diagnostic_only"] for record_id, result in dev_rule.items())
    fp = sum(not int(labels[record_id]["v2"]) and result["prediction_diagnostic_only"] for record_id, result in dev_rule.items())
    fn = sum(int(labels[record_id]["v2"]) and not result["prediction_diagnostic_only"] for record_id, result in dev_rule.items())
    report = {
        "experiment_id": "inc041_v2_v3_v21_rule_composition_audit",
        "method": "frozen INC-040 v2 rule replaces only v2/e2 in verified INC-037 CSV",
        "dev": {"v2_rule": {"tp": tp, "fp": fp, "fn": fn, "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0}, "composition_macro_f1": metrics["macro_f1"], "composition_per_item": per_item, "non_v2_cells_unchanged": unchanged, "changed_v2_e2_pairs": changed_pairs, "evidence_validity": all(evidence_valid(record, dev_rule[record["id"]]) for record in dev)},
        "unlabeled_format_audit": {"record_count": len(unlabeled), "positive_count": sum(result["prediction_diagnostic_only"] for result in unlabeled_rule.values()), "reason_counts": dict(Counter(result["reason"] for result in unlabeled_rule.values())), "evidence_validity": all(evidence_valid(record, unlabeled_rule[record["id"]]) for record in unlabeled)},
    }
    common.write_jsonl(output / "dev_v2_rule_manifest.jsonl", list(dev_rule.values()))
    common.write_jsonl(output / "unlabeled_v2_rule_manifest.jsonl", list(unlabeled_rule.values()))
    common.write_json(output / "report.json", report)
    with (output / "dev_composed_predictions.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=common.CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(composed)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
