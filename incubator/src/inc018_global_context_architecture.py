#!/usr/bin/env python3
"""All-dev global comparison: one full notice versus document-pass merge."""
from __future__ import annotations

import argparse
import csv
import fcntl
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from dotenv import load_dotenv
from transformers import AutoTokenizer

import inc001_simple_joint24 as common
from inc007_token_admission_profile import count_messages
from inc006_input_budget_ablation import metric


def read_jsonl(path: Any) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_jsonl(path: Any, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()


def system_prompt(items: dict[str, Any], split: bool) -> str:
    base = common.build_system_prompt(items)
    if not split:
        return base
    return base + "\n\n이 pass의 [판정 대상 문서]만 non-absence 위반의 근거가 될 수 있다. 대상 문서 밖의 공고문 앵커·메타·참고문서는 맥락일 뿐 근거가 아니다. 부재탐지 항목은 대상 문서에서 필요한 명시가 없으면 1, 있으면 0으로 판정한다."


def user_message(record: dict[str, Any], document_context: str, target: dict[str, Any] | None = None, anchor: str = "") -> list[dict[str, str]]:
    sections = [
        f"[공고 ID]\n{record['id']}",
        "[나라장터 입력 메타]\n" + json.dumps(record["meta"], ensure_ascii=False, sort_keys=True),
    ]
    if anchor:
        sections.append(anchor)
    if target is None:
        sections.append("[전체 문서]\n" + document_context)
    else:
        sections.append(f"[판정 대상 문서:{target['type']}:{target['doc_id']}]\n" + document_context)
    return sections


def build_messages(record: dict[str, Any], system: str, document_context: str, target: dict[str, Any] | None = None, anchor: str = "") -> list[dict[str, str]]:
    return [{"role": "system", "content": system}, {"role": "user", "content": "\n\n".join(user_message(record, document_context, target, anchor))}]


def full_context(record: dict[str, Any]) -> str:
    docs = sorted(record["docs"], key=lambda doc: (common.DOCUMENT_ORDER[doc["type"]], doc["doc_id"]))
    return "\n\n".join(f"[{doc['type']}:{doc['doc_id']}]\n{doc['text']}" for doc in docs)


def split_requests(record: dict[str, Any], system: str, tokenizer: Any, budget: int, anchor_chars: int) -> list[dict[str, Any]]:
    docs = sorted(record["docs"], key=lambda doc: (common.DOCUMENT_ORDER[doc["type"]], doc["doc_id"]))
    announcement = next((doc for doc in docs if doc["type"] == "공고문"), None)
    result = []
    for doc in docs:
        anchor = "" if doc is announcement else f"[공고문 앵커:{announcement['doc_id']}]\n{announcement['text'][:anchor_chars]}" if announcement else ""
        text, offset, fragment = doc["text"], 0, 0
        while offset < len(text) or (not text and offset == 0):
            header = "" if fragment == 0 else f"[계속 {offset}]\n"
            candidate = header + text[offset:]
            messages = build_messages(record, system, candidate, doc, anchor)
            if count_messages(tokenizer, messages) <= budget:
                result.append({"id": record["id"], "policy": "full_split_merge", "target_doc_id": doc["doc_id"], "target_doc_type": doc["type"], "fragment_offset": offset, "messages": messages, "prompt_tokens": count_messages(tokenizer, messages)})
                break
            low, high, best = 1, len(text) - offset, 0
            while low <= high:
                middle = (low + high) // 2
                trial = header + text[offset:offset + middle]
                if count_messages(tokenizer, build_messages(record, system, trial, doc, anchor)) <= budget:
                    best, low = middle, middle + 1
                else:
                    high = middle - 1
            if best == 0:
                raise RuntimeError(f"fixed split prompt too large: {record['id']} {doc['doc_id']}")
            trial = header + text[offset:offset + best]
            messages = build_messages(record, system, trial, doc, anchor)
            result.append({"id": record["id"], "policy": "full_split_merge", "target_doc_id": doc["doc_id"], "target_doc_type": doc["type"], "fragment_offset": offset, "messages": messages, "prompt_tokens": count_messages(tokenizer, messages)})
            offset += best; fragment += 1
    return result


def strict_pass(payload: dict[str, Any], request: dict[str, Any], record: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    result, warnings = common.postprocess(payload, record)
    doc = next(doc for doc in record["docs"] if doc["doc_id"] == request["target_doc_id"])
    for item in common.ITEMS:
        if item not in common.ABSENCE_ITEMS and result[item]["위반여부"] and result[item]["근거문구"] not in doc["text"]:
            result[item] = {"위반여부": 0, "근거문구": ""}
            warnings.append(f"{item}: evidence outside target document downgraded")
    return result, warnings


def merge(record_id: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
    judgment: dict[str, dict[str, Any]] = {}
    for item in common.ITEMS:
        cells = [entry["judgment"][item] for entry in entries]
        if item in common.ABSENCE_ITEMS:
            value = int(bool(cells) and all(cell["위반여부"] == 1 for cell in cells))
            judgment[item] = {"위반여부": value, "근거문구": ""}
        else:
            positive = next((cell for cell in cells if cell["위반여부"] == 1), None)
            judgment[item] = positive if positive else {"위반여부": 0, "근거문구": ""}
    return common.to_row(record_id, judgment)


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--config", default="incubator/configs/inc018_global_context_architecture.json"); parser.add_argument("--mode", choices=("preflight", "run"), default="preflight"); args = parser.parse_args()
    root = common.repo_root(); config = json.loads((root / args.config).read_text(encoding="utf-8")); load_dotenv(root / ".env")
    out = root / "incubator/runs" / config["experiment_id"]; out.mkdir(parents=True, exist_ok=True); lock = (out / ".run.lock").open("w", encoding="utf-8"); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    data = root / config["data_root"]; records = {row["id"]: row for row in common.read_jsonl_gz(data / "dev.jsonl.gz")}; labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}; items = json.loads((data / "data/항목표.json").read_text(encoding="utf-8"))["항목"]
    tokenizer = AutoTokenizer.from_pretrained(config["model_tokenizer"]); budget = config["max_model_len"] - config["output_reserve_tokens"]; joint_system, split_system = system_prompt(items, False), system_prompt(items, True)
    prepared = []
    for record in records.values():
        message = build_messages(record, joint_system, full_context(record))
        tokens = count_messages(tokenizer, message)
        if tokens > budget: raise RuntimeError(f"joint prompt exceeds budget: {record['id']} {tokens}>{budget}")
        prepared.append({"id": record["id"], "policy": "single_full", "messages": message, "prompt_tokens": tokens})
        prepared.extend(split_requests(record, split_system, tokenizer, budget, config["announcement_anchor_chars"]))
    for request in prepared: request["prompt_sha256"] = common.sha256_text(json.dumps(request["messages"], ensure_ascii=False, sort_keys=True))
    counts = defaultdict(int)
    for request in prepared: counts[request["policy"]] += 1
    projected = sum(request["prompt_tokens"] * config["observed_input_cost_per_token_usd"] + config["assumed_completion_tokens"] * config["observed_completion_cost_per_token_usd"] for request in prepared)
    plan = {"experiment_id": config["experiment_id"], "hypothesis": "document-local attention plus contract-correct merge improves global macro F1 and document-grounded evidence over one full-notice judgment", "changed_variable": "context architecture and its required evidence/merge contract", "cohort_count": len(records), "request_count_by_policy": dict(counts), "request_count": len(prepared), "prompt_token_budget": budget, "prompt_token_max": max(request["prompt_tokens"] for request in prepared), "projected_cost_usd": projected, "max_cost_usd": config["max_cost_usd"], "success_gate": "full_split_merge macro F1 > single_full + 0.02; evidence validity non-decrease; no more than 5% failed calls", "source_sha256": {"dev": common.sha256_file(data / "dev.jsonl.gz"), "labels": common.sha256_file(data / "dev_labels.csv"), "item_table": common.sha256_file(data / "data/항목표.json")}}
    common.write_json(out / "config.json", config); common.write_json(out / "plan.json", plan); common.write_jsonl(out / "inputs.jsonl", prepared)
    if projected > config["max_cost_usd"]: raise RuntimeError(f"projected cost exceeds ceiling: {projected:.4f}")
    if args.mode == "preflight": print(json.dumps({"status": "preflight_ok", **plan}, ensure_ascii=False, indent=2)); return
    if len(prepared) > config["max_requests"]: raise RuntimeError("request ceiling exceeded")
    checkpoint = out / "checkpoint.jsonl"; done = {(row["id"], row["policy"], row.get("target_doc_id"), row.get("fragment_offset")): row for row in read_jsonl(checkpoint)} if checkpoint.exists() else {}
    def key(request: dict[str, Any]) -> tuple[Any, ...]: return request["id"], request["policy"], request.get("target_doc_id"), request.get("fragment_offset")
    def run(request: dict[str, Any]) -> dict[str, Any]:
        response: dict[str, Any] = {"raw_response": "", "model": config["model"], "usage": {}, "latency_seconds": 0.0, "finish_reason": None, "success": False}
        try:
            output = common.completion(config, request["messages"], common.judgment_schema()); response.update({"raw_response": output.content, "model": output.model, "usage": output.usage, "latency_seconds": output.latency_seconds, "finish_reason": output.finish_reason})
            payload = common.parse_json(output.content); judgment, warnings = strict_pass(payload, request, records[request["id"]]) if request["policy"] == "full_split_merge" else common.postprocess(payload, records[request["id"]]); response["success"] = True
        except Exception as exc: judgment, warnings = common.zero_judgment(), [f"failure:{type(exc).__name__}:{str(exc)[:240]}"]
        return {"id": request["id"], "policy": request["policy"], "target_doc_id": request.get("target_doc_id"), "fragment_offset": request.get("fragment_offset"), "judgment": judgment, "response": response, "warnings": warnings}
    remaining = [request for request in prepared if key(request) not in done]
    with ThreadPoolExecutor(max_workers=config["concurrency"]) as executor:
        futures = [executor.submit(run, request) for request in remaining]
        for index, future in enumerate(as_completed(futures), 1):
            row = future.result(); done[(row["id"], row["policy"], row.get("target_doc_id"), row.get("fragment_offset"))] = row; append_jsonl(checkpoint, row)
            if index % 20 == 0 or index == len(remaining): print(f"[{index}/{len(remaining)}] completed", flush=True)
    entries = list(done.values()); rows = {"single_full": [], "full_split_merge": []}
    for record_id in sorted(records):
        joint = [entry for entry in entries if entry["id"] == record_id and entry["policy"] == "single_full"]
        split = [entry for entry in entries if entry["id"] == record_id and entry["policy"] == "full_split_merge"]
        rows["single_full"].append(common.to_row(record_id, joint[0]["judgment"]))
        rows["full_split_merge"].append(merge(record_id, split))
    metrics = {"experiment_id": config["experiment_id"], "request_count": len(entries), "successful_request_count": sum(entry["response"]["success"] for entry in entries), "reported_cost_usd": sum(float(entry["response"]["usage"].get("cost", 0) or 0) for entry in entries), "policies": {}, "per_item": {}}
    for policy, result_rows in rows.items(): metrics["policies"][policy], metrics["per_item"][policy] = metric(result_rows, labels, records)
    a, b = metrics["policies"]["single_full"], metrics["policies"]["full_split_merge"]; metrics["delta_split_minus_single"] = {name: b[name] - a[name] for name in ("macro_f1", "tp", "fp", "fn", "recall_micro", "evidence_validity")}; metrics["success_gate_pass"] = b["macro_f1"] > a["macro_f1"] + .02 and (b["evidence_validity"] or 0) >= (a["evidence_validity"] or 0) and metrics["successful_request_count"] >= len(prepared) * .95
    for policy, result_rows in rows.items():
        with (out / f"predictions_{policy}.csv").open("w", encoding="utf-8", newline="") as handle: writer = csv.DictWriter(handle, fieldnames=common.CSV_COLUMNS, lineterminator="\n"); writer.writeheader(); writer.writerows(result_rows)
    common.write_jsonl(out / "responses.jsonl", [{"id": entry["id"], "policy": entry["policy"], "target_doc_id": entry["target_doc_id"], "fragment_offset": entry["fragment_offset"], **entry["response"], "warnings": entry["warnings"]} for entry in entries]); common.write_json(out / "metrics.json", metrics); print(json.dumps({"status": "complete", "metrics": metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
