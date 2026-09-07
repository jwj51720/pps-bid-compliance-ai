#!/usr/bin/env python3
"""All-dev confirmation runner for the frozen INC-029 law-context policy."""

from __future__ import annotations

import argparse
import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

import inc001_simple_joint24 as common
import inc029_restriction_law_context as base


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "incubator/runs/inc030_restriction_law_context_dev200"


def ids() -> list[str]:
    records, _, _ = base.load_inputs()
    return sorted(records)


def confusion(entries: dict[str, dict[str, Any]], labels: dict[str, dict[str, str]], sample: list[str]) -> tuple[float, int, int, int]:
    scores, total_tp, total_fp, total_fn = [], 0, 0, 0
    for item in base.ITEMS:
        tp = fp = fn = 0
        for record_id in sample:
            gold = int(labels[record_id][item])
            pred = int(entries[record_id].get("judgment", {}).get(item, {}).get("위반여부", 0))
            tp += gold and pred; fp += not gold and pred; fn += gold and not pred
        scores.append(base.f1(tp, fp, fn)); total_tp += tp; total_fp += fp; total_fn += fn
    return sum(scores) / len(scores), total_tp, total_fp, total_fn


def aggregate() -> None:
    records, labels, _ = base.load_inputs(); record_ids = ids(); arms: dict[str, dict[str, dict[str, Any]]] = {"control": {}, "law": {}}
    for record_id in record_ids:
        for arm in arms:
            path = OUTPUT / "records" / f"{record_id}_{arm}.json"
            if path.exists(): arms[arm][record_id] = json.loads(path.read_text(encoding="utf-8"))
    report: dict[str, Any] = {"experiment_id": "inc030_restriction_law_context_dev200", "requested_calls": 400, "observed_calls": sum(len(v) for v in arms.values()), "arms": {}}
    for arm, entries in arms.items():
        macro, tp, fp, fn = confusion(entries, labels, list(entries))
        positives = valid = 0
        per_item = []
        for item in base.ITEMS:
            item_tp = item_fp = item_fn = 0
            for record_id, entry in entries.items():
                gold = int(labels[record_id][item])
                pred = int(entry.get("judgment", {}).get(item, {}).get("위반여부", 0))
                item_tp += gold and pred; item_fp += not gold and pred; item_fn += gold and not pred
            per_item.append({"item": item, "tp": item_tp, "fp": item_fp, "fn": item_fn, "f1": base.f1(item_tp, item_fp, item_fn)})
        for record_id, entry in entries.items():
            source = "\n".join(doc["text"] for doc in records[record_id]["docs"])
            for item in base.ITEMS:
                if entry.get("judgment", {}).get(item, {}).get("위반여부", 0):
                    positives += 1; valid += bool(entry["judgment"][item]["근거문구"] in source)
        report["arms"][arm] = {"successful_calls": sum(entry["success"] for entry in entries.values()), "failure_count": sum(not entry["success"] for entry in entries.values()), "macro_f1": macro, "tp": tp, "fp": fp, "fn": fn, "recall_micro": tp / (tp + fn) if tp + fn else 0.0, "evidence_validity": valid / positives if positives else None, "reported_cost_usd": sum(float(entry["usage"].get("cost", 0) or 0) for entry in entries.values()), "per_item": per_item}
    if len(arms["control"]) == len(record_ids) and len(arms["law"]) == len(record_ids):
        rng = random.Random(20260905); deltas = []
        for _ in range(10_000):
            sample = [rng.choice(record_ids) for _ in record_ids]
            deltas.append(confusion(arms["law"], labels, sample)[0] - confusion(arms["control"], labels, sample)[0])
        deltas.sort(); report["bootstrap_delta_law_minus_control"] = {"replicates": 10_000, "seed": 20260905, "p05": deltas[499], "median": deltas[4999], "p95": deltas[9499]}
    common.write_json(OUTPUT / "metrics.json", report); common.write_jsonl(OUTPUT / "responses.jsonl", [entry for arm in arms.values() for entry in arm.values()]); print(json.dumps(report, ensure_ascii=False, indent=2))


def preflight() -> None:
    records, _, table = base.load_inputs(); manifest = []
    for record_id in ids():
        record = records[record_id]
        manifest.append({"id": record_id, "contract_law": record["meta"]["적용계약법"], "control_prompt_sha256": common.sha256_text(json.dumps(base.messages(record, table, "control"), ensure_ascii=False, sort_keys=True)), "law_prompt_sha256": common.sha256_text(json.dumps(base.messages(record, table, "law"), ensure_ascii=False, sort_keys=True))})
    common.write_json(OUTPUT / "config.json", {"items": base.ITEMS, "model": base.request_config(), "max_calls": 400, "max_cost_usd": 0.70, "bootstrap_replicates": 10_000, "bootstrap_seed": 20260905})
    common.write_jsonl(OUTPUT / "cohort.jsonl", manifest); print(json.dumps({"status": "preflight_ok", "notice_count": len(manifest), "calls": 400}, ensure_ascii=False))


def run_one(record_id: str, arm: str) -> None:
    base.OUTPUT = OUTPUT
    if (OUTPUT / "records" / f"{record_id}_{arm}.json").exists():
        return
    base.run_one(record_id, arm)


def run_all(workers: int) -> None:
    jobs = [(record_id, arm) for record_id in ids() for arm in ("control", "law")]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_one, record_id, arm) for record_id, arm in jobs]
        for index, future in enumerate(as_completed(futures), 1):
            future.result()
            if index % workers == 0 or index == len(futures):
                print(f"completed={index}/{len(futures)}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--mode", choices=("preflight", "run", "run-all", "aggregate"), required=True); parser.add_argument("--id"); parser.add_argument("--arm", choices=("control", "law")); parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args(); load_dotenv(ROOT / ".env"); OUTPUT.mkdir(parents=True, exist_ok=True)
    if args.mode == "preflight": preflight()
    elif args.mode == "aggregate": aggregate()
    elif args.mode == "run-all": run_all(args.workers)
    elif not args.id or not args.arm: parser.error("run requires --id and --arm")
    else: run_one(args.id, args.arm)


if __name__ == "__main__": main()
