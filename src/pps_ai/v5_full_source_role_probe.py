"""Full-source, source-only bidder-location observation for a fixed v5 panel."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import importlib
import json
from pathlib import Path
import time
from typing import Any, Callable, Mapping, Sequence

from .config import CleanExperimentConfig
from .ingest import load_notice_records
from .preflight import compare_manifests
from .reference.frozen import FrozenL41Reference
from .runtime.openrouter import OpenRouterRuntime, atomic_json
from .runtime.tokenizer import GemmaTokenCounter
from .v5_role_guard_diagnostic import frozen_v5_positive
from .views.native_full_prompt import DOCUMENT_ORDER


ROLES = ("BIDDER_LOCATION", "NOT_BIDDER_LOCATION", "UNCLEAR")
SYSTEM = (
    "당신은 공공 입찰공고 원문의 지역 문구가 누구의 위치를 어떤 목적으로 요구하는지 관찰한다. "
    "이 작업에서는 v5 위반 여부, 금액 기준, 법률상 허용 예외를 판정하지 않는다. "
    "모든 제공 문서를 읽고 실제 입찰참가자가 입찰 전부터 본점·주된 영업소·사업장을 "
    "특정 지역에 두어야만 참가할 수 있는 필수 자격이 하나라도 있으면 BIDDER_LOCATION이다. "
    "지역기업 가점·정량평가, 과거 납품처의 위치, 현장·납품지, 계약 후 지역업체 이용, "
    "참가 허용 예시, 일반 등록 안내만 있으면 NOT_BIDDER_LOCATION이다. "
    "둘을 함께 발견하면 실제 필수 참가조건을 우선하여 BIDDER_LOCATION으로 답한다. "
    "원문이 잘렸거나 역할이 불명확하면 UNCLEAR로 답한다. "
    "BIDDER_LOCATION이면 필수 참가조건의 원문에서 변경 없는 연속된 1~500자를 quote로 복사한다. "
    "그 외에는 quote를 비워도 되며, 적었다면 실제 원문의 연속된 1~500자여야 한다. "
    "JSON 한 개만 출력한다."
)
SCHEMA = {
    "type": "object",
    "properties": {
        "role": {"type": "string", "enum": list(ROLES)},
        "quote": {"type": "string", "maxLength": 500},
    },
    "required": ["role", "quote"],
    "additionalProperties": False,
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _ordered_documents(record: Any) -> list[Any]:
    unknown = {doc.document_type for doc in record.documents} - set(DOCUMENT_ORDER)
    if unknown:
        raise ValueError(f"{record.notice_id}: unknown document types {sorted(unknown)}")
    return sorted(record.documents, key=lambda doc: (DOCUMENT_ORDER[doc.document_type], doc.order))


def _document_block(document: Any, start: int, end: int) -> str:
    return (
        f"[문서 {document.document_type} / {document.doc_id} / 원문 문자 {start}:{end}]\n"
        f"{document.text[start:end]}"
    )


def _fixed(record: Any, *, anchor: bool) -> str:
    meta = record.metadata
    lines = [
        f"공고 ID: {record.notice_id}",
        "[전자조달 입력 — 원문 참가제한의 증거가 아님]",
        f"적용 계약법: {meta.get('적용계약법') or '미기재'}",
        f"업무구분: {meta.get('업무구분') or '미기재'}",
        f"계약방법: {meta.get('계약방법') or '미기재'}",
        f"낙찰방법: {meta.get('낙찰방법') or '미기재'}",
        f"추정가격(원, 부가가치세 제외): {meta.get('입찰추정가격')}",
    ]
    if anchor:
        notice = next((doc for doc in _ordered_documents(record) if doc.document_type == "공고문"), None)
        if notice is None:
            raise ValueError(f"{record.notice_id}: no announcement anchor")
        lines.extend([
            "[반복 공고문 anchor — 원문 범위와 중복; 참가조건 확정 근거로 단독 사용 금지]",
            f"{notice.text[:1200]}",
        ])
    return "\n".join(lines)


def _task(record: Any, blocks: Sequence[str], part: int, *, anchor: bool) -> dict[str, Any]:
    user = _fixed(record, anchor=anchor) + "\n\n[실제 공고 원문 — 이 pass의 범위]\n" + "\n\n".join(blocks)
    return {
        "id": record.notice_id, "arm": "V5_SOURCE_ROLE", "part": part,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
        "schema": SCHEMA,
    }


def build_role_tasks(
    record: Any, counter: GemmaTokenCounter, budget: int,
    task_factory: Callable[..., dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Token-admit all documents; overflow repeats an announcement anchor and covers every character."""
    make_task = task_factory or _task
    documents = _ordered_documents(record)
    full = make_task(
        record, [_document_block(doc, 0, len(doc.text)) for doc in documents], 1,
        anchor=False,
    )
    full_tokens = counter.count(full["messages"])
    if full_tokens <= budget:
        full["source_texts"] = [doc.text for doc in documents]
        return [full], [{
            "part": 1, "tokens": full_tokens, "anchor_repeated": False,
            "spans": [{
                "doc_id": doc.doc_id, "document_type": doc.document_type,
                "document_sha256": doc.sha256, "start": 0, "end": len(doc.text),
            } for doc in documents],
        }]

    atoms: list[tuple[Any, int, int, str]] = []
    for doc in documents:
        start = 0
        while start < len(doc.text):
            low, high, best = start + 1, len(doc.text), start
            while low <= high:
                middle = (low + high) // 2
                block = _document_block(doc, start, middle)
                if counter.count(make_task(record, [block], 1, anchor=True)["messages"]) <= budget:
                    best = middle
                    low = middle + 1
                else:
                    high = middle - 1
            if best == start:
                raise ValueError(f"{record.notice_id}/{doc.doc_id}: no source capacity")
            atoms.append((doc, start, best, _document_block(doc, start, best)))
            start = best

    packs: list[list[tuple[Any, int, int, str]]] = []
    current: list[tuple[Any, int, int, str]] = []
    for atom in atoms:
        trial = [*current, atom]
        task = make_task(record, [value[3] for value in trial], len(packs) + 1, anchor=True)
        if counter.count(task["messages"]) <= budget:
            current = trial
        else:
            if not current:
                raise ValueError(f"{record.notice_id}: atomic block exceeds budget")
            packs.append(current)
            current = [atom]
    if current:
        packs.append(current)

    tasks: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []
    for part, pack in enumerate(packs, 1):
        task = make_task(record, [value[3] for value in pack], part, anchor=True)
        task["source_texts"] = [doc.text[start:end] for doc, start, end, _ in pack]
        tokens = counter.count(task["messages"])
        if tokens > budget:
            raise ValueError(f"{record.notice_id}/p{part}: overflow")
        tasks.append(task)
        ledger.append({
            "part": part, "tokens": tokens, "anchor_repeated": True,
            "spans": [{
                "doc_id": doc.doc_id, "document_type": doc.document_type,
                "document_sha256": doc.sha256, "start": start, "end": end,
            } for doc, start, end, _ in pack],
        })
    _validate_coverage(record, ledger)
    return tasks, ledger


def _validate_coverage(record: Any, ledger: Sequence[Mapping[str, Any]]) -> None:
    spans_by_doc: dict[str, list[tuple[int, int]]] = {}
    for pass_info in ledger:
        for span in pass_info["spans"]:
            spans_by_doc.setdefault(span["doc_id"], []).append((span["start"], span["end"]))
    for doc in _ordered_documents(record):
        cursor = 0
        for start, end in sorted(spans_by_doc.get(doc.doc_id, [])):
            if start != cursor or end <= start:
                raise ValueError(f"{record.notice_id}/{doc.doc_id}: source gap or overlap")
            cursor = end
        if cursor != len(doc.text):
            raise ValueError(f"{record.notice_id}/{doc.doc_id}: incomplete source")


def parse_role_response(response: Mapping[str, Any], task: Mapping[str, Any]) -> dict[str, str]:
    if response.get("finish_reason") != "stop" or response.get("invalid") is True:
        raise ValueError("response did not finish normally")
    value = json.loads(str(response.get("content") or ""))
    if not isinstance(value, dict) or set(value) != {"role", "quote"}:
        raise ValueError("role response shape mismatch")
    if value["role"] not in ROLES or not isinstance(value["quote"], str):
        raise ValueError("role response type/enum mismatch")
    quote = value["quote"]
    if len(quote) > 500 or (quote and not any(quote in text for text in task["source_texts"])):
        raise ValueError("quote is not an exact current source substring")
    if value["role"] == "BIDDER_LOCATION" and not quote:
        raise ValueError("positive role requires quote")
    return {"role": value["role"], "quote": quote}


def _records(config: CleanExperimentConfig) -> tuple[list[str], dict[str, Any], dict[str, str]]:
    policy = config.raw["v5_full_source_role_probe"]
    review_path = config.path.parents[2] / policy["source_review_path"]
    review = json.loads(review_path.read_text(encoding="utf-8"))
    reviewed_ids = [row["id"] for row in review["cases"] if row["owner"] == "v5"]
    ids = [*policy["dev_ids"], *reviewed_ids, *policy["blind_ids"]]
    if len(ids) != policy["max_notices"] or len(set(ids)) != len(ids):
        raise ValueError("fixed panel IDs invalid")
    population_path = config.path.parents[2] / policy["unlabeled_input_path"]
    chosen = set(ids)
    records = {}
    provenance = {}
    for path in (config.input_path, population_path):
        for record in load_notice_records(path):
            if record.notice_id in chosen:
                if record.notice_id in records:
                    raise ValueError(f"duplicate panel ID: {record.notice_id}")
                records[record.notice_id] = record
                provenance[record.notice_id] = str(path)
    if set(records) != chosen:
        raise ValueError(f"panel source missing: {sorted(chosen - set(records))}")
    frozen = FrozenL41Reference(config.reference_zip, config.reference_zip_sha256)
    hits = importlib.import_module("dev.run_v5_amount_region_experiment_v2")
    gate = importlib.import_module("dev.run_v5_amount_region_experiment")
    for notice_id in ids:
        if not frozen_v5_positive(records[notice_id].raw, hits, gate):
            raise ValueError(f"{notice_id}: not a frozen v5 positive candidate")
    return ids, records, provenance


def prepare_probe(config: CleanExperimentConfig) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    manifest = compare_manifests(config.path, config.path.parents[2])
    if manifest["status"] != "PASS":
        raise ValueError("manifest policy diff failed")
    ids, records, provenance = _records(config)
    counter = GemmaTokenCounter(config.tokenizer_dir)
    tasks: list[dict[str, Any]] = []
    ledger: list[dict[str, Any]] = []
    for notice_id in ids:
        record = records[notice_id]
        passes, source = build_role_tasks(record, counter, config.prompt_budget)
        _validate_coverage(record, source)
        for task, pass_info in zip(passes, source, strict=True):
            tasks.append(task)
            ledger.append({
                "id": notice_id, "source_path": provenance[notice_id],
                "source_file_sha256": _sha256(Path(provenance[notice_id])),
                "document_count": len(record.documents),
                "task_sha256": counter.task_sha256(task), **pass_info,
            })
    return tasks, ledger


def _aggregate(rows: Sequence[Mapping[str, Any]]) -> str:
    roles = [row["role"] for row in rows if row.get("valid")]
    if "BIDDER_LOCATION" in roles:
        return "BIDDER_LOCATION"
    if len(roles) == len(rows) and all(role == "NOT_BIDDER_LOCATION" for role in roles):
        return "NOT_BIDDER_LOCATION"
    return "UNCLEAR"


def run_probe(config: CleanExperimentConfig, *, mock: bool, api_key: str = "") -> dict[str, Any]:
    tasks, ledger = prepare_probe(config)
    output = config.output_dir
    output.mkdir(parents=True, exist_ok=True)
    atomic_json(output / "manifest.snapshot.json", config.raw)
    atomic_json(output / "source_ledger.json", ledger)
    for task in tasks:
        atomic_json(output / "rendered" / f"{task['id']}__p{task['part']:02d}.json", task)
    if mock:
        for task in tasks:
            parse_role_response({"content": '{"role":"UNCLEAR","quote":""}', "finish_reason": "stop", "invalid": False}, task)
        report = {
            "status": "PASS", "mode": "mock", "notices": len({task["id"] for task in tasks}),
            "calls": len(tasks), "tokens": sum(row["tokens"] for row in ledger),
            "overflow_notices": sorted({row["id"] for row in ledger if row["anchor_repeated"]}),
            "llm_calls": 0,
        }
        atomic_json(output / "mock_report.json", report)
        return report
    runtime = OpenRouterRuntime(config.provider, api_key)
    started = time.monotonic()
    results: list[dict[str, Any]] = []

    def complete(task: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
        path = output / "responses" / f"{task['id']}__p{task['part']:02d}.json"
        if path.exists():
            response = json.loads(path.read_text(encoding="utf-8"))
            if response.get("task_sha256") != source["task_sha256"]:
                raise ValueError(f"{task['id']}: response checkpoint mismatch")
        else:
            try:
                response = runtime.complete(task)
            except RuntimeError as error:
                response = {"invalid": True, "error": str(error), "usage": {}, "attempts": 0}
            response["task_sha256"] = source["task_sha256"]
            atomic_json(path, response)
        try:
            parsed = parse_role_response(response, task)
            return {"id": task["id"], "part": task["part"], "valid": True, **parsed,
                    "usage": response.get("usage", {}), "attempts": response.get("attempts", 0)}
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
            return {"id": task["id"], "part": task["part"], "valid": False,
                    "error": str(error), "usage": response.get("usage", {}),
                    "attempts": response.get("attempts", 0)}

    with ThreadPoolExecutor(max_workers=min(config.provider.concurrency, len(tasks))) as pool:
        futures = [pool.submit(complete, task, source) for task, source in zip(tasks, ledger, strict=True)]
        for future in as_completed(futures):
            results.append(future.result())
            if len(results) % 5 == 0 or len(results) == len(tasks):
                atomic_json(output / f"checkpoint_{len(results):02d}.json", {
                    "completed": len(results),
                    "invalid": sum(not row["valid"] for row in results),
                    "elapsed_seconds": time.monotonic() - started,
                    "results": sorted(results, key=lambda row: (row["id"], row["part"])),
                })
    by_id: dict[str, list[dict[str, Any]]] = {}
    for row in results:
        by_id.setdefault(row["id"], []).append(row)
    report = {
        "status": "COMPLETE", "mode": "api", "notices": len(by_id), "calls": len(tasks),
        "invalid": sum(not row["valid"] for row in results),
        "elapsed_seconds": time.monotonic() - started,
        "prompt_tokens_admitted": sum(row["tokens"] for row in ledger),
        "usage_prompt_tokens": sum(row.get("usage", {}).get("prompt_tokens", 0) for row in results),
        "usage_completion_tokens": sum(row.get("usage", {}).get("completion_tokens", 0) for row in results),
        "per_notice": {notice_id: {
            "role": _aggregate(rows), "parts": sorted(rows, key=lambda row: row["part"]),
        } for notice_id, rows in sorted(by_id.items())},
        "final_v5_labels_changed": 0,
        "limitation": "Source-role diagnostic only; not a complete v5 legal judgment or public F1 estimate.",
    }
    atomic_json(output / "report.json", report)
    return report
