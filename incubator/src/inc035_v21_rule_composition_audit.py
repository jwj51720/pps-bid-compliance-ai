#!/usr/bin/env python3
"""Compose frozen INC-034 v21 rule into immutable INC-018 predictions."""

from __future__ import annotations

import csv
import gzip
import json
from collections import Counter
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common
from inc034_v21_default_share_predicate_audit import classify


ROOT = Path(__file__).resolve().parents[2]


def load_split(name: str) -> list[dict[str, Any]]:
    filename = "dev.jsonl.gz" if name == "dev" else "train_unlabeled.jsonl.gz"
    path = ROOT / "data/raw/open" / filename
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def valid(record: dict[str, Any], row: dict[str, Any]) -> bool:
    return not row["prediction_diagnostic_only"] or bool(row["evidence"]) and any(row["evidence"] in doc["text"] for doc in record["docs"])


def main() -> None:
    output = ROOT / "incubator/runs/inc035_v21_rule_composition_audit"; output.mkdir(parents=True, exist_ok=True)
    dev = load_split("dev"); unlabeled = load_split("unlabeled"); dev_rule = {record["id"]: classify(record) for record in dev}; unlabeled_rule = {record["id"]: classify(record) for record in unlabeled}
    labels = {row["id"]: row for row in common.read_csv(ROOT / "data/raw/open/dev_labels.csv")}
    baseline_path = ROOT / "incubator/runs/inc018_global_context_architecture/predictions_single_full.csv"
    with baseline_path.open(encoding="utf-8", newline="") as handle: baseline = {row["id"]: row for row in csv.DictReader(handle)}
    composed = []
    unchanged = True
    for record in dev:
        row = baseline[record["id"]].copy(); rule = dev_rule[record["id"]]
        original = row["v21"], row["e21"]
        row["v21"] = str(rule["prediction_diagnostic_only"]); row["e21"] = rule["evidence"]
        unchanged &= all(row[key] == baseline[record["id"]][key] for key in row if key not in ("v21", "e21"))
        if original == (row["v21"], row["e21"]): pass
        for item in common.ITEMS: row[item] = int(row[item])
        composed.append(row)
    metrics, per_item = common.evaluate(composed, labels)
    report = {"experiment_id": "inc035_v21_rule_composition_audit", "method": "frozen INC-034 rule replaces only v21/e21 in INC-018 single_full", "dev": {"v21_rule": {"tp": sum(int(labels[row["id"]]["v21"]) and row["prediction_diagnostic_only"] for row in dev_rule.values()), "fp": sum(not int(labels[row["id"]]["v21"]) and row["prediction_diagnostic_only"] for row in dev_rule.values()), "fn": sum(int(labels[row["id"]]["v21"]) and not row["prediction_diagnostic_only"] for row in dev_rule.values()), "evidence_validity": all(valid(record, dev_rule[record["id"]]) for record in dev)}, "composition_macro_f1": metrics["macro_f1"], "composition_per_item": per_item, "non_v21_cells_unchanged": unchanged}, "unlabeled_format_audit": {"record_count": len(unlabeled), "positive_count": sum(row["prediction_diagnostic_only"] for row in unlabeled_rule.values()), "reason_counts": dict(Counter(row["reason"] for row in unlabeled_rule.values())), "evidence_validity": all(valid(record, unlabeled_rule[record["id"]]) for record in unlabeled)} }
    common.write_jsonl(output / "dev_rule_manifest.jsonl", list(dev_rule.values())); common.write_jsonl(output / "unlabeled_rule_manifest.jsonl", list(unlabeled_rule.values())); common.write_json(output / "report.json", report)
    with (output / "dev_composed_predictions.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=common.CSV_COLUMNS, lineterminator="\n"); writer.writeheader(); writer.writerows(composed)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
