#!/usr/bin/env python3
"""Frozen-card all-dev confirmation for the INC-014 v20 signal."""

from __future__ import annotations

import argparse
import fcntl
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from transformers import AutoTokenizer

import inc001_simple_joint24 as common
import inc014_v20_card_pilot as pilot
from inc007_token_admission_profile import count_messages


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="incubator/configs/inc015_v20_card_dev200_confirmation.json")
    parser.add_argument("--mode", choices=("preflight", "run"), default="preflight")
    args = parser.parse_args()
    root = common.repo_root()
    config = json.loads((root / args.config).read_text(encoding="utf-8"))
    load_dotenv(root / ".env")
    output = root / "incubator/runs" / config["experiment_id"]
    output.mkdir(parents=True, exist_ok=True)
    lock = (output / ".run.lock").open("w", encoding="utf-8")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    data_root = root / config["data_root"]
    records = {row["id"]: row for row in common.read_jsonl_gz(data_root / "dev.jsonl.gz")}
    labels = {row["id"]: row for row in common.read_csv(data_root / "dev_labels.csv")}
    card_path = root / config["card_path"]
    card = json.loads(card_path.read_text(encoding="utf-8"))
    card_sha = common.sha256_file(card_path)
    if card_sha != config["expected_card_sha256"]:
        raise RuntimeError("frozen card hash does not match config")
    card_context = pilot.card_for_prompt(card)
    tokenizer = AutoTokenizer.from_pretrained(config["model_tokenizer"])
    budget = config["max_model_len"] - config["output_reserve_tokens"]
    requests: list[dict[str, Any]] = []
    for record_id in sorted(records):
        for policy, context in (("control", None), ("law_card", card_context)):
            messages = pilot.build_messages(records[record_id], context)
            prompt_tokens = count_messages(tokenizer, messages)
            if prompt_tokens > budget:
                raise RuntimeError(f"prompt exceeds exact budget: {record_id} {policy} {prompt_tokens}>{budget}")
            requests.append({"id": record_id, "policy": policy, "messages": messages, "prompt_tokens": prompt_tokens, "prompt_sha256": common.sha256_text(json.dumps(messages, ensure_ascii=False, sort_keys=True))})
    projected = sum(row["prompt_tokens"] * config["observed_input_cost_per_token_usd"] + config["assumed_completion_tokens"] * config["observed_completion_cost_per_token_usd"] for row in requests)
    plan = {
        "experiment_id": config["experiment_id"], "hypothesis": "the frozen INC-014 card improves v20 F1 across all dev notices without a false-positive regression",
        "changed_variable": "the same frozen law fact card only", "cohort_count": len(records), "positive_count": sum(row["v20"] == "1" for row in labels.values()), "negative_count": sum(row["v20"] == "0" for row in labels.values()),
        "request_count": len(requests), "full_notice_context": True, "prompt_token_budget": budget, "prompt_token_max": max(row["prompt_tokens"] for row in requests), "prompt_token_mean": sum(row["prompt_tokens"] for row in requests) / len(requests),
        "projected_cost_usd": projected, "max_cost_usd": config["max_cost_usd"],
        "success_gate": "law_card v20 F1 > control; law_card recall >= control; law_card FP <= control FP; zero transport/schema failures", "source_sha256": {"dev": common.sha256_file(data_root / "dev.jsonl.gz"), "labels": common.sha256_file(data_root / "dev_labels.csv"), "card": card_sha},
    }
    common.write_json(output / "config.json", config)
    common.write_json(output / "plan.json", plan)
    common.write_jsonl(output / "inputs.jsonl", requests)
    if projected > config["max_cost_usd"]:
        raise RuntimeError(f"projected cost exceeds ceiling: {projected:.4f}")
    if args.mode == "preflight":
        print(json.dumps({"status": "preflight_ok", **plan}, ensure_ascii=False, indent=2))
        return
    if len(requests) > config["max_requests"]:
        raise RuntimeError("request ceiling exceeded")
    checkpoint = output / "checkpoint.jsonl"
    done = {(row["id"], row["policy"]): row for row in read_jsonl(checkpoint)} if checkpoint.exists() else {}
    remaining = [row for row in requests if (row["id"], row["policy"]) not in done]

    def run(request: dict[str, Any]) -> dict[str, Any]:
        response: dict[str, Any] = {"raw_response": "", "model": config["model"], "usage": {}, "latency_seconds": 0.0, "finish_reason": None, "success": False}
        try:
            completion = common.completion(config, request["messages"], pilot.V20_SCHEMA)
            response.update({"raw_response": completion.content, "model": completion.model, "usage": completion.usage, "latency_seconds": completion.latency_seconds, "finish_reason": completion.finish_reason})
            prediction = pilot.parse_v20(completion.content)
            response["success"] = True
            warning = None
        except Exception as exc:
            prediction, warning = 0, f"failure:{type(exc).__name__}:{str(exc)[:240]}"
        return {"id": request["id"], "policy": request["policy"], "prediction": prediction, "response": response, "warning": warning}

    with ThreadPoolExecutor(max_workers=config["concurrency"]) as executor:
        futures = [executor.submit(run, request) for request in remaining]
        for index, future in enumerate(as_completed(futures), 1):
            row = future.result()
            done[(row["id"], row["policy"])] = row
            append_jsonl(checkpoint, row)
            if index % 20 == 0 or index == len(remaining):
                print(f"[{index}/{len(remaining)}] completed", flush=True)
    entries = list(done.values())
    by_policy = {policy: sorted([row for row in entries if row["policy"] == policy], key=lambda row: row["id"]) for policy in ("control", "law_card")}
    metrics = {"experiment_id": config["experiment_id"], "request_count": len(entries), "successful_request_count": sum(row["response"]["success"] for row in entries), "reported_cost_usd": sum(float(row["response"]["usage"].get("cost", 0) or 0) for row in entries), "policies": {policy: pilot.score(rows, labels) for policy, rows in by_policy.items()}}
    control, treatment = metrics["policies"]["control"], metrics["policies"]["law_card"]
    metrics["delta_law_card_minus_control"] = {key: treatment[key] - control[key] for key in ("tp", "fp", "fn", "precision", "recall", "f1")}
    metrics["success_gate_pass"] = treatment["f1"] > control["f1"] and treatment["recall"] >= control["recall"] and treatment["fp"] <= control["fp"] and metrics["successful_request_count"] == len(requests)
    common.write_jsonl(output / "responses.jsonl", [{"id": row["id"], "policy": row["policy"], **row["response"], "warning": row["warning"]} for row in entries])
    common.write_jsonl(output / "predictions.jsonl", [{"id": row["id"], "policy": row["policy"], "v20": row["prediction"]} for row in entries])
    common.write_json(output / "metrics.json", metrics)
    print(json.dumps({"status": "complete", "metrics": metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
