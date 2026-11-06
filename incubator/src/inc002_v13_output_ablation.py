#!/usr/bin/env python3
"""Paired test of joint-24 versus v13-only output scope, with no extra facts."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
import inc001_simple_joint24 as common


TARGET = "v13"


def target_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [TARGET],
        "properties": {
            TARGET: {
                "type": "object",
                "additionalProperties": False,
                "required": ["위반여부", "근거문구"],
                "properties": {
                    "위반여부": {"type": "integer", "enum": [0, 1]},
                    "근거문구": {"type": ["string", "null"], "maxLength": 2000},
                },
            }
        },
    }


def v13_system_prompt(item_table: dict[str, dict[str, Any]]) -> str:
    definition = item_table[TARGET]
    note = f" (참고: {definition['비고']})" if definition.get("비고") else ""
    return "\n".join(
        [
            "당신은 공공 입찰공고의 법령 위반 여부를 점검한다.",
            "공고문, 제공된 첨부문서, 나라장터 입력 메타를 읽고 아래 한 항목만 판정한다.",
            "판단이 어려우면 0으로 둔다. 키워드만으로 위반을 단정하지 말고 실제 제한과 항목의 적용 조건을 확인한다.",
            f"- {TARGET}: {definition['항목명']}{note}",
            "위반여부가 1이면 근거문구는 제공 문서에 있는 변경 없는 연속 부분문자열이고 500자 이하여야 한다.",
            "위반여부가 0이면 근거문구는 null이다.",
            "JSON 객체 하나만 출력한다: {\"v13\": {\"위반여부\": 0 또는 1, \"근거문구\": 문자열 또는 null}}.",
        ]
    )


def historical_v13_fp(path: Path, labels: dict[str, dict[str, str]]) -> set[str]:
    result: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        payload = json.loads(line)
        record_id = payload.get("id")
        if record_id in labels and labels[record_id][TARGET] == "0":
            if int(payload.get("row", {}).get(TARGET, 0)) == 1:
                result.add(record_id)
    return result


def select_cohort(labels: list[dict[str, str]], historical_fp: set[str], limit: int) -> list[dict[str, str]]:
    positives = [row for row in labels if row[TARGET] == "1"]
    negatives = sorted((row for row in labels if row["id"] in historical_fp), key=lambda row: row["id"])
    result = sorted(positives + negatives[:limit], key=lambda row: row["id"])
    return result


def postprocess_target(payload: dict[str, Any], record: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    cell = payload.get(TARGET)
    if not isinstance(cell, dict) or cell.get("위반여부") not in (0, 1):
        raise ValueError("invalid v13 cell")
    violation = int(cell["위반여부"])
    evidence = cell.get("근거문구") if violation else ""
    evidence = evidence.strip() if isinstance(evidence, str) else ""
    source = "\n".join(document["text"] for document in record["docs"])
    warnings: list[str] = []
    if violation and evidence not in source:
        warnings.append("v13: invalid evidence")
        evidence = ""
    return {"id": record["id"], TARGET: violation, "e13": evidence[:500]}, warnings


def zero_row(record_id: str) -> dict[str, Any]:
    return {"id": record_id, TARGET: 0, "e13": ""}


def metric(rows: list[dict[str, Any]], labels: dict[str, dict[str, str]], records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    tp = fp = fn = valid = positives = 0
    for row in rows:
        gold, prediction = int(labels[row["id"]][TARGET]), int(row[TARGET])
        tp += gold == prediction == 1
        fp += gold == 0 and prediction == 1
        fn += gold == 1 and prediction == 0
        if prediction:
            positives += 1
            source = "\n".join(document["text"] for document in records[row["id"]]["docs"])
            valid += bool(row["e13"]) and row["e13"] in source
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "predicted_positive": tp + fp, "precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0, "evidence_validity": valid / positives if positives else None, "evidence_positive_cases": positives}


def append_checkpoint(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="incubator/configs/inc002_v13_output_ablation.json")
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
    hard_fps = historical_v13_fp(root / config["historical_prediction_path"], labels)
    cohort_labels = select_cohort(label_rows, hard_fps, config["hard_negative_limit"])
    cohort = [record_by_id[row["id"]] for row in cohort_labels]
    systems = {"joint24": common.build_system_prompt(item_table), "v13_only": v13_system_prompt(item_table)}
    schemas = {"joint24": common.judgment_schema(), "v13_only": target_schema()}
    prepared: list[dict[str, Any]] = []
    for record in cohort:
        for policy in ("joint24", "v13_only"):
            messages, rendering = common.build_messages(record, systems[policy], config["max_document_chars_total"])
            prepared.append({"id": record["id"], "policy": policy, "messages": messages, "rendering": rendering, "prompt_sha256": common.sha256_text(json.dumps(messages, ensure_ascii=False, sort_keys=True))})
    plan = {"experiment_id": config["experiment_id"], "hypothesis": "v13-only output lowers v13 false positives without product facts, law chunks, or changed notice context", "comparator": "same-context joint24 control", "target": TARGET, "cohort_count": len(cohort), "gold_positive_count": sum(row[TARGET] == "1" for row in cohort_labels), "historical_v13_fp_negative_count": len(cohort) - sum(row[TARGET] == "1" for row in cohort_labels), "max_requests": config["max_requests"], "max_cost_usd": config["max_cost_usd"], "success_gate": "treatment F1 >= control F1 + 0.10, treatment recall non-decrease, treatment FP <= control FP - 3, evidence validity 1.0", "source_sha256": {"dev": common.sha256_file(data_root / "dev.jsonl.gz"), "labels": common.sha256_file(data_root / "dev_labels.csv")}}
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
            result = common.completion(config, request["messages"], schemas[request["policy"]])
            payload = common.parse_json(result.content)
            if request["policy"] == "joint24":
                judgment, warnings = common.postprocess(payload, record)
                row = {"id": record["id"], TARGET: judgment[TARGET]["위반여부"], "e13": judgment[TARGET]["근거문구"]}
            else:
                row, warnings = postprocess_target(payload, record)
            response = {"raw_response": result.content, "model": result.model, "usage": result.usage, "latency_seconds": result.latency_seconds, "finish_reason": result.finish_reason, "success": True}
        except (RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            row, warnings = zero_row(record["id"]), [f"transport_or_parse_failure: {type(exc).__name__}: {str(exc)[:300]}"]
            response = {"raw_response": "", "model": config["model"], "usage": {}, "latency_seconds": 0.0, "finish_reason": None, "success": False}
        cost = float(response["usage"].get("cost", 0.0) or 0.0)
        total_cost += cost
        entry = {"id": record["id"], "policy": request["policy"], "row": row, "response": response, "warnings": warnings}
        completed[key] = entry
        append_checkpoint(checkpoint_path, entry)
        print(f"[{position}/{len(prepared)}] {request['policy']} cost=${cost:.6f} cumulative=${total_cost:.6f}", flush=True)
        time.sleep(config["min_request_interval_seconds"])
    by_policy: dict[str, list[dict[str, Any]]] = {policy: [] for policy in systems}
    for entry in completed.values():
        by_policy[entry["policy"]].append(entry["row"])
    metrics = {"experiment_id": config["experiment_id"], "reported_cost_usd": total_cost, "request_count": len(completed), "successful_request_count": sum(bool(entry["response"].get("success")) for entry in completed.values()), "policies": {policy: metric(sorted(rows, key=lambda row: row["id"]), labels, record_by_id) for policy, rows in by_policy.items()}}
    control, treatment = metrics["policies"]["joint24"], metrics["policies"]["v13_only"]
    metrics["delta_v13_only_minus_joint24"] = {key: treatment[key] - control[key] for key in ("tp", "fp", "fn", "precision", "recall", "f1")}
    for policy, rows in by_policy.items():
        with (output / f"predictions_{policy}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=("id", TARGET, "e13"), lineterminator="\n")
            writer.writeheader(); writer.writerows(sorted(rows, key=lambda row: row["id"]))
    common.write_jsonl(output / "responses.jsonl", [{"id": entry["id"], "policy": entry["policy"], **entry["response"], "warnings": entry["warnings"]} for entry in completed.values()])
    common.write_json(output / "metrics.json", metrics)
    print(json.dumps({"status": "complete", "metrics": metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
