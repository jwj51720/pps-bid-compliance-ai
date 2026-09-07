#!/usr/bin/env python3
"""Check frozen EXP-123 rules on both pre-existing INC-076 folds; no API call."""

from __future__ import annotations

import json
import sys
import tarfile
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common


ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "dist/pps-artifacts_20260904_mac.tar.xz"
MEMBER = "pps-artifacts_20260904_mac/outputs/exp-120-official-baseline-card-v6-full200/predictions.jsonl"
FOLDS = ROOT / "incubator/runs/inc076_frozen_holdout_audit/holdout.json"
OUT = ROOT / "incubator/runs/inc130_exp123_frozen_fold_stability"
sys.path.insert(0, str(ROOT / "incubator/submission_candidates/exp123_card_v6_frozen_rules"))
from src.frozen_rules import _v2, _v3, _v21  # noqa: E402


RULES = {"v2": _v2, "v3": _v3, "v21": _v21}


def archived_rows() -> dict[str, dict[str, int]]:
    with tarfile.open(ARCHIVE, "r:xz") as archive:
        handle = archive.extractfile(MEMBER)
        if handle is None:
            raise RuntimeError("EXP-120 prediction artifact absent")
        rows = [json.loads(line) for line in handle.read().decode("utf-8").splitlines() if line]
    result = {row["id"]: {item: int(row["judgment"][item]["위반여부"]) for item in common.ITEMS} for row in rows}
    if len(result) != 200:
        raise RuntimeError(f"expected 200 archived predictions, got {len(result)}")
    return result


def metrics(predictions: dict[str, dict[str, int]], labels: dict[str, dict[str, str]], ids: list[str]) -> tuple[float, list[dict[str, Any]]]:
    per_item = []
    for item in common.ITEMS:
        tp = fp = fn = 0
        for record_id in ids:
            actual, prediction = int(labels[record_id][item]), predictions[record_id][item]
            tp += actual == prediction == 1; fp += actual == 0 and prediction == 1; fn += actual == 1 and prediction == 0
        per_item.append({"item": item, "tp": tp, "fp": fp, "fn": fn, "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0})
    return sum(row["f1"] for row in per_item) / len(per_item), per_item


def main() -> None:
    records = list(common.read_jsonl_gz(ROOT / "data/raw/open/dev.jsonl.gz"))
    labels = {row["id"]: row for row in common.read_csv(ROOT / "data/raw/open/dev_labels.csv")}
    baseline = archived_rows()
    if set(baseline) != set(labels):
        raise RuntimeError("archived predictions must match dev labels")
    composed = {record_id: dict(row) for record_id, row in baseline.items()}
    audit = []
    for record in records:
        for item, rule in RULES.items():
            evidence = rule(record); old = composed[record["id"]][item]; new = int(bool(evidence))
            composed[record["id"]][item] = new
            audit.append({"id": record["id"], "item": item, "changed": int(old != new), "source_evidence_valid": not evidence or any(evidence in document["text"] for document in record["docs"])})
    folds = json.loads(FOLDS.read_text(encoding="utf-8"))["folds"]
    report: dict[str, Any] = {"experiment_id": "inc130_exp123_frozen_fold_stability", "method": "archived EXP-120 plus predicates frozen before EXP-123, scored by pre-existing INC-076 folds", "source_evidence_valid": all(row["source_evidence_valid"] for row in audit), "changed_cells": sum(row["changed"] for row in audit), "folds": {}}
    for name, data in folds.items():
        ids = data["ids"]
        before, before_per = metrics(baseline, labels, ids); after, after_per = metrics(composed, labels, ids)
        report["folds"][name] = {"records": len(ids), "baseline_macro_f1": before, "composed_macro_f1": after, "delta": after - before, "per_item": [{"item": old["item"], "before_f1": old["f1"], "after_f1": new["f1"]} for old, new in zip(before_per, after_per)]}
    OUT.mkdir(parents=True, exist_ok=True); common.write_json(OUT / "report.json", report)
    print(json.dumps({name: {key: row[key] for key in ("records", "baseline_macro_f1", "composed_macro_f1", "delta")} for name, row in report["folds"].items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
