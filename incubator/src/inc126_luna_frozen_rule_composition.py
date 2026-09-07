#!/usr/bin/env python3
"""Historical composition of INC-125 with rules frozen before that run."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import inc001_simple_joint24 as common


ROOT = Path(__file__).resolve().parents[2]
INC125 = ROOT / "incubator/runs/inc125_luna_full_dev_official_ledger"
OUT = ROOT / "incubator/runs/inc126_luna_ledger_frozen_rule_composition"
FROZEN_CANDIDATE = ROOT / "incubator/submission_candidates/exp123_card_v6_frozen_rules"
sys.path.insert(0, str(FROZEN_CANDIDATE))
from src.frozen_rules import _v2, _v3, _v21  # noqa: E402


RULES = {"v2": _v2, "v3": _v3, "v21": _v21}


def metrics(predictions: dict[str, dict[str, int]], gold: dict[str, dict[str, str]]):
    rows = []
    for item in common.ITEMS:
        tp = fp = fn = 0
        for record_id, prediction in predictions.items():
            actual = int(gold[record_id][item])
            tp += actual == prediction[item] == 1
            fp += actual == 0 and prediction[item] == 1
            fn += actual == 1 and prediction[item] == 0
        f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0
        rows.append({"item": item, "tp": tp, "fp": fp, "fn": fn, "f1": f1})
    return sum(row["f1"] for row in rows) / len(rows), rows


def main() -> None:
    records = list(common.read_jsonl_gz(ROOT / "data/raw/open/dev.jsonl.gz"))
    gold = {row["id"]: row for row in common.read_csv(ROOT / "data/raw/open/dev_labels.csv")}
    base_rows = [json.loads(line) for line in (INC125 / "full_dev_predictions.jsonl").read_text(encoding="utf-8").splitlines() if line]
    base = {row["id"]: row["labels"] for row in base_rows}
    if set(base) != set(gold):
        raise RuntimeError("INC-125 predictions must cover exactly dev-200")
    composed = {record_id: dict(labels) for record_id, labels in base.items()}
    audit = []
    for record in records:
        for item, rule in RULES.items():
            evidence = rule(record)
            before = composed[record["id"]][item]
            composed[record["id"]][item] = int(bool(evidence))
            audit.append({
                "id": record["id"], "item": item, "prediction": int(bool(evidence)),
                "evidence_valid": not evidence or any(evidence in doc["text"] for doc in record["docs"]),
                "changed": int(before != int(bool(evidence))),
            })
    base_macro, base_items = metrics(base, gold)
    macro, item_rows = metrics(composed, gold)
    if not all(row["evidence_valid"] for row in audit):
        raise RuntimeError("frozen rule evidence must be source-contained")
    OUT.mkdir(parents=True, exist_ok=True)
    report = {
        "experiment_id": "inc126_luna_ledger_frozen_rule_composition",
        "status": "historical composition only; predicates were frozen before INC-125",
        "source_policy": "INC-125 official ledger v1-v23 + direct-card v24",
        "replaced_items": list(RULES),
        "baseline_macro_f1": base_macro,
        "composed_macro_f1": macro,
        "delta": macro - base_macro,
        "per_item_before": base_items,
        "per_item_after": item_rows,
        "rule_audit": {
            "rows": len(audit), "changed_cells": sum(row["changed"] for row in audit),
            "source_evidence_valid": all(row["evidence_valid"] for row in audit),
        },
    }
    common.write_json(OUT / "report.json", report)
    common.write_jsonl(OUT / "predictions.jsonl", [{"id": record_id, "labels": composed[record_id]} for record_id in base])
    with (OUT / "per_item.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["item", "before_f1", "after_f1", "before_tp", "before_fp", "before_fn", "after_tp", "after_fp", "after_fn"])
        writer.writeheader()
        for before, after in zip(base_items, item_rows):
            writer.writerow({"item": before["item"], "before_f1": before["f1"], "after_f1": after["f1"], "before_tp": before["tp"], "before_fp": before["fp"], "before_fn": before["fn"], "after_tp": after["tp"], "after_fp": after["fp"], "after_fn": after["fn"]})
    print(json.dumps({key: report[key] for key in ("baseline_macro_f1", "composed_macro_f1", "delta", "rule_audit")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
