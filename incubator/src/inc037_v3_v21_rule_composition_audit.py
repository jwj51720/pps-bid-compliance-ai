#!/usr/bin/env python3
"""Compose independently frozen v3/v21 rules into INC-018 predictions."""

from __future__ import annotations

import csv
import gzip
import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable

import inc001_simple_joint24 as common
from inc034_v21_default_share_predicate_audit import classify as classify_v21
from inc036_v3_performance_ratio_predicate_audit import classify as classify_v3


ROOT = Path(__file__).resolve().parents[2]
Rule = Callable[[dict[str, Any]], dict[str, Any]]
RULES: dict[str, Rule] = {"v3": classify_v3, "v21": classify_v21}


def load_records(filename: str) -> list[dict[str, Any]]:
    with gzip.open(ROOT / "data/raw/open" / filename, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def evidence_valid(record: dict[str, Any], result: dict[str, Any]) -> bool:
    return not result["prediction_diagnostic_only"] or (
        bool(result["evidence"])
        and any(result["evidence"] in document["text"] for document in record["docs"])
    )


def rule_summary(records: list[dict[str, Any]], results: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    return {
        item: {
            "positive_count": sum(result["prediction_diagnostic_only"] for result in rows.values()),
            "reason_counts": dict(Counter(result["reason"] for result in rows.values())),
            "evidence_validity": all(evidence_valid(record, rows[record["id"]]) for record in records),
        }
        for item, rows in results.items()
    }


def main() -> None:
    output = ROOT / "incubator/runs/inc037_v3_v21_rule_composition_audit"
    output.mkdir(parents=True, exist_ok=True)
    dev = load_records("dev.jsonl.gz")
    unlabeled = load_records("train_unlabeled.jsonl.gz")
    dev_results = {item: {record["id"]: rule(record) for record in dev} for item, rule in RULES.items()}
    unlabeled_results = {item: {record["id"]: rule(record) for record in unlabeled} for item, rule in RULES.items()}
    labels = {row["id"]: row for row in common.read_csv(ROOT / "data/raw/open/dev_labels.csv")}
    baseline_path = ROOT / "incubator/runs/inc018_global_context_architecture/predictions_single_full.csv"
    with baseline_path.open(encoding="utf-8", newline="") as handle:
        baseline_rows = list(csv.DictReader(handle))
    baseline = {row["id"]: row for row in baseline_rows}
    if set(baseline) != {record["id"] for record in dev}:
        raise ValueError("INC-018 baseline IDs do not exactly match the dev records")

    composed_by_id: dict[str, dict[str, Any]] = {}
    unchanged = True
    changed_cells = Counter()
    for record in dev:
        row = baseline[record["id"]].copy()
        for item, rows in dev_results.items():
            before = row[item], row[f"e{item[1:]}"]
            result = rows[record["id"]]
            row[item] = str(result["prediction_diagnostic_only"])
            row[f"e{item[1:]}"] = result["evidence"]
            changed_cells[item] += before != (row[item], row[f"e{item[1:]}"])
        unchanged &= all(
            row[key] == baseline[record["id"]][key]
            for key in row
            if key not in ("v3", "e3", "v21", "e21")
        )
        for item in common.ITEMS:
            row[item] = int(row[item])
        composed_by_id[record["id"]] = row
    # Preserve the immutable baseline's row order in the materialized artifact.
    composed = [composed_by_id[row["id"]] for row in baseline_rows]
    metrics, per_item = common.evaluate(composed, labels)

    dev_rule_metrics: dict[str, dict[str, Any]] = {}
    for item, rows in dev_results.items():
        tp = sum(int(labels[record_id][item]) and result["prediction_diagnostic_only"] for record_id, result in rows.items())
        fp = sum(not int(labels[record_id][item]) and result["prediction_diagnostic_only"] for record_id, result in rows.items())
        fn = sum(int(labels[record_id][item]) and not result["prediction_diagnostic_only"] for record_id, result in rows.items())
        dev_rule_metrics[item] = {"tp": tp, "fp": fp, "fn": fn, "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0}
    report = {
        "experiment_id": "inc037_v3_v21_rule_composition_audit",
        "method": "frozen INC-034 v21 and INC-036 v3 rules replace only their four INC-018 cells",
        "dev": {
            "rules": dev_rule_metrics,
            "composition_macro_f1": metrics["macro_f1"],
            "composition_per_item": per_item,
            "non_target_cells_unchanged": unchanged,
            "changed_target_cell_pairs": dict(changed_cells),
            "evidence_validity": all(
                evidence_valid(record, dev_results[item][record["id"]])
                for record in dev for item in RULES
            ),
        },
        "unlabeled_format_audit": rule_summary(unlabeled, unlabeled_results),
    }
    for item, rows in dev_results.items():
        common.write_jsonl(output / f"dev_{item}_rule_manifest.jsonl", list(rows.values()))
    for item, rows in unlabeled_results.items():
        common.write_jsonl(output / f"unlabeled_{item}_rule_manifest.jsonl", list(rows.values()))
    common.write_json(output / "report.json", report)
    with (output / "dev_composed_predictions.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=common.CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(composed)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
