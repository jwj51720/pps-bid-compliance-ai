#!/usr/bin/env python3
"""Aggregate the predeclared INC-125 ledger/direct-card policy on dev-200."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common


ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "incubator/runs/inc125_luna_full_dev_official_ledger"
DIRECT = ROOT / "incubator/runs/inc088_openai_luna_high_full_dev_card/responses.jsonl"
PRIOR_RUNS = (
    ROOT / "incubator/runs/inc118_luna_official_ledger_stratified32/responses.jsonl",
    ROOT / "incubator/runs/inc118_luna_official_ledger_holdout32/responses.jsonl",
    ROOT / "incubator/runs/inc118_luna_official_ledger_third32/responses.jsonl",
)


def read_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def score(predictions: dict[str, dict[str, int]], gold: dict[str, dict[str, str]]) -> tuple[float, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    for item in common.ITEMS:
        tp = fp = fn = 0
        for record_id, labels in predictions.items():
            actual, predicted = int(gold[record_id][item]), labels[item]
            tp += actual == predicted == 1
            fp += actual == 0 and predicted == 1
            fn += actual == 1 and predicted == 0
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        rows.append({
            "item": item, "gold_positive": tp + fn, "predicted_positive": tp + fp,
            "tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        })
    return sum(row["f1"] for row in rows) / len(rows), rows


def main() -> None:
    records = list(common.read_jsonl_gz(ROOT / "data/raw/open/dev.jsonl.gz"))
    all_ids = [record["id"] for record in records]
    gold = {row["id"]: row for row in common.read_csv(ROOT / "data/raw/open/dev_labels.csv")}
    direct_rows = read_rows(DIRECT)
    direct = {row["id"]: row["labels"] for row in direct_rows if row.get("success")}
    if set(direct) != set(all_ids):
        raise RuntimeError("INC-088 direct outputs must cover exactly dev-200")
    ledger_rows = [row for path in (*PRIOR_RUNS, RUN / "responses.jsonl") for row in read_rows(path)]
    ledger = {row["id"]: row["labels"] for row in ledger_rows if row.get("success")}
    duplicate_successes = len([row for row in ledger_rows if row.get("success")]) != len(ledger)
    if duplicate_successes:
        raise RuntimeError("ledger responses must not duplicate a successful record")
    unexpected = set(ledger) - set(all_ids)
    if unexpected:
        raise RuntimeError(f"unknown ledger IDs: {sorted(unexpected)}")
    fallback_ids = [record_id for record_id in all_ids if record_id not in ledger]
    # A whole-vector fallback is fixed by protocol.  v24 always uses direct;
    # for an unavailable ledger row every item uses direct rather than a
    # label-selective choice.
    hybrid: dict[str, dict[str, int]] = {}
    source: dict[str, str] = {}
    for record_id in all_ids:
        if record_id in ledger:
            hybrid[record_id] = {item: ledger[record_id][item] for item in common.ITEMS if item != "v24"}
            hybrid[record_id]["v24"] = direct[record_id]["v24"]
            source[record_id] = "ledger_v1_v23__direct_v24"
        else:
            hybrid[record_id] = dict(direct[record_id])
            source[record_id] = "direct_whole_vector_transport_fallback"
    if len(hybrid) != 200 or set(hybrid) != set(all_ids):
        raise RuntimeError("aggregation must account for every dev record")
    baseline_macro, baseline_items = score(direct, gold)
    hybrid_macro, hybrid_items = score(hybrid, gold)
    comparison = {
        "experiment_id": "inc125_luna_full_dev_official_ledger",
        "policy": "official ledger v1-v23 + direct card-v6 v24; direct whole-vector on ledger transport failure",
        "records": len(all_ids),
        "ledger_successes": len(ledger),
        "fallback_ids": fallback_ids,
        "baseline_direct_card_macro_f1": baseline_macro,
        "hybrid_macro_f1": hybrid_macro,
        "delta": hybrid_macro - baseline_macro,
        "per_item_baseline": baseline_items,
        "per_item_hybrid": hybrid_items,
        "prediction_source_counts": {
            "ledger_v1_v23__direct_v24": sum(value == "ledger_v1_v23__direct_v24" for value in source.values()),
            "direct_whole_vector_transport_fallback": sum(value == "direct_whole_vector_transport_fallback" for value in source.values()),
        },
    }
    RUN.mkdir(parents=True, exist_ok=True)
    common.write_json(RUN / "full_dev_comparison.json", comparison)
    with (RUN / "full_dev_predictions.jsonl").open("w", encoding="utf-8") as handle:
        for record_id in all_ids:
            handle.write(json.dumps({"id": record_id, "labels": hybrid[record_id], "source": source[record_id]}, ensure_ascii=False) + "\n")
    with (RUN / "per_item_full_dev.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["item", "baseline_f1", "hybrid_f1", "baseline_tp", "baseline_fp", "baseline_fn", "hybrid_tp", "hybrid_fp", "hybrid_fn"])
        writer.writeheader()
        for before, after in zip(baseline_items, hybrid_items):
            writer.writerow({
                "item": before["item"], "baseline_f1": before["f1"], "hybrid_f1": after["f1"],
                "baseline_tp": before["tp"], "baseline_fp": before["fp"], "baseline_fn": before["fn"],
                "hybrid_tp": after["tp"], "hybrid_fp": after["fp"], "hybrid_fn": after["fn"],
            })
    changed = []
    for record_id in all_ids:
        for item in common.ITEMS:
            if direct[record_id][item] != hybrid[record_id][item]:
                changed.append({
                    "id": record_id,
                    "item": item,
                    "gold": int(gold[record_id][item]),
                    "direct": direct[record_id][item],
                    "hybrid": hybrid[record_id][item],
                    "became_correct": int(hybrid[record_id][item] == int(gold[record_id][item])),
                    "became_wrong": int(direct[record_id][item] == int(gold[record_id][item])),
                })
    with (RUN / "changed_cells.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(changed[0]) if changed else ["id", "item", "gold", "direct", "hybrid", "became_correct", "became_wrong"])
        writer.writeheader()
        writer.writerows(changed)
    comparison["changed_cells"] = {
        "count": len(changed),
        "became_correct": sum(row["became_correct"] for row in changed),
        "became_wrong": sum(row["became_wrong"] for row in changed),
    }
    common.write_json(RUN / "full_dev_comparison.json", comparison)
    print(json.dumps({key: comparison[key] for key in ("records", "ledger_successes", "fallback_ids", "baseline_direct_card_macro_f1", "hybrid_macro_f1", "delta")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
