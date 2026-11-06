"""Source-only regional-clause role probe; it never produces final v labels."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time
from typing import Any

from .config import CleanExperimentConfig
from .ingest import load_notice_records
from .runtime.openrouter import OpenRouterRuntime, atomic_json
from .runtime.tokenizer import GemmaTokenCounter


ROLES = (
    "BIDDER_QUALIFICATION", "EVALUATION", "SITE_OR_DELIVERY",
    "POST_AWARD", "OTHER", "UNCLEAR",
)
UNITS = ("BASIC", "PROVINCE", "MULTI_PROVINCE", "UNSPECIFIED")
SYSTEM = (
    "당신은 입찰 공고 원문 한 구절의 사실상 역할을 식별합니다. 법률 위반 여부나 "
    "v 항목을 판정하지 마세요. 입찰참가자격 제한, 평가 기준, 현장·납품 정보, "
    "낙찰 후 권고를 구분하세요. 지역 단위는 업체에 요구된 소재지에 대해서만 "
    "표시하고, 현장 주소의 단위는 업체 자격 단위로 옮기지 마세요. "
    "quote는 제시된 원문에서 문자 그대로 연속된 부분만 복사하세요."
)
SCHEMA = {
    "type": "object",
    "properties": {
        "role": {"type": "string", "enum": list(ROLES)},
        "unit": {"type": "string", "enum": list(UNITS)},
        "quote": {"type": "string"},
    },
    "required": ["role", "unit", "quote"],
    "additionalProperties": False,
}


def _document_excerpt(text: str, candidate: str, max_chars: int) -> tuple[int, str]:
    start = text.find(candidate)
    if start < 0:
        raise ValueError("review excerpt is not an exact source substring")
    if len(candidate) <= max_chars:
        return start, candidate
    anchors = ("[지역:", "[수요기관(기초자치단체)]", "서울", "경상", "전라")
    positions = [candidate.find(marker) for marker in anchors if candidate.find(marker) >= 0]
    anchor = min(positions) if positions else max_chars // 2
    offset = min(max(0, anchor - 320), len(candidate) - max_chars)
    return start + offset, candidate[offset:offset + max_chars]


def _dev_excerpt(record: Any, max_chars: int) -> tuple[Any, int, str]:
    for document in record.documents:
        for line in document.text.splitlines():
            if not ("지역:" in line or "[수요기관(기초자치단체)]" in line):
                continue
            if not ("업체" in line or "입찰참가자" in line or "본점소재지" in line):
                continue
            start, excerpt = _document_excerpt(document.text, line, max_chars)
            return document, start, excerpt
    raise ValueError(f"{record.notice_id}: no label-blind candidate source line")


def _train_excerpt(record: Any, review: dict[str, Any], max_chars: int) -> tuple[Any, int, str]:
    candidates = review["participation_candidates"]
    selected = candidates[0]["exact_text"] if candidates else review["first_source_hit"]
    for document in record.documents:
        if selected in document.text:
            start, excerpt = _document_excerpt(document.text, selected, max_chars)
            return document, start, excerpt
    raise ValueError(f"{record.notice_id}: review excerpt absent from original documents")


def build_micro_tasks(config: CleanExperimentConfig) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    policy = config.raw["micro"]
    ids = policy["notice_ids"]
    if len(ids) != len(set(ids)) or len(ids) > policy["max_calls"]:
        raise ValueError("invalid fixed micro panel")
    dev = {row.notice_id: row for row in load_notice_records(config.input_path)}
    unlabeled_path = config.path.parents[2] / config.raw["regional_threshold_policy"]["unlabeled_input_path"]
    input_hashes = {
        "dev": hashlib.sha256(config.input_path.read_bytes()).hexdigest(),
        "unlabeled": hashlib.sha256(unlabeled_path.read_bytes()).hexdigest(),
    }
    train = {row.notice_id: row for row in load_notice_records(unlabeled_path)
             if row.notice_id in ids}
    review_path = config.path.parents[2] / policy["source_review_path"]
    reviews = {row["id"]: row for row in json.loads(review_path.read_text(encoding="utf-8"))}
    tokenizer = GemmaTokenCounter(config.tokenizer_dir)
    tasks: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []
    for notice_id in ids:
        record = dev.get(notice_id) or train.get(notice_id)
        if record is None:
            raise ValueError(f"missing micro notice: {notice_id}")
        if notice_id in dev:
            document, start, excerpt = _dev_excerpt(record, policy["excerpt_max_chars"])
        else:
            document, start, excerpt = _train_excerpt(
                record, reviews[notice_id], policy["excerpt_max_chars"],
            )
        end = start + len(excerpt)
        if document.text[start:end] != excerpt or len(excerpt) > 500:
            raise ValueError(f"{notice_id}: invalid source span")
        user = (
            f"공고 ID: {notice_id}\n문서: {document.document_type} ({document.doc_id})\n"
            "아래 한 구절만 근거로 역할과 업체 소재지 제한의 지역 단위를 식별하세요. "
            "다른 문서나 금액은 제공되지 않았으므로 최종 위반 여부를 추론하지 마세요.\n\n"
            f"<원문>\n{excerpt}\n</원문>"
        )
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
        task = {"id": notice_id, "arm": "REGIONAL_ROLE", "messages": messages, "schema": SCHEMA}
        count = tokenizer.count(messages)
        if count > config.prompt_budget:
            raise ValueError(f"{notice_id}: token admission failed: {count}")
        tasks.append(task)
        ledger.append({
            "id": notice_id, "doc_id": document.doc_id, "document_type": document.document_type,
            "input_file": str(config.input_path if notice_id in dev else unlabeled_path),
            "input_file_sha256": input_hashes["dev" if notice_id in dev else "unlabeled"],
            "document_order": document.order, "document_sha256": document.sha256,
            "start": start, "end": end, "excerpt_sha256": hashlib.sha256(excerpt.encode()).hexdigest(),
            "excerpt_length": len(excerpt), "prompt_tokens": count,
            "other_source_omitted": len(record.documents) != 1 or len(document.text) != len(excerpt),
            "notice_documents": len(record.documents),
            "task_sha256": tokenizer.task_sha256(task),
        })
    return tasks, ledger


def parse_role_response(content: str, excerpt: str) -> dict[str, Any]:
    value = json.loads(content)
    if not isinstance(value, dict) or set(value) != {"role", "unit", "quote"}:
        raise ValueError("role response shape mismatch")
    if value["role"] not in ROLES or value["unit"] not in UNITS:
        raise ValueError("role response enum mismatch")
    quote = value["quote"]
    if not isinstance(quote, str) or len(quote) > 300 or (quote and quote not in excerpt):
        raise ValueError("role quote is not a valid exact excerpt substring")
    if value["role"] != "UNCLEAR" and not quote:
        raise ValueError("non-unclear role requires source quote")
    return value


def run_micro(config: CleanExperimentConfig, *, mock: bool, api_key: str = "") -> dict[str, Any]:
    tasks, ledger = build_micro_tasks(config)
    out = config.output_dir
    out.mkdir(parents=True, exist_ok=True)
    atomic_json(out / "manifest.snapshot.json", config.raw)
    atomic_json(out / "source_ledger.json", ledger)
    for task in tasks:
        atomic_json(out / "rendered" / f"{task['id']}.json", task)
    if mock:
        for task in tasks:
            excerpt = task["messages"][1]["content"].split("<원문>\n", 1)[1].split("\n</원문>", 1)[0]
            parse_role_response(json.dumps({"role": "UNCLEAR", "unit": "UNSPECIFIED", "quote": ""}), excerpt)
        report = {"status": "PASS", "mode": "mock", "tasks": len(tasks),
                  "prompt_tokens": sum(row["prompt_tokens"] for row in ledger)}
        atomic_json(out / "mock_report.json", report)
        return report
    runtime = OpenRouterRuntime(config.provider, api_key)
    outcomes: list[dict[str, Any]] = []
    started = time.monotonic()
    for task, source in zip(tasks, ledger, strict=True):
        response_path = out / "responses" / f"{task['id']}.json"
        if response_path.exists():
            response = json.loads(response_path.read_text(encoding="utf-8"))
            if response.get("task_sha256") != source["task_sha256"]:
                raise ValueError(f"{task['id']}: checkpoint/task mismatch")
        else:
            try:
                response = runtime.complete(task)
            except RuntimeError as error:
                response = {"invalid": True, "error": str(error), "usage": {}, "attempts": 0}
            response["task_sha256"] = source["task_sha256"]
            atomic_json(response_path, response)
        excerpt = task["messages"][1]["content"].split("<원문>\n", 1)[1].split("\n</원문>", 1)[0]
        try:
            parsed = parse_role_response(response["content"], excerpt)
            result = {"id": task["id"], "valid": True, **parsed,
                      "usage": response.get("usage", {}), "attempts": response.get("attempts", 0)}
        except (KeyError, ValueError, TypeError, json.JSONDecodeError) as error:
            result = {"id": task["id"], "valid": False, "error": str(error),
                      "usage": response.get("usage", {}), "attempts": response.get("attempts", 0)}
        outcomes.append(result)
        if len(outcomes) % 5 == 0 or len(outcomes) == len(tasks):
            atomic_json(out / f"checkpoint_{len(outcomes):02d}.json", {
                "completed": len(outcomes), "invalid": sum(not row["valid"] for row in outcomes),
                "elapsed_seconds": round(time.monotonic() - started, 3), "results": outcomes,
            })
    report = {"status": "COMPLETE", "mode": "api", "calls": len(tasks),
              "invalid": sum(not row["valid"] for row in outcomes),
              "elapsed_seconds": round(time.monotonic() - started, 3), "results": outcomes}
    atomic_json(out / "report.json", report)
    return report
