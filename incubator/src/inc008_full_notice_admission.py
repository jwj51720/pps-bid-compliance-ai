#!/usr/bin/env python3
"""Paired full-notice vs prefix pilot with exact Gemma-token admission."""

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
from transformers import AutoTokenizer

import inc001_simple_joint24 as common
import inc006_input_budget_ablation as inc006
import inc007_token_admission_profile as inc007


POLICIES = ("prefix_12000", "full_notice")


def append_checkpoint(path: Path, entry: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="incubator/configs/inc008_full_notice_admission.json")
    parser.add_argument("--mode", choices=("preflight", "run"), default="preflight")
    args = parser.parse_args()
    root = common.repo_root()
    config = json.loads((root / args.config).read_text(encoding="utf-8"))
    load_dotenv(root / ".env")
    output = root / "incubator/runs" / config["experiment_id"]
    output.mkdir(parents=True, exist_ok=True)
    lock = (output / ".run.lock").open("w", encoding="utf-8")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise RuntimeError(f"another run already owns {output}") from exc
    data_root = root / config["data_root"]
    records = common.read_jsonl_gz(data_root / "dev.jsonl.gz")
    by_id = {record["id"]: record for record in records}
    label_rows = common.read_csv(data_root / "dev_labels.csv")
    labels = {row["id"]: row for row in label_rows}
    items = json.loads((data_root / "data/항목표.json").read_text(encoding="utf-8"))["항목"]
    historical = common.load_historical_false_positives(root / config["historical_prediction_path"], labels)
    cohort_rows, cohort_meta = common.select_cohort(label_rows, historical, config["positive_seed_limit"], config["hard_negative_limit"])
    cohort = [by_id[row["id"]] for row in cohort_rows]
    system = common.build_system_prompt(items)
    tokenizer = AutoTokenizer.from_pretrained(config["model_tokenizer"])
    budget = config["max_model_len"] - config["output_reserve_tokens"]
    prepared: list[dict[str, Any]] = []
    token_summary: dict[str, list[int]] = defaultdict(list)
    for record in cohort:
        for policy in POLICIES:
            limit = config["prefix_chars"] if policy == "prefix_12000" else 10**9
            messages, rendering = common.build_messages(record, system, limit)
            tokens = inc007.count_messages(tokenizer, messages)
            if tokens > budget:
                raise RuntimeError(f"{record['id']} {policy} exceeds exact budget: {tokens}>{budget}")
            token_summary[policy].append(tokens)
            prepared.append({"id": record["id"], "policy": policy, "messages": messages, "rendering": rendering, "exact_prompt_tokens": tokens, "prompt_sha256": common.sha256_text(json.dumps(messages, ensure_ascii=False, sort_keys=True))})
    plan = {"experiment_id": config["experiment_id"], "hypothesis": "full exact-token-admitted ordered notice improves over the diagnostic 12000-character prefix", "cohort": cohort_meta, "prompt_budget_tokens": budget, "exact_prompt_tokens": {policy: {"min": min(values), "mean": sum(values) / len(values), "max": max(values)} for policy, values in token_summary.items()}, "max_requests": config["max_requests"], "max_cost_usd": config["max_cost_usd"], "success_gate": "full Macro F1 >= prefix +0.02, micro recall non-decrease, evidence validity decline <=0.05, no item +>3 FP", "source_sha256": {"dev": common.sha256_file(data_root / "dev.jsonl.gz"), "labels": common.sha256_file(data_root / "dev_labels.csv")}}
    common.write_json(output / "config.json", config)
    common.write_json(output / "plan.json", plan)
    common.write_jsonl(output / "inputs.jsonl", prepared)
    if args.mode == "preflight":
        print(json.dumps({"status": "preflight_ok", **plan, "prepared_requests": len(prepared)}, ensure_ascii=False, indent=2))
        return
    checkpoint = output / "checkpoint.jsonl"
    completed = {(entry["id"], entry["policy"]): entry for entry in read_jsonl(checkpoint)} if checkpoint.exists() else {}
    cost = sum(float(entry["response"]["usage"].get("cost", 0) or 0) for entry in completed.values())
    for index, request in enumerate(prepared, 1):
        key = (request["id"], request["policy"])
        if key in completed:
            print(f"[{index}/{len(prepared)}] resumed", flush=True)
            continue
        if cost >= config["max_cost_usd"]:
            raise RuntimeError("reported cost ceiling reached")
        record = by_id[request["id"]]
        response: dict[str, Any] | None = None
        try:
            result = common.completion(config, request["messages"], common.judgment_schema())
            response = {"raw_response": result.content, "model": result.model, "usage": result.usage, "latency_seconds": result.latency_seconds, "finish_reason": result.finish_reason, "success": False}
            judgment, warnings = common.postprocess(common.parse_json(result.content), record)
            row = common.to_row(record["id"], judgment)
            response["success"] = True
        except (RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            response = response or {"raw_response": "", "model": config["model"], "usage": {}, "latency_seconds": 0.0, "finish_reason": None, "success": False}
            row, warnings = common.to_row(record["id"], common.zero_judgment()), [f"transport_or_parse_failure: {type(exc).__name__}: {str(exc)[:300]}"]
        cost += float(response["usage"].get("cost", 0) or 0)
        entry = {"id": record["id"], "policy": request["policy"], "row": row, "response": response, "warnings": warnings}
        completed[key] = entry
        append_checkpoint(checkpoint, entry)
        print(f"[{index}/{len(prepared)}] {request['policy']} cumulative=${cost:.6f}", flush=True)
        time.sleep(config["min_request_interval_seconds"])
    rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in completed.values():
        rows[entry["policy"]].append(entry["row"])
    metrics: dict[str, Any] = {"experiment_id": config["experiment_id"], "request_count": len(completed), "successful_request_count": sum(entry["response"]["success"] for entry in completed.values()), "reported_cost_usd": cost, "policies": {}, "per_item": {}}
    for policy in POLICIES:
        result, per_item = inc006.metric(sorted(rows[policy], key=lambda row: row["id"]), labels, by_id)
        metrics["policies"][policy], metrics["per_item"][policy] = result, per_item
        with (output / f"predictions_{policy}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=common.CSV_COLUMNS, lineterminator="\n")
            writer.writeheader(); writer.writerows(sorted(rows[policy], key=lambda row: row["id"]))
    prefix, full = metrics["policies"]["prefix_12000"], metrics["policies"]["full_notice"]
    metrics["delta_full_minus_prefix"] = {field: full[field] - prefix[field] for field in ("macro_f1", "tp", "fp", "fn", "recall_micro", "evidence_validity")}
    metrics["new_false_positives_by_item"] = {item: max(0, full_item["fp"] - metrics["per_item"]["prefix_12000"][index]["fp"]) for index, (item, full_item) in enumerate(zip(common.ITEMS, metrics["per_item"]["full_notice"]))}
    common.write_jsonl(output / "responses.jsonl", [{"id": entry["id"], "policy": entry["policy"], **entry["response"], "warnings": entry["warnings"]} for entry in completed.values()])
    common.write_json(output / "metrics.json", metrics)
    print(json.dumps({"status": "complete", "metrics": metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
