#!/usr/bin/env python3
"""Paired ordered-document budget ablation on the frozen INC-001 cohort."""

from __future__ import annotations

import argparse
import csv
import fcntl
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

import inc001_simple_joint24 as common


def request_key(row: dict[str, Any]) -> tuple[str, str]:
    return row["id"], row["policy"]


def append_checkpoint(path: Path, entry: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()


def source_chars(record: dict[str, Any]) -> int:
    return sum(len(document["text"]) for document in record["docs"])


def metric(rows: list[dict[str, Any]], labels: dict[str, dict[str, str]], records: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    result, per_item = common.evaluate(rows, labels)
    tp = sum(item["tp"] for item in per_item)
    fp = sum(item["fp"] for item in per_item)
    fn = sum(item["fn"] for item in per_item)
    positive = sum(item["predicted_positive"] for item in per_item)
    valid = 0
    for row in rows:
        source = "\n".join(document["text"] for document in records[row["id"]]["docs"])
        for index, item in enumerate(common.ITEMS, 1):
            if item not in common.ABSENCE_ITEMS and row[item] == 1:
                valid += bool(row[f"e{index}"]) and row[f"e{index}"] in source
    result.update({"tp": tp, "fp": fp, "fn": fn, "positive_predictions": positive, "recall_micro": tp / (tp + fn) if tp + fn else 0.0, "evidence_validity": valid / positive if positive else None, "evidence_positive_cases": positive})
    return result, per_item


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="incubator/configs/inc006_input_budget_ablation.json")
    parser.add_argument("--mode", choices=("preflight", "run"), default="preflight")
    args = parser.parse_args()
    root = common.repo_root()
    config = json.loads((root / args.config).read_text(encoding="utf-8"))
    load_dotenv(root / ".env")
    output = root / "incubator/runs" / config["experiment_id"]
    output.mkdir(parents=True, exist_ok=True)
    lock_handle = (output / ".run.lock").open("w", encoding="utf-8")
    try:
        fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise RuntimeError(f"another run already owns {output}") from exc
    data_root = root / config["data_root"]
    records = common.read_jsonl_gz(data_root / "dev.jsonl.gz")
    record_by_id = {record["id"]: record for record in records}
    label_rows = common.read_csv(data_root / "dev_labels.csv")
    labels = {row["id"]: row for row in label_rows}
    item_table = json.loads((data_root / "data" / "항목표.json").read_text(encoding="utf-8"))["항목"]
    historical_fp = common.load_historical_false_positives(root / config["historical_prediction_path"], labels)
    cohort_labels, cohort_meta = common.select_cohort(label_rows, historical_fp, config["positive_seed_limit"], config["hard_negative_limit"])
    cohort = [record_by_id[row["id"]] for row in cohort_labels]
    system = common.build_system_prompt(item_table)
    prepared: list[dict[str, Any]] = []
    coverage: dict[str, dict[str, float]] = {}
    for policy, budget in config["document_char_budgets"].items():
        included = total = complete = 0
        for record in cohort:
            messages, rendering = common.build_messages(record, system, budget)
            included_chars = sum(part["chars"] for part in rendering["included_documents"])
            total_chars = source_chars(record)
            included += included_chars
            total += total_chars
            complete += included_chars == total_chars
            prepared.append({"id": record["id"], "policy": policy, "budget": budget, "messages": messages, "rendering": rendering, "prompt_sha256": common.sha256_text(json.dumps(messages, ensure_ascii=False, sort_keys=True))})
        coverage[policy] = {"budget_chars": budget, "included_document_chars": included, "source_document_chars": total, "coverage": included / total, "complete_notice_count": complete}
    plan = {"experiment_id": config["experiment_id"], "hypothesis": "raising only the ordered document prefix from 4,000 to 12,000 characters improves joint-24 macro F1 through greater source coverage", "comparator": "contemporary 4,000-character arm", "cohort": cohort_meta, "coverage_preflight": coverage, "max_requests": config["max_requests"], "max_cost_usd": config["max_cost_usd"], "success_gate": "12000 macro F1 >= 4000 + 0.02, micro recall non-decrease, evidence validity decline <=0.05, and no item gains >3 false positives", "source_sha256": {"dev": common.sha256_file(data_root / "dev.jsonl.gz"), "labels": common.sha256_file(data_root / "dev_labels.csv"), "item_table": common.sha256_file(data_root / "data" / "항목표.json")}}
    common.write_json(output / "config.json", config)
    common.write_json(output / "plan.json", plan)
    common.write_jsonl(output / "inputs.jsonl", prepared)
    if args.mode == "preflight":
        print(json.dumps({"status": "preflight_ok", **plan, "prepared_requests": len(prepared)}, ensure_ascii=False, indent=2))
        return
    if len(prepared) > config["max_requests"]:
        raise RuntimeError("prepared requests exceed configured ceiling")
    checkpoint = output / "checkpoint.jsonl"
    completed: dict[tuple[str, str], dict[str, Any]] = {}
    if checkpoint.exists():
        for entry in jsonl(checkpoint):
            completed[request_key(entry)] = entry
    reported_cost = sum(float(entry["response"]["usage"].get("cost", 0) or 0) for entry in completed.values())
    for position, request in enumerate(prepared, 1):
        key = request_key(request)
        if key in completed:
            print(f"[{position}/{len(prepared)}] {key[1]} resumed", flush=True)
            continue
        if reported_cost >= config["max_cost_usd"]:
            raise RuntimeError("reported cost ceiling reached")
        record = record_by_id[request["id"]]
        response: dict[str, Any] | None = None
        warnings: list[str] = []
        try:
            completion = common.completion(config, request["messages"], common.judgment_schema())
            response = {"raw_response": completion.content, "model": completion.model, "usage": completion.usage, "latency_seconds": completion.latency_seconds, "finish_reason": completion.finish_reason, "success": False}
            payload = common.parse_json(completion.content)
            judgment, warnings = common.postprocess(payload, record)
            row = common.to_row(record["id"], judgment)
            response["success"] = True
        except (RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            if response is None:
                response = {"raw_response": "", "model": config["model"], "usage": {}, "latency_seconds": 0.0, "finish_reason": None, "success": False}
            row = common.to_row(record["id"], common.zero_judgment())
            warnings = [f"transport_or_parse_failure: {type(exc).__name__}: {str(exc)[:300]}"]
        assert response is not None
        reported_cost += float(response["usage"].get("cost", 0) or 0)
        entry = {"id": request["id"], "policy": request["policy"], "row": row, "response": response, "warnings": warnings}
        completed[key] = entry
        append_checkpoint(checkpoint, entry)
        print(f"[{position}/{len(prepared)}] {request['policy']} cumulative=${reported_cost:.6f}", flush=True)
        time.sleep(config["min_request_interval_seconds"])
    by_policy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in completed.values():
        by_policy[entry["policy"]].append(entry["row"])
    metrics: dict[str, Any] = {"experiment_id": config["experiment_id"], "request_count": len(completed), "successful_request_count": sum(entry["response"]["success"] for entry in completed.values()), "reported_cost_usd": reported_cost, "coverage_preflight": coverage, "policies": {}, "per_item": {}}
    for policy, rows in by_policy.items():
        result, items = metric(sorted(rows, key=lambda row: row["id"]), labels, record_by_id)
        metrics["policies"][policy] = result
        metrics["per_item"][policy] = items
        with (output / f"predictions_{policy}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=common.CSV_COLUMNS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(sorted(rows, key=lambda row: row["id"]))
    small, large = metrics["policies"]["ordered_4000"], metrics["policies"]["ordered_12000"]
    metrics["delta_12000_minus_4000"] = {key: large[key] - small[key] for key in ("macro_f1", "tp", "fp", "fn", "recall_micro", "evidence_validity")}
    metrics["new_false_positives_by_item"] = {item: max(0, large_item["fp"] - small_item["fp"]) for item, large_item in zip(common.ITEMS, metrics["per_item"]["ordered_12000"]) for small_item in [metrics["per_item"]["ordered_4000"][int(item[1:]) - 1]]}
    common.write_jsonl(output / "responses.jsonl", [{"id": entry["id"], "policy": entry["policy"], **entry["response"], "warnings": entry["warnings"]} for entry in completed.values()])
    common.write_json(output / "metrics.json", metrics)
    print(json.dumps({"status": "complete", "metrics": metrics}, ensure_ascii=False, indent=2))


def jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


if __name__ == "__main__":
    main()
