#!/usr/bin/env python3
"""Independent replication of the no-law INC-030 restriction-group control."""

from __future__ import annotations

import argparse
import csv
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

import inc001_simple_joint24 as common
import inc029_restriction_law_context as base
import inc030_restriction_law_context_dev200 as inc030


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "incubator/runs/inc032_restriction_group_replication"


def ids() -> list[str]:
    records, _, _ = base.load_inputs()
    return sorted(records)


def run_one(record_id: str) -> None:
    path = OUTPUT / "records" / f"{record_id}_control.json"
    if path.exists():
        return
    base.OUTPUT = OUTPUT
    base.run_one(record_id, "control")


def run_all(workers: int) -> None:
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_one, record_id) for record_id in ids()]
        for index, future in enumerate(as_completed(futures), 1):
            future.result()
            if index % workers == 0 or index == len(futures):
                print(f"completed={index}/{len(futures)}", flush=True)


def load_entries(directory: Path) -> dict[str, dict[str, Any]]:
    return {record_id: json.loads((directory / "records" / f"{record_id}_control.json").read_text(encoding="utf-8")) for record_id in ids()}


def composition(group_entries: dict[str, dict[str, Any]], labels: dict[str, dict[str, str]]) -> dict[str, Any]:
    baseline_path = ROOT / "incubator/runs/inc018_global_context_architecture/predictions_single_full.csv"
    with baseline_path.open(encoding="utf-8", newline="") as handle:
        rows = {row["id"]: row for row in csv.DictReader(handle)}
    for record_id, entry in group_entries.items():
        for item in base.ITEMS:
            index = item[1:]
            rows[record_id][item] = str(entry["judgment"][item]["위반여부"])
            rows[record_id][f"e{index}"] = entry["judgment"][item]["근거문구"]
    normalized = []
    for record_id in ids():
        row = rows[record_id].copy()
        for item in common.ITEMS:
            row[item] = int(row[item])
        normalized.append(row)
    metrics, per_item = common.evaluate(normalized, labels)
    return {"macro_f1": metrics["macro_f1"], "per_item": per_item}


def aggregate() -> None:
    records, labels, _ = base.load_inputs(); entries = load_entries(OUTPUT)
    macro, tp, fp, fn = inc030.confusion(entries, labels, ids())
    positives = valid = 0
    for record_id, entry in entries.items():
        source = "\n".join(doc["text"] for doc in records[record_id]["docs"])
        for item in base.ITEMS:
            if entry.get("judgment", {}).get(item, {}).get("위반여부", 0):
                positives += 1; valid += bool(entry["judgment"][item]["근거문구"] in source)
    inc030_entries = load_entries(ROOT / "incubator/runs/inc030_restriction_law_context_dev200")
    result = {"experiment_id": "inc032_restriction_group_replication", "requested_calls": 200, "observed_calls": len(entries), "successful_calls": sum(entry["success"] for entry in entries.values()), "failure_count": sum(not entry["success"] for entry in entries.values()), "target_metrics": {"macro_f1": macro, "tp": tp, "fp": fp, "fn": fn, "recall_micro": tp / (tp + fn) if tp + fn else 0.0, "evidence_validity": valid / positives if positives else None, "reported_cost_usd": sum(float(entry["usage"].get("cost", 0) or 0) for entry in entries.values())}, "compositions": {"inc030_control": composition(inc030_entries, labels), "inc032_replication": composition(entries, labels)}}
    common.write_json(OUTPUT / "metrics.json", result); common.write_jsonl(OUTPUT / "responses.jsonl", list(entries.values())); print(json.dumps(result, ensure_ascii=False, indent=2))


def preflight() -> None:
    records, _, table = base.load_inputs(); manifest = []
    for record_id in ids():
        manifest.append({"id": record_id, "prompt_sha256": common.sha256_text(json.dumps(base.messages(records[record_id], table, "control"), ensure_ascii=False, sort_keys=True))})
    common.write_json(OUTPUT / "config.json", {"items": base.ITEMS, "model": base.request_config(), "max_calls": 200, "max_cost_usd": 0.30})
    common.write_jsonl(OUTPUT / "cohort.jsonl", manifest); print(json.dumps({"status": "preflight_ok", "calls": 200}, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--mode", choices=("preflight", "run-all", "aggregate"), required=True); parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args(); load_dotenv(ROOT / ".env"); OUTPUT.mkdir(parents=True, exist_ok=True)
    if args.mode == "preflight": preflight()
    elif args.mode == "run-all": run_all(args.workers)
    else: aggregate()


if __name__ == "__main__": main()
