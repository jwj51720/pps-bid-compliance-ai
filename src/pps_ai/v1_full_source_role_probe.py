"""Fixed-panel, full-source observation of v1 bidder-organization role."""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import hashlib
import importlib
import json
from pathlib import Path
import time
from typing import Any, Mapping

from .config import CleanExperimentConfig
from .decisions.v19_quote_resolution_v2 import resolve_exact_quote
from .ingest import load_notice_records
from .preflight import compare_manifests
from .reference.frozen import FrozenL41Reference
from .runtime.openrouter import OpenRouterRuntime, atomic_json
from .runtime.tokenizer import GemmaTokenCounter
from .v5_full_source_role_probe import _fixed, build_role_tasks, _validate_coverage


ROLES = ("EXCLUSIVE_BIDDER_ORGANIZATION", "NOT_EXCLUSIVE", "UNCLEAR")
SYSTEM = (
    "당신은 공공 입찰공고의 실제 입찰참가자격을 원문에서 관찰한다. "
    "이 단계에서는 v1 법률 위반 여부나 허용 예외의 최종 판단을 출력하지 않는다. "
    "모든 제공 문서를 읽고, 대학·연구기관·특정 법인 등 기관 종류만으로 실제 입찰자 참여를 "
    "필수적으로 닫은 조항이 하나라도 있으면 EXCLUSIVE_BIDDER_ORGANIZATION이다. "
    "일반 면허·등록·신고·보안적합성, 특정 제조사 등록, 시설·인력 선보유, "
    "참가 가능 예시, 수요자·관람객·평가위원·계약 후 수행인력의 참여만 있으면 "
    "NOT_EXCLUSIVE다. 둘 다 있으면 실제 입찰자 제한을 우선한다. "
    "원문이 나뉘어 이 pass만으로 확정할 수 없거나 역할이 모호하면 UNCLEAR다. "
    "EXCLUSIVE_BIDDER_ORGANIZATION이면 해당 참가조건의 현재 pass 실제 원문에서 "
    "변경 없는 연속된 1~500자를 quote로 복사한다. 나머지는 quote를 비워도 된다. "
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
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _task(record: Any, blocks: list[str], part: int, *, anchor: bool) -> dict[str, Any]:
    user = (
        _fixed(record, anchor=anchor)
        + "\n\n[실제 공고 원문 — 현재 pass의 판정 범위]\n"
        + "\n\n".join(blocks)
    )
    return {
        "id": record.notice_id, "arm": "V1_SOURCE_ROLE", "part": part,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
        "schema": SCHEMA,
    }


def parse_response(response: Mapping[str, Any], task: Mapping[str, Any]) -> dict[str, Any]:
    if response.get("finish_reason") != "stop" or response.get("invalid") is True:
        raise ValueError("response did not finish normally")
    value = json.loads(str(response.get("content") or ""))
    if not isinstance(value, dict) or set(value) != {"role", "quote"}:
        raise ValueError("role response shape mismatch")
    role, quote = value["role"], value["quote"]
    if role not in ROLES or not isinstance(quote, str) or len(quote) > 500:
        raise ValueError("role/quote contract mismatch")
    if role == "EXCLUSIVE_BIDDER_ORGANIZATION" and not quote:
        raise ValueError("positive role requires quote")
    if not quote:
        return {"role": role, "quote": "", "quote_method": "EMPTY"}
    matches = []
    for index, source in enumerate(task["source_texts"]):
        resolved, method = resolve_exact_quote(source, quote)
        if resolved is not None:
            matches.append((index, resolved, method))
    if not matches:
        raise ValueError("quote is not recoverable from current actual source")
    exact = [match for match in matches if match[2] == "BYTE_EXACT"]
    source_index, resolved, method = (exact or matches)[0]
    return {
        "role": role, "quote": resolved, "quote_method": method,
        "source_fragment_index": source_index, "quote_matches": len(matches),
    }


def _panel(config: CleanExperimentConfig) -> tuple[list[str], dict[str, Any], dict[str, str]]:
    root = config.path.parents[2]
    policy = config.raw["v1_positive_source_role_verification"]
    with config.labels_path.open(encoding="utf-8", newline="") as handle:
        labeled_positive = {row["id"] for row in csv.DictReader(handle) if row["v1"] == "1"}
    review = json.loads((root / policy["source_review_path"]).read_text(encoding="utf-8"))
    known_all = {row["id"] for row in review["cases"] if row["owner"] == "v1"}
    frozen = FrozenL41Reference(config.reference_zip, config.reference_zip_sha256)
    v1 = importlib.import_module("dev.run_v1_organization_capacity_experiment_v3")
    dev_ids = []
    for record in frozen.baseline.iter_records(str(config.input_path)):
        kinds = {
            kind for kind, _ in
            v1.same_line_candidate_hits(record, "plus_all_manufacturer_registration")
        }
        if str(record["id"]) in labeled_positive and kinds == {"organization_only"}:
            dev_ids.append(str(record["id"]))
    dev_ids.sort()
    if len(dev_ids) != policy["dev_positive_count"]:
        raise ValueError("dev organization-only positive count differs")
    positives = []
    for record in frozen.baseline.iter_records(str(root / policy["unlabeled_input_path"])):
        kinds = {
            kind for kind, _ in
            v1.same_line_candidate_hits(record, "plus_all_manufacturer_registration")
        }
        if kinds == {"organization_only"}:
            positives.append(str(record["id"]))
    if len(positives) != 39:
        raise ValueError("frozen v1 population candidate set differs from S019/S020")
    known = sorted(known_all & set(positives))
    if len(known) != policy["known_review_count"]:
        raise ValueError("known v1 organization-only review count differs")
    blind = sorted(
        set(positives) - set(known),
        key=lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest(),
    )[:policy["blind_count"]]
    ids = [*dev_ids, *known, *blind]
    if len(ids) != policy["max_notices"] or len(set(ids)) != len(ids):
        raise ValueError("fixed panel IDs invalid")
    records = {}
    provenance = {}
    for path in (config.input_path, root / policy["unlabeled_input_path"]):
        for record in load_notice_records(path):
            if record.notice_id in ids:
                if record.notice_id in records:
                    raise ValueError(f"duplicate panel ID: {record.notice_id}")
                records[record.notice_id] = record
                provenance[record.notice_id] = str(path)
    if set(records) != set(ids):
        raise ValueError("panel source coverage differs")
    return ids, records, provenance


def prepare(config: CleanExperimentConfig) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if compare_manifests(config.path, config.path.parents[2])["status"] != "PASS":
        raise ValueError("undeclared manifest change")
    ids, records, provenance = _panel(config)
    counter = GemmaTokenCounter(config.tokenizer_dir)
    tasks = []
    ledger = []
    for notice_id in ids:
        record = records[notice_id]
        passes, source = build_role_tasks(
            record, counter, config.prompt_budget, task_factory=_task,
        )
        _validate_coverage(record, source)
        for task, row in zip(passes, source, strict=True):
            tasks.append(task)
            ledger.append({
                "id": notice_id, "cohort": (
                    "dev_positive" if notice_id in ids[:4]
                    else "known_unlabeled" if notice_id in ids[4:8]
                    else "blind_unlabeled"
                ),
                "source_path": provenance[notice_id],
                "source_sha256": _sha256(Path(provenance[notice_id])),
                "task_sha256": counter.task_sha256(task), **row,
            })
    return tasks, ledger


def run(config: CleanExperimentConfig, *, mock: bool, api_key: str = "") -> dict[str, Any]:
    tasks, ledger = prepare(config)
    output = config.output_dir
    output.mkdir(parents=True, exist_ok=True)
    atomic_json(output / "manifest.snapshot.json", config.raw)
    atomic_json(output / "source_ledger.json", ledger)
    for task in tasks:
        atomic_json(output / "rendered" / f"{task['id']}__p{task['part']:02d}.json", task)
    if mock:
        for task in tasks:
            parse_response({
                "content": '{"role":"UNCLEAR","quote":""}',
                "finish_reason": "stop", "invalid": False,
            }, task)
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
    results = []

    def complete(task: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
        path = output / "responses" / f"{task['id']}__p{task['part']:02d}.json"
        if path.exists():
            response = json.loads(path.read_text(encoding="utf-8"))
            if response.get("task_sha256") != source["task_sha256"]:
                raise ValueError("stored response task hash differs")
        else:
            try:
                response = runtime.complete(task)
            except RuntimeError as error:
                response = {"invalid": True, "error": str(error), "usage": {}, "attempts": 0}
            response["task_sha256"] = source["task_sha256"]
            atomic_json(path, response)
        try:
            parsed = parse_response(response, task)
            return {"id": task["id"], "part": task["part"], "valid": True,
                    **parsed, "usage": response.get("usage", {})}
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
            return {"id": task["id"], "part": task["part"], "valid": False,
                    "error": str(error), "usage": response.get("usage", {})}

    with ThreadPoolExecutor(max_workers=min(config.provider.concurrency, len(tasks))) as pool:
        futures = [pool.submit(complete, task, row) for task, row in zip(tasks, ledger, strict=True)]
        for future in as_completed(futures):
            results.append(future.result())
            if len(results) % 5 == 0 or len(results) == len(tasks):
                atomic_json(output / f"checkpoint_{len(results):02d}.json", {
                    "completed": len(results), "invalid": sum(not row["valid"] for row in results),
                    "elapsed_seconds": time.monotonic() - started,
                })
    by_id: dict[str, list[dict[str, Any]]] = {}
    for row in results:
        by_id.setdefault(row["id"], []).append(row)
    per_notice = {}
    for notice_id, parts in sorted(by_id.items()):
        ordered = sorted(parts, key=lambda row: row["part"])
        roles = [row["role"] for row in ordered if row["valid"]]
        if "EXCLUSIVE_BIDDER_ORGANIZATION" in roles:
            role = "EXCLUSIVE_BIDDER_ORGANIZATION"
        elif len(roles) == len(ordered) and all(value == "NOT_EXCLUSIVE" for value in roles):
            role = "NOT_EXCLUSIVE"
        else:
            role = "UNCLEAR"
        per_notice[notice_id] = {"role": role, "parts": ordered}
    report = {
        "status": "COMPLETE", "mode": "api", "notices": len(by_id), "calls": len(tasks),
        "invalid": sum(not row["valid"] for row in results),
        "elapsed_seconds": time.monotonic() - started,
        "prompt_tokens_admitted": sum(row["tokens"] for row in ledger),
        "usage_prompt_tokens": sum(row.get("usage", {}).get("prompt_tokens", 0) for row in results),
        "usage_completion_tokens": sum(row.get("usage", {}).get("completion_tokens", 0) for row in results),
        "role_counts": dict(Counter(value["role"] for value in per_notice.values())),
        "per_notice": per_notice,
        "final_labels_changed": 0,
    }
    atomic_json(output / "report.json", report)
    return report
