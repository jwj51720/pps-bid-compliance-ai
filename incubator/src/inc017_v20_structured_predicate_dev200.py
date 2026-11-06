#!/usr/bin/env python3
"""All-dev v20 predicate diagnostic with source-substring validation."""

from __future__ import annotations

import argparse
import fcntl
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from dotenv import load_dotenv
from transformers import AutoTokenizer

import inc001_simple_joint24 as common
import inc014_v20_card_pilot as pilot
from inc007_token_admission_profile import count_messages


SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["sw_applicability", "sw_evidence", "declaration_status", "declaration_evidence", "exception_status", "exception_evidence"],
    "properties": {
        "sw_applicability": {"type": "string", "enum": ["yes", "no", "uncertain"]},
        "sw_evidence": {"type": ["string", "null"], "maxLength": 500},
        "declaration_status": {"type": "string", "enum": ["present", "absent", "uncertain"]},
        "declaration_evidence": {"type": ["string", "null"], "maxLength": 500},
        "exception_status": {"type": "string", "enum": ["present", "not_present", "uncertain"]},
        "exception_evidence": {"type": ["string", "null"], "maxLength": 500},
    },
}
SYSTEM = """당신은 v20을 위한 원문 기반 진단을 한다. 내부 추론은 출력하지 말고 JSON만 출력한다.

각 필드를 독립적으로 판정한다.
1) sw_applicability=yes는 이 조달 자체가 소프트웨어사업(소프트웨어 라이선스·구축·개발·운영·유지보수 포함)임을 원문이 뒷받침할 때만 쓴다. yes이면 sw_evidence에 변경 없는 원문 연속 substring을 넣는다. no/uncertain이면 null이다.
2) declaration_status=present는 원문이 대기업인 소프트웨어사업자 참여제한 하한제도의 적용 여부와 적용 근거를 실제로 명시할 때만 쓴다. present이면 declaration_evidence에 원문 substring을 넣는다. absent는 전체 원문을 검토했으나 그 명시를 찾지 못했을 때만 쓴다. uncertain이면 null이다.
3) exception_status=present는 원문이 이 사업에 대한 적용예외 또는 분리·분담이행 예외를 실제로 명시할 때만 쓴다. present이면 exception_evidence에 원문 substring을 넣는다. not_present/uncertain이면 null이다.

일반적인 입찰참가 제한·제재, 단순 중소기업 조건, 일반 소프트웨어 제품 언급은 declaration present가 아니다. 제공 법령 사실은 해석 보조이고, 근거는 반드시 공고 원문이어야 한다. JSON만 출력한다."""


def read_jsonl(path: Any) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_jsonl(path: Any, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()


def messages(record: dict[str, Any], card_context: str) -> list[dict[str, str]]:
    base = pilot.build_messages(record, card_context)
    return [{"role": "system", "content": SYSTEM}, base[1]]


def valid_evidence(value: Any, source: str) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 500 and value in source


def parse_and_merge(content: str, record: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    value = common.parse_json(content)
    required = set(SCHEMA["required"])
    if not required.issubset(value):
        raise ValueError("missing predicate field")
    source = "\n".join(doc["text"] for doc in record["docs"])
    warnings: list[str] = []
    sw = value["sw_applicability"]
    declaration = value["declaration_status"]
    exception = value["exception_status"]
    if sw not in {"yes", "no", "uncertain"} or declaration not in {"present", "absent", "uncertain"} or exception not in {"present", "not_present", "uncertain"}:
        raise ValueError("invalid predicate enum")
    if sw == "yes" and not valid_evidence(value["sw_evidence"], source):
        warnings.append("invalid_sw_evidence_downgraded")
        sw = "uncertain"
    if declaration == "present" and not valid_evidence(value["declaration_evidence"], source):
        warnings.append("invalid_declaration_evidence_downgraded")
        declaration = "uncertain"
    if exception == "present" and not valid_evidence(value["exception_evidence"], source):
        warnings.append("invalid_exception_evidence_downgraded")
        exception = "uncertain"
    # This is a deterministic merge of Gemma's separately requested predicates,
    # never an extractor-only inference. Unknown is deliberately conservative.
    v20 = int(sw == "yes" and declaration == "absent" and exception == "not_present")
    return {"sw_applicability": sw, "declaration_status": declaration, "exception_status": exception, "v20": v20}, warnings


def score(rows: list[dict[str, Any]], labels: dict[str, dict[str, str]]) -> dict[str, Any]:
    tp = sum(row["v20"] == 1 and labels[row["id"]]["v20"] == "1" for row in rows)
    fp = sum(row["v20"] == 1 and labels[row["id"]]["v20"] == "0" for row in rows)
    fn = sum(row["v20"] == 0 and labels[row["id"]]["v20"] == "1" for row in rows)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--config", default="incubator/configs/inc017_v20_structured_predicate_dev200.json"); parser.add_argument("--mode", choices=("preflight", "run"), default="preflight"); args = parser.parse_args()
    root = common.repo_root(); config = json.loads((root / args.config).read_text(encoding="utf-8")); load_dotenv(root / ".env")
    output = root / "incubator/runs" / config["experiment_id"]; output.mkdir(parents=True, exist_ok=True)
    lock = (output / ".run.lock").open("w", encoding="utf-8"); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    data = root / config["data_root"]; records = {row["id"]: row for row in common.read_jsonl_gz(data / "dev.jsonl.gz")}; labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}
    card_path = root / config["card_path"]; card_sha = common.sha256_file(card_path)
    if card_sha != config["expected_card_sha256"]: raise RuntimeError("frozen card hash mismatch")
    card_context = pilot.card_for_prompt(json.loads(card_path.read_text(encoding="utf-8"))); tokenizer = AutoTokenizer.from_pretrained(config["model_tokenizer"]); budget = config["max_model_len"] - config["output_reserve_tokens"]
    prepared = []
    for record_id in sorted(records):
        request_messages = messages(records[record_id], card_context); tokens = count_messages(tokenizer, request_messages)
        if tokens > budget: raise RuntimeError(f"prompt exceeds budget: {record_id} {tokens}>{budget}")
        prepared.append({"id": record_id, "messages": request_messages, "prompt_tokens": tokens, "prompt_sha256": common.sha256_text(json.dumps(request_messages, ensure_ascii=False, sort_keys=True))})
    projected = sum(row["prompt_tokens"] * config["observed_input_cost_per_token_usd"] + config["assumed_completion_tokens"] * config["observed_completion_cost_per_token_usd"] for row in prepared)
    plan = {"experiment_id": config["experiment_id"], "hypothesis": "source-validated decomposed predicates reduce the INC-015 card's applicability-leakage false positives", "changed_variable": "single-shot v20 output replaced with source-validated diagnostic predicates", "cohort_count": len(prepared), "request_count": len(prepared), "full_notice_context": True, "prompt_token_budget": budget, "prompt_token_max": max(row["prompt_tokens"] for row in prepared), "projected_cost_usd": projected, "max_cost_usd": config["max_cost_usd"], "success_gate": "v20 F1 > INC-015 control 0.60; FP <= 2; recall >= 0.60; zero failures", "source_sha256": {"dev": common.sha256_file(data / "dev.jsonl.gz"), "labels": common.sha256_file(data / "dev_labels.csv"), "card": card_sha}}
    common.write_json(output / "config.json", config); common.write_json(output / "plan.json", plan); common.write_jsonl(output / "inputs.jsonl", prepared)
    if projected > config["max_cost_usd"]: raise RuntimeError(f"projected cost exceeds ceiling: {projected:.4f}")
    if args.mode == "preflight": print(json.dumps({"status": "preflight_ok", **plan}, ensure_ascii=False, indent=2)); return
    checkpoint = output / "checkpoint.jsonl"; done = {row["id"]: row for row in read_jsonl(checkpoint)} if checkpoint.exists() else {}
    def run(request: dict[str, Any]) -> dict[str, Any]:
        response: dict[str, Any] = {"raw_response": "", "model": config["model"], "usage": {}, "latency_seconds": 0.0, "finish_reason": None, "success": False}
        try:
            result = common.completion(config, request["messages"], SCHEMA); response.update({"raw_response": result.content, "model": result.model, "usage": result.usage, "latency_seconds": result.latency_seconds, "finish_reason": result.finish_reason}); diagnostic, warnings = parse_and_merge(result.content, records[request["id"]]); response["success"] = True
        except Exception as exc: diagnostic, warnings = {"sw_applicability": "uncertain", "declaration_status": "uncertain", "exception_status": "uncertain", "v20": 0}, [f"failure:{type(exc).__name__}:{str(exc)[:240]}"]
        return {"id": request["id"], "diagnostic": diagnostic, "response": response, "warnings": warnings}
    remaining = [request for request in prepared if request["id"] not in done]
    with ThreadPoolExecutor(max_workers=config["concurrency"]) as executor:
        futures = [executor.submit(run, request) for request in remaining]
        for index, future in enumerate(as_completed(futures), 1):
            row = future.result(); done[row["id"]] = row; append_jsonl(checkpoint, row)
            if index % 20 == 0 or index == len(remaining): print(f"[{index}/{len(remaining)}] completed", flush=True)
    rows = sorted(done.values(), key=lambda row: row["id"]); metrics = {"experiment_id": config["experiment_id"], "request_count": len(rows), "successful_request_count": sum(row["response"]["success"] for row in rows), "reported_cost_usd": sum(float(row["response"]["usage"].get("cost", 0) or 0) for row in rows), "v20": score([{**row["diagnostic"], "id": row["id"]} for row in rows], labels), "predicate_distribution": {name: {value: sum(row["diagnostic"][name] == value for row in rows) for value in values} for name, values in {"sw_applicability": ("yes", "no", "uncertain"), "declaration_status": ("present", "absent", "uncertain"), "exception_status": ("present", "not_present", "uncertain")}.items()}, "warning_count": sum(len(row["warnings"]) for row in rows)}
    v20 = metrics["v20"]; metrics["success_gate_pass"] = v20["f1"] > .60 and v20["fp"] <= 2 and v20["recall"] >= .60 and metrics["successful_request_count"] == len(prepared)
    common.write_jsonl(output / "responses.jsonl", [{"id": row["id"], **row["response"], "warnings": row["warnings"]} for row in rows]); common.write_jsonl(output / "predictions.jsonl", [{"id": row["id"], **row["diagnostic"]} for row in rows]); common.write_json(output / "metrics.json", metrics); print(json.dumps({"status": "complete", "metrics": metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
