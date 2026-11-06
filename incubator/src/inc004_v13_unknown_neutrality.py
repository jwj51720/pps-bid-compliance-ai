#!/usr/bin/env python3
"""Paired wording-only repair for the unknown product-fact state in v13."""

from __future__ import annotations

import argparse
import csv
import fcntl
import json
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
import inc001_simple_joint24 as common
import inc002_v13_output_ablation as inc002
import inc003_v13_product_fact as inc003


TARGET = "v13"
CURRENT_POLICY = "product_fact_current_unknown"
NEUTRAL_POLICY = "product_fact_neutral_unknown"


def render_neutral_unknown_context() -> str:
    """Keep the unknown fact, while explicitly prohibiting directional use of it."""
    return "\n".join([
        "[v13 적용성 참고: 공식 경쟁제품 CSV 정확 대조]",
        "제공된 metadata와 문서만으로는 제공된 경쟁제품 CSV와 정확 대조할 세부품명번호를 확인할 수 없다.",
        "이 알 수 없음 상태는 v13 위반 판단을 긍정 또는 부정 어느 방향으로도 바꾸는 근거가 되어서는 안 된다.",
        "v13 판단은 이 참고 상태를 무시하고, 일반 공고 내용과 항목표의 기준만으로 결정한다.",
        "이 참고 상태는 위반 근거나 evidence가 아니다.",
    ])


def append_checkpoint(path: Path, entry: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()


def summarize_unknown_groups(rows: list[dict[str, Any]], labels: dict[str, dict[str, str]]) -> dict[str, dict[str, int]]:
    result = {"gold_positive": {"count": 0, "predicted_positive": 0}, "gold_negative": {"count": 0, "predicted_positive": 0}}
    for row in rows:
        group = "gold_positive" if labels[row["id"]][TARGET] == "1" else "gold_negative"
        result[group]["count"] += 1
        result[group]["predicted_positive"] += row[TARGET]
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="incubator/configs/inc004_v13_unknown_neutrality.json")
    parser.add_argument("--mode", choices=("preflight", "run"), default="preflight")
    args = parser.parse_args()

    root = common.repo_root()
    config = json.loads((root / args.config).read_text(encoding="utf-8"))
    load_dotenv(root / ".env")
    output = root / "incubator" / "runs" / config["experiment_id"]
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
    products = inc003.load_products(root / config["product_csv_path"])
    hard_fps = inc002.historical_v13_fp(root / config["historical_prediction_path"], labels)
    original_cohort = inc002.select_cohort(label_rows, hard_fps, config["hard_negative_limit"])
    cohort = [record_by_id[row["id"]] for row in original_cohort if inc003.product_fact(record_by_id[row["id"]], products)["status"] == "unknown"]
    if len(cohort) != 7:
        raise RuntimeError(f"expected seven pre-registered unknown notices, found {len(cohort)}")

    system = common.build_system_prompt(item_table)
    prepared: list[dict[str, Any]] = []
    for record in cohort:
        fact = inc003.product_fact(record, products)
        for policy in (CURRENT_POLICY, NEUTRAL_POLICY):
            messages, rendering = common.build_messages(record, system, config["max_document_chars_total"])
            messages = [dict(message) for message in messages]
            context = inc003.render_product_context(fact) if policy == CURRENT_POLICY else render_neutral_unknown_context()
            messages[1]["content"] += "\n\n" + context
            prepared.append({"id": record["id"], "policy": policy, "messages": messages, "rendering": rendering, "product_fact": fact, "prompt_sha256": common.sha256_text(json.dumps(messages, ensure_ascii=False, sort_keys=True))})

    gold_positive = sum(labels[record["id"]][TARGET] == "1" for record in cohort)
    plan = {
        "experiment_id": config["experiment_id"],
        "hypothesis": "explicitly neutralizing only the unknown exact-product status restores its v13 recall without restoring its false positives",
        "scope": "only the seven pre-registered unknown-status notices from INC-003",
        "fixed": ["cohort", "product lookup", "joint-24 output", "documents", "metadata", "model", "schema", "document budget"],
        "changed": "only unknown-state natural-language rendering",
        "cohort_count": len(cohort),
        "gold_positive_count": gold_positive,
        "gold_negative_count": len(cohort) - gold_positive,
        "max_requests": config["max_requests"],
        "max_cost_usd": config["max_cost_usd"],
        "success_gate": "neutral policy predicts both unknown positives as 1 and no more than one of five unknown negatives as 1; current-policy paired result is retained for comparison",
        "source_sha256": {"dev": common.sha256_file(data_root / "dev.jsonl.gz"), "labels": common.sha256_file(data_root / "dev_labels.csv"), "product_csv": common.sha256_file(root / config["product_csv_path"])},
    }
    common.write_json(output / "config.json", config)
    common.write_json(output / "plan.json", plan)
    common.write_jsonl(output / "inputs.jsonl", prepared)
    if args.mode == "preflight":
        print(json.dumps({"status": "preflight_ok", **plan, "prepared_requests": len(prepared)}, ensure_ascii=False, indent=2))
        return
    if len(prepared) > config["max_requests"]:
        raise RuntimeError("prepared requests exceed configured ceiling")

    checkpoint_path = output / "checkpoint.jsonl"
    completed: dict[tuple[str, str], dict[str, Any]] = {}
    if checkpoint_path.exists():
        for line in checkpoint_path.read_text(encoding="utf-8").splitlines():
            entry = json.loads(line)
            completed[(entry["id"], entry["policy"])] = entry
    total_cost = sum(float(entry["response"]["usage"].get("cost", 0.0) or 0.0) for entry in completed.values())
    for position, request in enumerate(prepared, 1):
        key = (request["id"], request["policy"])
        if key in completed:
            print(f"[{position}/{len(prepared)}] {request['policy']} resumed", flush=True)
            continue
        if total_cost >= config["max_cost_usd"]:
            raise RuntimeError("reported cost ceiling reached")
        record = record_by_id[request["id"]]
        try:
            result = common.completion(config, request["messages"], common.judgment_schema())
            payload = common.parse_json(result.content)
            judgment, warnings = common.postprocess(payload, record)
            row = {"id": record["id"], TARGET: judgment[TARGET]["위반여부"], "e13": judgment[TARGET]["근거문구"]}
            response = {"raw_response": result.content, "model": result.model, "usage": result.usage, "latency_seconds": result.latency_seconds, "finish_reason": result.finish_reason, "success": True}
        except (RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            row, warnings = inc002.zero_row(record["id"]), [f"transport_or_parse_failure: {type(exc).__name__}: {str(exc)[:300]}"]
            response = {"raw_response": "", "model": config["model"], "usage": {}, "latency_seconds": 0.0, "finish_reason": None, "success": False}
        total_cost += float(response["usage"].get("cost", 0.0) or 0.0)
        entry = {"id": record["id"], "policy": request["policy"], "row": row, "response": response, "warnings": warnings}
        completed[key] = entry
        append_checkpoint(checkpoint_path, entry)
        print(f"[{position}/{len(prepared)}] {request['policy']} cumulative=${total_cost:.6f}", flush=True)
        time.sleep(config["min_request_interval_seconds"])

    by_policy: dict[str, list[dict[str, Any]]] = {CURRENT_POLICY: [], NEUTRAL_POLICY: []}
    for entry in completed.values():
        by_policy[entry["policy"]].append(entry["row"])
    metrics = {"experiment_id": config["experiment_id"], "reported_cost_usd": total_cost, "request_count": len(completed), "successful_request_count": sum(bool(entry["response"].get("success")) for entry in completed.values()), "policies": {policy: inc002.metric(sorted(rows, key=lambda row: row["id"]), labels, record_by_id) for policy, rows in by_policy.items()}, "unknown_groups": {policy: summarize_unknown_groups(rows, labels) for policy, rows in by_policy.items()}}
    current, neutral = metrics["policies"][CURRENT_POLICY], metrics["policies"][NEUTRAL_POLICY]
    metrics["delta_neutral_minus_current"] = {key: neutral[key] - current[key] for key in ("tp", "fp", "fn", "precision", "recall", "f1")}
    for policy, rows in by_policy.items():
        with (output / f"predictions_{policy}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=("id", TARGET, "e13"), lineterminator="\n")
            writer.writeheader()
            writer.writerows(sorted(rows, key=lambda row: row["id"]))
    common.write_jsonl(output / "responses.jsonl", [{"id": entry["id"], "policy": entry["policy"], **entry["response"], "warnings": entry["warnings"]} for entry in completed.values()])
    common.write_json(output / "metrics.json", metrics)
    print(json.dumps({"status": "complete", "metrics": metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
