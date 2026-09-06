#!/usr/bin/env python3
"""Concurrent paired active-item pilot for frozen v19--v21 source windows."""

from __future__ import annotations

import argparse
import csv
import fcntl
import json
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

import inc001_simple_joint24 as common


ITEMS = ("v19", "v20", "v21")
ABSENCE = frozenset({"v20"})
DOC_ORDER = common.DOCUMENT_ORDER


def schema() -> dict[str, Any]:
    return {"type": "object", "additionalProperties": False, "required": list(ITEMS), "properties": {item: {"type": "object", "additionalProperties": False, "required": ["위반여부", "근거문구"], "properties": {"위반여부": {"type": "integer", "enum": [0, 1]}, "근거문구": {"type": ["string", "null"], "maxLength": 2000}}} for item in ITEMS}}


def system_prompt(item_table: dict[str, Any]) -> str:
    lines = [f"- {item}: {item_table[item]['항목명']}" + (" [부재탐지]" if item in ABSENCE else "") for item in ITEMS]
    return "\n".join(["당신은 공공 입찰공고의 법령 위반 여부를 점검한다.", "제공된 metadata와 문서 원문만으로 아래 항목을 판정한다. 후보문맥의 선택 자체는 위반 근거나 결론이 아니다.", "판단이 어려우면 0으로 둔다. v19와 v21이 1이면 근거문구는 제공 문서의 변경 없는 연속 부분문자열(500자 이하)이어야 한다. v20의 근거문구는 항상 null이다.", "JSON 객체 하나만 출력한다. 각 항목은 {위반여부: 0 또는 1, 근거문구: 문자열 또는 null}이다.", "판정 항목:", *lines])


def messages(record: dict[str, Any], system: str, context: str) -> list[dict[str, str]]:
    return [{"role": "system", "content": system}, {"role": "user", "content": "\n\n".join([f"[공고 ID]\n{record['id']}", "[나라장터 입력 메타]\n" + json.dumps(record["meta"], ensure_ascii=False, sort_keys=True), "[문서]\n" + context])}]


def candidate_context(record: dict[str, Any], windows: list[dict[str, Any]], config: dict[str, Any]) -> str:
    docs = {doc["doc_id"]: doc for doc in record["docs"]}
    selected: list[str] = []
    used = 0
    for window in sorted(windows, key=lambda w: (DOC_ORDER[w["doc_type"]], w["doc_id"], w["start"])):
        text = window["text"]
        header = f"[{window['doc_type']}:{window['doc_id']} offset={window['start']}]\n"
        if used + len(header) + len(text) > config["treatment_max_candidate_chars"]:
            continue
        selected.append(header + text)
        used += len(header) + len(text)
    announcement = next((doc for doc in record["docs"] if doc["type"] == "공고문"), None)
    anchor = f"[공고문 앵커:{announcement['doc_id']}]\n{announcement['text'][:config['announcement_anchor_chars']]}" if announcement else ""
    return "\n\n".join([anchor, "[항목별 후보 원문: 후보 없음은 위반 부재가 아니다]", *selected])


def parse_active(content: str, record: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    payload = common.parse_json(content)
    source = "\n".join(doc["text"] for doc in record["docs"])
    result, warnings = {}, []
    for item in ITEMS:
        cell = payload.get(item)
        if not isinstance(cell, dict) or cell.get("위반여부") not in (0, 1):
            raise ValueError(f"invalid {item} cell")
        value = int(cell["위반여부"])
        evidence = "" if item in ABSENCE or not value else str(cell.get("근거문구") or "").strip()
        if value and item not in ABSENCE and evidence not in source:
            warnings.append(f"{item}: invalid evidence")
            evidence = ""
        result[item] = {"위반여부": value, "근거문구": evidence[:500]}
    return result, warnings


def append(path: Path, entry: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()


def task(request: dict[str, Any], record: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    response: dict[str, Any] | None = None
    try:
        result = common.completion(config, request["messages"], schema())
        response = {"raw_response": result.content, "model": result.model, "usage": result.usage, "latency_seconds": result.latency_seconds, "finish_reason": result.finish_reason, "success": False}
        judgment, warnings = parse_active(result.content, record)
        row = {"id": record["id"], **{item: judgment[item]["위반여부"] for item in ITEMS}, **{f"e{item[1:]}": judgment[item]["근거문구"] for item in ITEMS}}
        response["success"] = True
    except (RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        response = response or {"raw_response": "", "model": config["model"], "usage": {}, "latency_seconds": 0.0, "finish_reason": None, "success": False}
        row = {"id": record["id"], **{item: 0 for item in ITEMS}, **{f"e{item[1:]}": "" for item in ITEMS}}
        warnings = [f"transport_or_parse_failure: {type(exc).__name__}: {str(exc)[:300]}"]
    return {"id": request["id"], "policy": request["policy"], "row": row, "response": response, "warnings": warnings}


def score(rows: list[dict[str, Any]], labels: dict[str, dict[str, str]], records: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    per_item, all_tp, all_fp, all_fn, positives, valid = [], 0, 0, 0, 0, 0
    for item in ITEMS:
        tp = fp = fn = 0
        for row in rows:
            gold, pred = labels[row["id"]][item] == "1", row[item] == 1
            tp += gold and pred; fp += not gold and pred; fn += gold and not pred
            if pred and item not in ABSENCE:
                positives += 1
                valid += bool(row[f"e{item[1:]}"]) and row[f"e{item[1:]}"] in "\n".join(doc["text"] for doc in records[row["id"]]["docs"])
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_item.append({"item": item, "tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1})
        all_tp += tp; all_fp += fp; all_fn += fn
    return {"macro_f1": sum(row["f1"] for row in per_item) / len(per_item), "tp": all_tp, "fp": all_fp, "fn": all_fn, "recall_micro": all_tp / (all_tp + all_fn) if all_tp + all_fn else 0.0, "evidence_validity": valid / positives if positives else None, "evidence_positive_cases": positives}, per_item


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--config", default="incubator/configs/inc010_procedure_candidate_pilot.json"); parser.add_argument("--mode", choices=("preflight", "run"), default="preflight"); args = parser.parse_args()
    root = common.repo_root(); config = json.loads((root / args.config).read_text(encoding="utf-8")); load_dotenv(root / ".env")
    output = root / "incubator/runs" / config["experiment_id"]; output.mkdir(parents=True, exist_ok=True)
    lock = (output / ".run.lock").open("w", encoding="utf-8")
    try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc: raise RuntimeError(f"another run already owns {output}") from exc
    data_root = root / config["data_root"]; records = common.read_jsonl_gz(data_root / "dev.jsonl.gz"); by_id = {row["id"]: row for row in records}; label_rows = common.read_csv(data_root / "dev_labels.csv"); labels = {row["id"]: row for row in label_rows}
    manifest = [json.loads(line) for line in (root / config["candidate_manifest_path"]).read_text(encoding="utf-8").splitlines()]
    by_manifest: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in manifest:
        if entry["item"] in ITEMS: by_manifest[entry["id"]].extend(entry["windows"])
    for record_id, windows in by_manifest.items():
        unique: dict[tuple[str, int, int], dict[str, Any]] = {}
        for window in windows:
            unique[(window["doc_id"], window["start"], window["end"])] = window
        by_manifest[record_id] = list(unique.values())
    positives = [row for row in label_rows if any(row[item] == "1" for item in ITEMS)]
    negatives = [row for row in label_rows if all(row[item] == "0" for item in ITEMS)]
    candidate_negatives = sorted((row for row in negatives if by_manifest[row["id"]]), key=lambda row: (-len(by_manifest[row["id"]]), row["id"]))[:config["hard_candidate_negative_limit"]]
    no_candidate_negatives = sorted((row for row in negatives if not by_manifest[row["id"]]), key=lambda row: row["id"])[:config["no_candidate_negative_limit"]]
    cohort = sorted({row["id"]: row for row in [*positives, *candidate_negatives, *no_candidate_negatives]}.values(), key=lambda row: row["id"])
    system = system_prompt(json.loads((data_root / "data/항목표.json").read_text(encoding="utf-8"))["항목"])
    prepared = []
    for cohort_row in cohort:
        record = by_id[cohort_row["id"]]
        control, rendering = common.build_messages(record, system, config["control_document_chars"])
        treatment_context = candidate_context(record, by_manifest[record["id"]], config)
        prepared.extend([{"id": record["id"], "policy": "prefix_control", "messages": control, "rendering": rendering}, {"id": record["id"], "policy": "candidate_treatment", "messages": messages(record, system, treatment_context), "candidate_count": len(by_manifest[record["id"]])}])
    plan = {"experiment_id": config["experiment_id"], "target_items": ITEMS, "cohort_count": len(cohort), "positive_notice_count": len(positives), "hard_candidate_negative_count": len(candidate_negatives), "no_candidate_negative_count": len(no_candidate_negatives), "max_requests": config["max_requests"], "concurrency": config["concurrency"], "max_cost_usd": config["max_cost_usd"], "success_gate": "treatment macro F1 >= control +0.05, recall non-decrease, evidence >=0.95, each item <=1 new FP", "source_sha256": {"dev": common.sha256_file(data_root / "dev.jsonl.gz"), "labels": common.sha256_file(data_root / "dev_labels.csv"), "manifest": common.sha256_file(root / config["candidate_manifest_path"])}}
    common.write_json(output / "config.json", config); common.write_json(output / "plan.json", plan); common.write_jsonl(output / "inputs.jsonl", prepared)
    if args.mode == "preflight": print(json.dumps({"status": "preflight_ok", **plan, "prepared_requests": len(prepared)}, ensure_ascii=False, indent=2)); return
    if len(prepared) > config["max_requests"]: raise RuntimeError("request ceiling exceeded")
    checkpoint = output / "checkpoint.jsonl"; completed = {(entry["id"], entry["policy"]): entry for entry in ([json.loads(line) for line in checkpoint.read_text(encoding="utf-8").splitlines()] if checkpoint.exists() else [])}; remaining = [request for request in prepared if (request["id"], request["policy"]) not in completed]
    cost = sum(float(entry["response"]["usage"].get("cost", 0) or 0) for entry in completed.values())
    with ThreadPoolExecutor(max_workers=config["concurrency"]) as pool:
        futures = {pool.submit(task, request, by_id[request["id"]], config): request for request in remaining}
        for index, future in enumerate(as_completed(futures), 1):
            entry = future.result(); cost += float(entry["response"]["usage"].get("cost", 0) or 0); completed[(entry["id"], entry["policy"])] = entry; append(checkpoint, entry); print(f"[{index}/{len(remaining)}] {entry['policy']} cumulative=${cost:.6f}", flush=True)
    rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in completed.values(): rows[entry["policy"]].append(entry["row"])
    metrics: dict[str, Any] = {"experiment_id": config["experiment_id"], "request_count": len(completed), "successful_request_count": sum(entry["response"]["success"] for entry in completed.values()), "reported_cost_usd": cost, "policies": {}, "per_item": {}}
    for policy in ("prefix_control", "candidate_treatment"):
        metrics["policies"][policy], metrics["per_item"][policy] = score(sorted(rows[policy], key=lambda row: row["id"]), labels, by_id)
        with (output / f"predictions_{policy}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=("id", *ITEMS, *(f"e{item[1:]}" for item in ITEMS)), lineterminator="\n"); writer.writeheader(); writer.writerows(sorted(rows[policy], key=lambda row: row["id"]))
    control, treatment = metrics["policies"]["prefix_control"], metrics["policies"]["candidate_treatment"]
    metrics["delta_treatment_minus_control"] = {key: treatment[key] - control[key] for key in ("macro_f1", "tp", "fp", "fn", "recall_micro", "evidence_validity")}
    metrics["new_false_positives_by_item"] = {item: max(0, treatment_item["fp"] - metrics["per_item"]["prefix_control"][index]["fp"]) for index, (item, treatment_item) in enumerate(zip(ITEMS, metrics["per_item"]["candidate_treatment"]))}
    common.write_jsonl(output / "responses.jsonl", [{"id": entry["id"], "policy": entry["policy"], **entry["response"], "warnings": entry["warnings"]} for entry in completed.values()]); common.write_json(output / "metrics.json", metrics); print(json.dumps({"status": "complete", "metrics": metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
