#!/usr/bin/env python3
"""Paired joint-24 ablation: add only an official CSV exact product fact for v13."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
import inc001_simple_joint24 as common
import inc002_v13_output_ablation as inc002


TARGET = "v13"
CODE = re.compile(r"\d{10}")


def load_products(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {row["세부품명번호"]: row["세부품명"] for row in csv.DictReader(handle) if re.fullmatch(r"\d{10}", row.get("세부품명번호", ""))}


def product_fact(record: dict[str, Any], products: dict[str, str]) -> dict[str, Any]:
    meta_codes = sorted(set(CODE.findall(str(record["meta"].get("세부품명번호목록") or ""))))
    document_codes = sorted({code for document in record["docs"] for code in CODE.findall(document["text"])})
    matched = sorted((set(meta_codes) | set(document_codes)) & set(products))
    if matched:
        status = "matched"
    elif meta_codes:
        status = "not_matched"
    else:
        status = "unknown"
    return {"status": status, "metadata_codes": meta_codes, "document_codes": document_codes, "matched_codes": matched, "matched_product_names": [products[code] for code in matched]}


def render_product_context(fact: dict[str, Any]) -> str:
    if fact["status"] == "matched":
        detail = ", ".join(fact["matched_product_names"])
        statement = f"나라장터 metadata 또는 제공 문서에 명시된 세부품명은 제공된 경쟁제품 CSV와 정확히 일치한다: {detail}."
    elif fact["status"] == "not_matched":
        statement = "나라장터 metadata의 명시 세부품명번호는 제공된 경쟁제품 CSV와 정확히 일치하지 않는다."
    else:
        statement = "나라장터 metadata에 정확 대조할 세부품명번호가 없어 경쟁제품 여부를 확인할 수 없다."
    return "\n".join([
        "[v13 적용성 참고: 공식 경쟁제품 CSV 정확 대조]",
        statement,
        "이 사실은 v13의 경쟁제품 적용대상을 검토하는 보조 정보일 뿐, 그 자체가 위반 근거나 evidence는 아니다.",
        "정확 대조 불가 또는 불일치는 경쟁제품이 아니라고 추측하는 근거가 아니다.",
    ])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="incubator/configs/inc003_v13_product_fact.json")
    parser.add_argument("--mode", choices=("preflight", "run"), default="preflight")
    args = parser.parse_args()
    root = common.repo_root()
    config = json.loads((root / args.config).read_text(encoding="utf-8"))
    load_dotenv(root / ".env")
    output = root / "incubator" / "runs" / config["experiment_id"]
    output.mkdir(parents=True, exist_ok=True)
    data_root = root / config["data_root"]
    records = common.read_jsonl_gz(data_root / "dev.jsonl.gz")
    record_by_id = {record["id"]: record for record in records}
    label_rows = common.read_csv(data_root / "dev_labels.csv")
    labels = {row["id"]: row for row in label_rows}
    item_table = json.loads((data_root / "data" / "항목표.json").read_text(encoding="utf-8"))["항목"]
    products = load_products(root / config["product_csv_path"])
    hard_fps = inc002.historical_v13_fp(root / config["historical_prediction_path"], labels)
    cohort_labels = inc002.select_cohort(label_rows, hard_fps, config["hard_negative_limit"])
    cohort = [record_by_id[row["id"]] for row in cohort_labels]
    system = common.build_system_prompt(item_table)
    prepared: list[dict[str, Any]] = []
    status_counts: dict[str, int] = {"matched": 0, "not_matched": 0, "unknown": 0}
    for record in cohort:
        fact = product_fact(record, products)
        status_counts[fact["status"]] += 1
        for policy in ("joint24_control", "joint24_product_fact"):
            messages, rendering = common.build_messages(record, system, config["max_document_chars_total"])
            if policy == "joint24_product_fact":
                messages = [dict(message) for message in messages]
                messages[1]["content"] += "\n\n" + render_product_context(fact)
            prepared.append({"id": record["id"], "policy": policy, "messages": messages, "rendering": rendering, "product_fact": fact if policy.endswith("fact") else None, "prompt_sha256": common.sha256_text(json.dumps(messages, ensure_ascii=False, sort_keys=True))})
    plan = {"experiment_id": config["experiment_id"], "hypothesis": "a concise official CSV exact product applicability fact reduces v13 false positives while retaining joint-24 recall", "comparator": "same-context joint-24 control", "target": TARGET, "cohort_count": len(cohort), "gold_positive_count": sum(row[TARGET] == "1" for row in cohort_labels), "historical_v13_fp_negative_count": len(cohort) - sum(row[TARGET] == "1" for row in cohort_labels), "product_fact_status_counts": status_counts, "max_requests": config["max_requests"], "max_cost_usd": config["max_cost_usd"], "success_gate": "treatment v13 F1 >= control + 0.10, recall non-decrease, FP <= control - 3, evidence validity non-decrease", "source_sha256": {"dev": common.sha256_file(data_root / "dev.jsonl.gz"), "labels": common.sha256_file(data_root / "dev_labels.csv"), "product_csv": common.sha256_file(root / config["product_csv_path"])}}
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
        inc002.append_checkpoint(checkpoint_path, entry)
        print(f"[{position}/{len(prepared)}] {request['policy']} cumulative=${total_cost:.6f}", flush=True)
        time.sleep(config["min_request_interval_seconds"])
    by_policy: dict[str, list[dict[str, Any]]] = {"joint24_control": [], "joint24_product_fact": []}
    for entry in completed.values():
        by_policy[entry["policy"]].append(entry["row"])
    metrics = {"experiment_id": config["experiment_id"], "reported_cost_usd": total_cost, "request_count": len(completed), "successful_request_count": sum(bool(entry["response"].get("success")) for entry in completed.values()), "policies": {policy: inc002.metric(sorted(rows, key=lambda row: row["id"]), labels, record_by_id) for policy, rows in by_policy.items()}}
    control, treatment = metrics["policies"]["joint24_control"], metrics["policies"]["joint24_product_fact"]
    metrics["delta_product_fact_minus_control"] = {key: treatment[key] - control[key] for key in ("tp", "fp", "fn", "precision", "recall", "f1")}
    for policy, rows in by_policy.items():
        with (output / f"predictions_{policy}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=("id", TARGET, "e13"), lineterminator="\n")
            writer.writeheader(); writer.writerows(sorted(rows, key=lambda row: row["id"]))
    common.write_jsonl(output / "responses.jsonl", [{"id": entry["id"], "policy": entry["policy"], **entry["response"], "warnings": entry["warnings"]} for entry in completed.values()])
    common.write_json(output / "metrics.json", metrics)
    print(json.dumps({"status": "complete", "metrics": metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
