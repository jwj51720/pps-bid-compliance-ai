"""Positive-only v16 full-source verifier with exact tokenizer admission."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import time
from typing import Any, Mapping, Sequence

from .config import CleanExperimentConfig
from .evaluate import evaluate_rows
from .facts.document_product_codes import (
    collect_document_product_mentions,
    render_document_product_mentions,
)
from .facts.metadata import build_metadata_facts, render_metadata_facts
from .facts.product_codes import (
    build_product_facts,
    load_product_index,
    render_product_facts,
)
from .ingest import load_notice_records
from .preflight import compare_manifests
from .runtime.openrouter import OpenRouterRuntime, atomic_json
from .runtime.tokenizer import GemmaTokenCounter
from .views.native_full_prompt import DOCUMENT_ORDER, load_card_texts


SYSTEM_MESSAGE_V1 = """당신은 공공 입찰공고의 v16 항목만 독립적으로 재검증한다.
제공된 카드의 적용대상·금액구간·필요 제한·예외를 순서대로 적용하라.
전자조달 입력 사실은 공고 원문과 별도로 대조하되, 조항 내용 한 줄만으로 원문에
참가제한이 존재한다고 가정하지 마라. 경쟁제품 CSV의 exact-code 사실도 구매대상과
실제 조건을 원문에서 확인하라. 낙찰자·계약상대자의 계약 후 서류, 단순 법명 인용,
해당 시 제출, 평가 우대는 입찰참가 중소기업 제한으로 바꾸지 마라.

이 메시지에 제공된 원문은 공고 전체 또는 공고 전체를 빠짐없이 나눈 한 pass다.
이 pass나 고정 사실에서 v16의 적용 제외, 필요한 중소기업 참가제한, 또는 명시적
판로지원 예외를 확인하면 v16=0이다. 그런 반대사실이 없으면 이 pass의 v16=1이다.
최종 결합은 모든 pass의 AND로 수행된다. 불명확함을 임의의 반대사실로 만들지 마라.
지정된 JSON 한 개만 출력한다."""

SCHEMA_V1 = {
    "type": "object",
    "properties": {"v16": {"type": "integer", "enum": [0, 1]}},
    "required": ["v16"],
    "additionalProperties": False,
}

SYSTEM_MESSAGE_V2 = """당신은 공공 입찰공고에서 v16 판정에 필요한 반대사실만 구조화한다.
최종 위반을 직감으로 답하지 말고 세 축을 서로 독립적으로 읽어라.
1) 이 공고가 v16의 일반제품·금액구간 적용대상인지,
2) 중기업을 포함하는 중소기업 제한이 실제 입찰참가자격으로 작용하는지,
3) 판로지원 예외가 명시됐는지 확인한다.

중·소기업·소상공인 또는 중소기업 확인서를 입찰 전에 요구하면 BIDDER_BROAD다.
소기업·소상공인만이면 SMALL_ONLY다. 낙찰자·계약상대자의 계약 후 제출, 단순 서류목록,
해당 시 제출, 평가 우대, 법명 인용은 POST_AWARD_OR_REFERENCE다.
전자조달 조항 내용만으로 원문에 제한이 있다고 만들지 마라. 다만 업무·가격·제품·명시적
예외의 적용성 사실은 원문과 함께 대조하라. quote는 이 pass의 실제 공고 원문에서만
변경 없이 연속된 0~500자를 복사하고, 찾지 못했으면 빈 문자열로 둔다.
JSON 밖 설명을 쓰지 않는다."""

SCHEMA_V2 = {
    "type": "object",
    "properties": {
        "applicability": {
            "type": "string", "enum": ["APPLIES", "NOT_APPLIES", "UNCLEAR"],
        },
        "qualification": {
            "type": "string",
            "enum": ["BIDDER_BROAD", "SMALL_ONLY", "POST_AWARD_OR_REFERENCE", "NOT_FOUND", "UNCLEAR"],
        },
        "qualification_quote": {"type": "string", "maxLength": 500},
        "exception": {
            "type": "string", "enum": ["EXPLICIT", "NOT_FOUND", "UNCLEAR"],
        },
        "exception_quote": {"type": "string", "maxLength": 500},
    },
    "required": [
        "applicability", "qualification", "qualification_quote", "exception", "exception_quote",
    ],
    "additionalProperties": False,
}


def parse_v16_response(
    response: Mapping[str, Any],
    user_message: str = "",
    contract_version: str = "v16-only-v1",
) -> int:
    if response.get("finish_reason") != "stop" or response.get("invalid") is True:
        raise ValueError("response did not finish normally")
    value = json.loads(str(response.get("content", "")))
    if contract_version == "v16-only-v1":
        if not isinstance(value, dict) or set(value) != {"v16"}:
            raise ValueError("v16 response shape mismatch")
        if type(value["v16"]) is not int or value["v16"] not in (0, 1):
            raise ValueError("v16 response is not binary")
        return value["v16"]
    if contract_version != "v16-observation-v2":
        raise ValueError("unknown v16 output contract")
    marker = "[실제 공고 원문 — 이 pass의 연속 원문]\n"
    if marker not in user_message:
        raise ValueError("rendered message lacks actual-source boundary")
    actual_source = user_message.split(marker, 1)[1]
    required = {
        "applicability", "qualification", "qualification_quote", "exception", "exception_quote",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("v16 observation response shape mismatch")
    if value["applicability"] not in {"APPLIES", "NOT_APPLIES", "UNCLEAR"}:
        raise ValueError("invalid applicability")
    if value["qualification"] not in {
        "BIDDER_BROAD", "SMALL_ONLY", "POST_AWARD_OR_REFERENCE", "NOT_FOUND", "UNCLEAR",
    }:
        raise ValueError("invalid qualification")
    if value["exception"] not in {"EXPLICIT", "NOT_FOUND", "UNCLEAR"}:
        raise ValueError("invalid exception")
    for key in ("qualification_quote", "exception_quote"):
        quote = value[key]
        if not isinstance(quote, str) or len(quote) > 500:
            raise ValueError(f"invalid {key}")
        if quote and quote not in actual_source:
            raise ValueError(f"{key} is not an exact actual rendered source substring")
    if value["qualification"] in {"BIDDER_BROAD", "SMALL_ONLY", "POST_AWARD_OR_REFERENCE"} \
            and not value["qualification_quote"]:
        raise ValueError("classified qualification requires a quote")
    if value["exception"] == "EXPLICIT" and not value["exception_quote"]:
        raise ValueError("explicit exception requires a quote")
    contrary = (
        value["applicability"] == "NOT_APPLIES"
        or value["qualification"] == "BIDDER_BROAD"
        or value["exception"] == "EXPLICIT"
    )
    return 0 if contrary else 1


def _read_rows(path: Path) -> dict[str, dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = {}
        for source in csv.DictReader(handle):
            row: dict[str, Any] = {"id": source["id"]}
            row.update({f"v{i}": int(source[f"v{i}"]) for i in range(1, 25)})
            row.update({f"e{i}": source[f"e{i}"] for i in range(1, 25)})
            rows[str(row["id"])] = row
        return rows


def _ordered_documents(record: Any) -> list[Any]:
    unknown = {document.document_type for document in record.documents} - set(DOCUMENT_ORDER)
    if unknown:
        raise ValueError(f"{record.notice_id}: unknown document types: {sorted(unknown)}")
    return sorted(
        record.documents,
        key=lambda document: (DOCUMENT_ORDER[document.document_type], document.order),
    )


def _fixed_context(
    record: Any, card: str, product_index: Mapping[str, Mapping[str, str]],
) -> str:
    metadata = render_metadata_facts(build_metadata_facts(record.metadata, ("v16",)))
    metadata_products = render_product_facts(build_product_facts(record.metadata, product_index))
    document_products = render_document_product_mentions(
        collect_document_product_mentions(record, product_index)
    )
    return (
        f"[판정 대상 공고] {record.notice_id}\n\n"
        f"[v16 판정 계약]\n{card}\n\n"
        f"[주최측 전자조달 입력 사실]\n{metadata}\n\n"
        f"[메타데이터 제품코드의 CSV exact 대조]\n{metadata_products}\n\n"
        f"[모든 문서의 제품코드 후보와 CSV exact 대조]\n{document_products}\n\n"
    )


def _document_block(document: Any, text: str, start: int, end: int) -> str:
    return (
        f"[문서: {document.document_type} / {document.doc_id} / "
        f"원문 문자 {start}:{end}]\n{text}"
    )


def _task(
    record: Any, fixed: str, blocks: Sequence[str], part: int, contract_version: str,
) -> dict[str, Any]:
    user = fixed + "[실제 공고 원문 — 이 pass의 연속 원문]\n" + "\n\n".join(blocks)
    return {
        "id": record.notice_id,
        "arm": "V16_FULL_SOURCE_VERIFY",
        "part": part,
        "messages": [
            {"role": "system", "content": (
                SYSTEM_MESSAGE_V1 if contract_version == "v16-only-v1" else SYSTEM_MESSAGE_V2
            )},
            {"role": "user", "content": user},
        ],
        "schema": SCHEMA_V1 if contract_version == "v16-only-v1" else SCHEMA_V2,
    }


def build_v16_tasks(
    record: Any,
    card: str,
    product_index: Mapping[str, Mapping[str, str]],
    counter: GemmaTokenCounter,
    budget: int,
    contract_version: str = "v16-only-v1",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Cover every source character exactly once when an all-document task overflows."""
    fixed = _fixed_context(record, card, product_index)
    documents = _ordered_documents(record)
    full_blocks = [
        _document_block(document, document.text, 0, len(document.text))
        for document in documents
    ]
    full = _task(record, fixed, full_blocks, 1, contract_version)
    full_tokens = counter.count(full["messages"])
    if full_tokens <= budget:
        ledger = [{
            "part": 1,
            "tokens": full_tokens,
            "spans": [{
                "doc_id": document.doc_id,
                "document_type": document.document_type,
                "document_sha256": document.sha256,
                "start": 0,
                "end": len(document.text),
            } for document in documents],
        }]
        return [full], ledger

    atomic_blocks: list[tuple[Any, int, int, str]] = []
    for document in documents:
        start = 0
        while start < len(document.text):
            low, high = start + 1, len(document.text)
            best = start
            while low <= high:
                middle = (low + high) // 2
                block = _document_block(
                    document, document.text[start:middle], start, middle,
                )
                candidate = _task(record, fixed, [block], 1, contract_version)
                if counter.count(candidate["messages"]) <= budget:
                    best = middle
                    low = middle + 1
                else:
                    high = middle - 1
            if best == start:
                raise ValueError(
                    f"{record.notice_id}/{document.doc_id}: fixed context leaves no source capacity"
                )
            atomic_blocks.append((
                document, start, best,
                _document_block(document, document.text[start:best], start, best),
            ))
            start = best

    packs: list[list[tuple[Any, int, int, str]]] = []
    current: list[tuple[Any, int, int, str]] = []
    for block in atomic_blocks:
        trial = [*current, block]
        task = _task(
            record, fixed, [value[3] for value in trial], len(packs) + 1, contract_version,
        )
        if counter.count(task["messages"]) <= budget:
            current = trial
            continue
        if not current:
            raise ValueError(f"{record.notice_id}: atomic source block exceeds budget")
        packs.append(current)
        current = [block]
    if current:
        packs.append(current)

    tasks, ledger = [], []
    for part, pack in enumerate(packs, 1):
        task = _task(record, fixed, [value[3] for value in pack], part, contract_version)
        tokens = counter.count(task["messages"])
        if tokens > budget:
            raise ValueError(f"{record.notice_id}/p{part:02d}: token admission failed")
        tasks.append(task)
        ledger.append({
            "part": part,
            "tokens": tokens,
            "spans": [{
                "doc_id": document.doc_id,
                "document_type": document.document_type,
                "document_sha256": document.sha256,
                "start": start,
                "end": end,
            } for document, start, end, _ in pack],
        })

    reconstructed: dict[str, list[tuple[int, int]]] = {}
    for row in ledger:
        for span in row["spans"]:
            reconstructed.setdefault(span["doc_id"], []).append((span["start"], span["end"]))
    for document in documents:
        spans = sorted(reconstructed.get(document.doc_id, []))
        cursor = 0
        for start, end in spans:
            if start != cursor or end <= start:
                raise ValueError(f"{record.notice_id}/{document.doc_id}: source gap or overlap")
            cursor = end
        if cursor != len(document.text):
            raise ValueError(f"{record.notice_id}/{document.doc_id}: incomplete source coverage")
    return tasks, ledger


def prepare_v16_tasks(
    config: CleanExperimentConfig,
    notice_ids: Sequence[str],
    inputs: Sequence[Path],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any], dict[str, Any]]:
    records = {}
    for path in inputs:
        for record in load_notice_records(path):
            if record.notice_id in notice_ids:
                records[record.notice_id] = record
    if set(records) != set(notice_ids):
        raise ValueError("v16 panel has IDs missing from supplied inputs")
    root = config.path.parents[2]
    policy = config.raw["v16_full_source_verifier"]
    contract_version = str(policy["output_contract"])
    if contract_version not in {"v16-only-v1", "v16-observation-v2"}:
        raise ValueError("unsupported v16 output contract")
    cards = load_card_texts(root / policy["card_path"])
    product_index = load_product_index(root / policy["product_index_path"])
    counter = GemmaTokenCounter(config.tokenizer_dir)
    tasks: dict[str, dict[str, Any]] = {}
    source_ledger: dict[str, Any] = {}
    for notice_id in notice_ids:
        record = records[notice_id]
        notice_tasks, ledger = build_v16_tasks(
            record, cards["v16"], product_index, counter, config.prompt_budget,
            contract_version,
        )
        for task in notice_tasks:
            task_id = f"{notice_id}__p{task['part']:02d}"
            task["task_id"] = task_id
            tasks[task_id] = task
        source_ledger[notice_id] = {
            "documents": len(record.documents),
            "document_characters": sum(len(document.text) for document in record.documents),
            "parts": ledger,
            "covered_characters": sum(
                span["end"] - span["start"] for row in ledger for span in row["spans"]
            ),
        }
    return tasks, source_ledger, records


def _call_tasks(
    config: CleanExperimentConfig,
    tasks: Mapping[str, Mapping[str, Any]],
    output_dir: Path,
    api_key: str,
) -> tuple[dict[str, int], dict[str, Any]]:
    runtime = OpenRouterRuntime(config.provider, api_key)
    counter = GemmaTokenCounter(config.tokenizer_dir)
    values: dict[str, int] = {}
    contract_version = str(config.raw["v16_full_source_verifier"]["output_contract"])
    invalid = []
    calls = 0
    started = time.monotonic()
    for task_id in sorted(tasks):
        task = dict(tasks[task_id])
        task_hash = counter.task_sha256(task)
        valid = None
        errors = []
        for attempt in range(1, 4):
            response_path = output_dir / "response_attempts" / task_id / f"attempt_{attempt:03d}.json"
            if response_path.exists():
                response = json.loads(response_path.read_text(encoding="utf-8"))
                if response.get("task_sha256") != task_hash:
                    raise ValueError(f"{task_id}: checkpoint/task mismatch")
            else:
                try:
                    response = runtime.complete(task)
                except RuntimeError as error:
                    response = {"invalid": True, "error": str(error), "usage": {}, "attempts": 0}
                response["task_sha256"] = task_hash
                atomic_json(response_path, response)
                calls += 1
            try:
                valid = parse_v16_response(
                    response, str(task["messages"][1]["content"]), contract_version,
                )
                break
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                errors.append(str(error))
        if valid is None:
            invalid.append({"task_id": task_id, "errors": errors})
        else:
            values[task_id] = valid
        completed = len(values) + len(invalid)
        if completed % 5 == 0 or completed == len(tasks):
            atomic_json(output_dir / f"checkpoint_{completed:03d}.json", {
                "completed_tasks": completed,
                "valid": len(values),
                "invalid": len(invalid),
                "new_calls": calls,
                "elapsed_seconds": time.monotonic() - started,
            })
    return values, {
        "tasks": len(tasks), "valid": len(values), "invalid": invalid,
        "new_calls": calls, "elapsed_seconds": time.monotonic() - started,
    }


def run_v16_verifier(
    config: CleanExperimentConfig,
    *,
    mode: str,
    mock: bool,
    api_key: str = "",
) -> dict[str, Any]:
    if mode not in {"micro", "dev200"}:
        raise ValueError("mode must be micro or dev200")
    manifest = compare_manifests(config.path, config.path.parents[2])
    if manifest["status"] != "PASS":
        raise ValueError("manifest policy diff failed")
    root = config.path.parents[2]
    policy = config.raw["v16_full_source_verifier"]
    base_rows = _read_rows(root / policy["base_submission_path"])
    if mode == "dev200":
        notice_ids = [notice_id for notice_id, row in base_rows.items() if row["v16"] == 1]
        inputs = [config.input_path]
    else:
        notice_ids = list(policy["micro_notice_ids"])
        inputs = [config.input_path, root / policy["population_input_path"]]
    tasks, ledger, records = prepare_v16_tasks(config, notice_ids, inputs)
    output_dir = config.output_dir / mode
    output_dir.mkdir(parents=True, exist_ok=True)
    atomic_json(output_dir / "manifest.snapshot.json", config.raw)
    atomic_json(output_dir / "source_ledger.json", ledger)
    token_counts = {
        task_id: next(
            row["tokens"] for row in ledger[task["id"]]["parts"]
            if row["part"] == task["part"]
        ) for task_id, task in tasks.items()
    }
    samples = {
        "short_complete": min(tasks, key=token_counts.get),
        "largest_or_overflow": max(tasks, key=token_counts.get),
    }
    attachment = next((
        task_id for task_id, task in tasks.items()
        if len(records[task["id"]].documents) > 1
    ), None)
    if attachment:
        samples["attachment"] = attachment
    for role, task_id in samples.items():
        atomic_json(output_dir / "rendered_inputs" / f"{role}_{task_id}.json", tasks[task_id])
    preflight = {
        "status": "PASS",
        "mode": mode,
        "notices": len(notice_ids),
        "tasks": len(tasks),
        "documents": sum(len(records[notice_id].documents) for notice_id in notice_ids),
        "source_characters": sum(
            sum(len(document.text) for document in records[notice_id].documents)
            for notice_id in notice_ids
        ),
        "covered_characters": sum(row["covered_characters"] for row in ledger.values()),
        "token_min": min(token_counts.values()),
        "token_max": max(token_counts.values()),
        "rendered_inputs": samples,
        "llm_calls": 0,
        "manifest_diff": manifest,
    }
    if preflight["source_characters"] != preflight["covered_characters"]:
        raise ValueError("source character coverage differs")
    atomic_json(output_dir / "preflight.json", preflight)
    semantic_contract = {
        "status": "PASS",
        "items": {
            f"v{index}": (
                {
                    "owner": "v16-positive-only-full-source-verifier-v1",
                    "applicability": "decision card v6 plus 업무구분/계약방법/입찰추정가격",
                    "one_condition": "decision card v6; final AND finds no contrary fact in any pass",
                    "zero_conditions": [
                        "competition-product or other non-applicability from exact product facts/source",
                        "actual bidder-facing SME qualification in source",
                        "explicit 판로지원 exception in metadata/source",
                    ],
                    "metadata": ["업무구분", "계약방법", "입찰추정가격", "조항호내용"],
                    "products": "metadata and all-document 10-digit exact-code CSV facts",
                    "documents": "all supplied document characters with type/doc-id provenance",
                    "merge": "pass-level AND; invalid preserves base positive",
                    "rendered_span": "every source span listed in source_ledger.json",
                }
                if index == 16 else
                {"owner": "unchanged-from-S001", "policy_change": False}
            ) for index in range(1, 25)
        },
        "changed_items": ["v16"],
        "unchanged_items": [f"v{index}" for index in range(1, 25) if index != 16],
    }
    atomic_json(output_dir / "semantic_contract.json", semantic_contract)
    if mock:
        for task in tasks.values():
            contract_version = str(policy["output_contract"])
            content = (
                '{"v16":1}' if contract_version == "v16-only-v1" else
                '{"applicability":"APPLIES","qualification":"NOT_FOUND",'
                '"qualification_quote":"","exception":"NOT_FOUND","exception_quote":""}'
            )
            parse_v16_response(
                {"content": content, "finish_reason": "stop"},
                str(task["messages"][1]["content"]), contract_version,
            )
        return preflight
    values, call_report = _call_tasks(config, tasks, output_dir, api_key)
    by_notice: dict[str, list[int]] = {}
    for task_id, value in values.items():
        by_notice.setdefault(tasks[task_id]["id"], []).append(value)
    results = {}
    for notice_id in notice_ids:
        task_ids = sorted(task_id for task_id, task in tasks.items() if task["id"] == notice_id)
        valid_values = [values[task_id] for task_id in task_ids if task_id in values]
        results[notice_id] = {
            "task_ids": task_ids,
            "valid_parts": len(valid_values),
            "parts": len(task_ids),
            "v16": min(valid_values) if len(valid_values) == len(task_ids) else 1,
            "invalid_fallback_to_base": len(valid_values) != len(task_ids),
        }
    report: dict[str, Any] = {
        "status": "PASS",
        "mode": mode,
        "preflight": preflight,
        "calls": call_report,
        "results": results,
    }
    if mode == "dev200":
        merged = {notice_id: dict(row) for notice_id, row in base_rows.items()}
        for notice_id, result in results.items():
            merged[notice_id]["v16"] = result["v16"]
            merged[notice_id]["e16"] = ""
        rows = list(merged.values())
        metrics = evaluate_rows(rows, config.labels_path, {
            "fast20": config.fast_panel_path,
            "holdout20": config.holdout_panel_path,
        })
        changed = [
            {"id": notice_id, "before": base_rows[notice_id]["v16"], "after": row["v16"]}
            for notice_id, row in merged.items()
            if row["v16"] != base_rows[notice_id]["v16"]
        ]
        report.update(metrics=metrics, changed_v16=changed, changed_v16_count=len(changed))
        atomic_json(output_dir / "metrics.json", metrics)
    atomic_json(output_dir / "run_report.json", report)
    return report
