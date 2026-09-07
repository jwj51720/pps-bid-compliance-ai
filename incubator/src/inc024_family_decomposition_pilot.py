#!/usr/bin/env python3
"""Run the pre-registered INC-024 joint-versus-family mechanism pilot.

No context is truncated or selected by character count.  Every request contains
the complete ordered notice; provider rejection is a stop condition, not a cue
to shorten a prompt.
"""

from __future__ import annotations

import argparse
import csv
import fcntl
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

import inc001_simple_joint24 as common
from inc006_input_budget_ablation import metric
from inc021_rag_family_pass_dev200 import FAMILIES, all_docs, append, post, read_jsonl, schema


def active_system(items: tuple[str, ...], table: dict[str, Any]) -> str:
    definitions = []
    for item in items:
        rule = table[item]
        absence = " [부재탐지]" if item in common.ABSENCE_ITEMS else ""
        note = f" (참고: {rule['비고']})" if rule.get("비고") else ""
        definitions.append(f"- {item}: {rule['항목명']}{absence}{note}")
    return "\n".join([
        "당신은 공공 입찰공고의 법령 위반 여부를 점검한다.",
        "제공된 모든 공고 문서와 나라장터 입력 메타만 읽고 아래 항목을 각각 판정한다.",
        "키워드만으로 1을 정하지 말고 실제 제한·부재·불일치를 확인한다. 판단이 어려우면 0이다.",
        "non-absence 항목이 1이면 근거문구는 제공 문서의 변경 없는 연속 substring이고 500자 이하여야 한다.",
        "0이면 근거문구는 null이다. 부재탐지(v10,v11,v16,v18,v20)는 근거문구를 항상 null로 둔다.",
        "v24는 문서의 명시 내용과 메타의 대응 값이 실제로 다를 때만 1이다.",
        "판정 항목:", *definitions,
        "JSON 객체 하나만 출력한다. 각 항목은 {\"위반여부\": 0 또는 1, \"근거문구\": 문자열 또는 null}이다.",
    ])


def messages(record: dict[str, Any], system: str) -> list[dict[str, str]]:
    user = "\n\n".join([
        f"[공고 ID]\n{record['id']}",
        "[나라장터 입력 메타]\n" + json.dumps(record["meta"], ensure_ascii=False, sort_keys=True),
        "[전체 문서]\n" + all_docs(record),
    ])
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def zero(items: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    return {item: {"위반여부": 0, "근거문구": ""} for item in items}


def write_predictions(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=common.CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="incubator/configs/inc024_family_decomposition_pilot.json")
    parser.add_argument("--mode", choices=("preflight", "run"), default="preflight")
    args = parser.parse_args()
    root = common.repo_root()
    config = json.loads((root / args.config).read_text(encoding="utf-8"))
    load_dotenv(root / ".env")
    output = root / "incubator/runs" / config["experiment_id"]
    output.mkdir(parents=True, exist_ok=True)
    lock = (output / ".run.lock").open("w", encoding="utf-8")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    data = root / config["data_root"]
    records = {row["id"]: row for row in common.read_jsonl_gz(data / "dev.jsonl.gz")}
    labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}
    table = json.loads((data / "data/항목표.json").read_text(encoding="utf-8"))["항목"]
    cohort = json.loads((root / config["cohort_path"]).read_text(encoding="utf-8"))
    cohort_ids = cohort["ordered_ids"]
    if len(cohort_ids) != 12 or len(set(cohort_ids)) != len(cohort_ids):
        raise ValueError("INC-024 preregistered cohort must contain 12 unique IDs")
    if any(record_id not in records for record_id in cohort_ids):
        raise ValueError("cohort ID missing from dev source")
    systems = {"joint": active_system(common.ITEMS, table)}
    systems.update({family: active_system(items, table) for family, items in FAMILIES.items()})
    prepared: list[dict[str, Any]] = []
    for record_id in cohort_ids:
        record = records[record_id]
        prepared.append({"id": record_id, "arm": "joint", "items": common.ITEMS, "messages": messages(record, systems["joint"])})
        for family, items in FAMILIES.items():
            prepared.append({"id": record_id, "arm": family, "items": items, "messages": messages(record, systems[family])})
    for request in prepared:
        request["prompt_sha256"] = common.sha256_text(json.dumps(request["messages"], ensure_ascii=False, sort_keys=True))
    plan = {
        "experiment_id": config["experiment_id"],
        "preregistration": "incubator/docs/inc024_family_decomposition_preregistration.md",
        "changed_variable": "joint 24-item output versus four fixed family outputs",
        "complete_document_policy": "every arm receives the same complete ordered notice; no character/token-derived truncation",
        "cohort": cohort,
        "request_count": len(prepared),
        "request_count_by_arm": {"joint": len(cohort_ids), **{family: len(cohort_ids) for family in FAMILIES}},
        "max_cost_usd": config["max_cost_usd"],
        "source_sha256": {
            "dev": common.sha256_file(data / "dev.jsonl.gz"),
            "labels": common.sha256_file(data / "dev_labels.csv"),
            "item_table": common.sha256_file(data / "data/항목표.json"),
        },
    }
    common.write_json(output / "config.json", config)
    common.write_json(output / "plan.json", plan)
    common.write_jsonl(output / "inputs.jsonl", prepared)
    if len(prepared) != config["max_requests"]:
        raise ValueError("request count differs from preregistered maximum")
    if args.mode == "preflight":
        print(json.dumps({"status": "preflight_ok", **plan}, ensure_ascii=False, indent=2))
        return
    checkpoint = output / "checkpoint.jsonl"
    done = {(row["id"], row["arm"]): row for row in read_jsonl(checkpoint)} if checkpoint.exists() else {}
    if any(float(row["response"]["usage"].get("cost", 0) or 0) >= config["max_cost_usd"] for row in done.values()):
        raise RuntimeError("invalid checkpoint cost entry")

    def run(request: dict[str, Any]) -> dict[str, Any]:
        response: dict[str, Any] = {"raw_response": "", "model": config["model"], "usage": {}, "latency_seconds": 0.0, "finish_reason": None, "success": False}
        try:
            completion = common.completion(config, request["messages"], schema(request["items"]))
            response.update({"raw_response": completion.content, "model": completion.model, "usage": completion.usage, "latency_seconds": completion.latency_seconds, "finish_reason": completion.finish_reason})
            judgment, warnings = post(completion.content, records[request["id"]], request["items"])
            response["success"] = True
        except Exception as exc:
            judgment, warnings = zero(request["items"]), [f"failure:{type(exc).__name__}:{str(exc)[:240]}"]
        return {"id": request["id"], "arm": request["arm"], "judgment": judgment, "response": response, "warnings": warnings}

    remaining = [request for request in prepared if (request["id"], request["arm"]) not in done]
    with ThreadPoolExecutor(max_workers=config["concurrency"]) as executor:
        futures = [executor.submit(run, request) for request in remaining]
        for position, future in enumerate(as_completed(futures), 1):
            entry = future.result()
            done[(entry["id"], entry["arm"])] = entry
            append(checkpoint, entry)
            if position % 10 == 0 or position == len(remaining):
                print(f"[{position}/{len(remaining)}] completed", flush=True)
    reported_cost = sum(float(entry["response"]["usage"].get("cost", 0) or 0) for entry in done.values())
    if reported_cost > config["max_cost_usd"]:
        raise RuntimeError(f"reported cost ceiling exceeded: {reported_cost:.6f}")
    failures = [entry for entry in done.values() if not entry["response"]["success"]]
    if len(failures) / len(prepared) > 0.05:
        raise RuntimeError("transport/parse failure rate exceeds preregistered ceiling")
    joint_rows: list[dict[str, Any]] = []
    family_rows: list[dict[str, Any]] = []
    for record_id in cohort_ids:
        joint_rows.append(common.to_row(record_id, done[(record_id, "joint")]["judgment"]))
        merged = common.zero_judgment()
        for family in FAMILIES:
            merged.update(done[(record_id, family)]["judgment"])
        family_rows.append(common.to_row(record_id, merged))
    joint_metric, joint_items = metric(joint_rows, labels, records)
    family_metric, family_items = metric(family_rows, labels, records)
    changed = []
    for joint_row, family_row in zip(joint_rows, family_rows):
        gold = labels[joint_row["id"]]
        for item in common.ITEMS:
            before, after, target = int(joint_row[item]), int(family_row[item]), int(gold[item])
            if before != after:
                changed.append({"id": joint_row["id"], "item": item, "gold": target, "joint": before, "family": after, "change": "corrected" if after == target else "introduced"})
    metrics = {
        "experiment_id": config["experiment_id"], "request_count": len(done),
        "successful_request_count": len(done) - len(failures), "reported_cost_usd": reported_cost,
        "joint": joint_metric, "family": family_metric,
        "per_item": {"joint": joint_items, "family": family_items}, "changed_cells": changed,
    }
    metrics["delta_family_minus_joint"] = {key: family_metric[key] - joint_metric[key] for key in ("macro_f1", "tp", "fp", "fn", "recall_micro")}
    metrics["changed_cell_summary"] = {kind: sum(row["change"] == kind for row in changed) for kind in ("corrected", "introduced")}
    write_predictions(output / "predictions_joint.csv", joint_rows)
    write_predictions(output / "predictions_family.csv", family_rows)
    common.write_jsonl(output / "responses.jsonl", [{"id": entry["id"], "arm": entry["arm"], **entry["response"], "warnings": entry["warnings"]} for entry in done.values()])
    common.write_json(output / "metrics.json", metrics)
    print(json.dumps({"status": "complete", "metrics": metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
