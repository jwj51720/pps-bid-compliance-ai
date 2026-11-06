"""V1-only fast-panel observation diagnostic with no frozen owner dependency."""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import csv
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

from .config import ProviderConfig
from .ingest.jsonl import load_notice_records
from .preflight import compare_manifests
from .runtime.openrouter import OpenRouterRuntime, atomic_json
from .runtime.tokenizer import GemmaTokenCounter
from .views.native_full_prompt import load_card_texts
from .views.v1_qualification import (
    V1QualificationView, build_v1_qualification_task,
    build_v1_qualification_task_v3,
    build_v1_qualification_axis_task,
    build_v1_bidder_relation_task,
    build_v1_qualification_view_v2,
)


@dataclass(frozen=True)
class NativeV1DiagnosticConfig:
    path: Path
    root: Path
    raw: dict[str, Any]
    input_path: Path
    labels_path: Path
    cards_path: Path
    audit_path: Path
    panel_path: Path
    tokenizer_dir: Path
    output_dir: Path
    budget: int
    provider: ProviderConfig


def _resolved(root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else root / path


def load_native_v1_config(path: Path, root: Path) -> NativeV1DiagnosticConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != "clean-native-v1-diagnostic":
        raise ValueError("not a native v1 diagnostic manifest")
    if raw.get("run") != {"mode": "fast20_observation"}:
        raise ValueError("audit-only or unknown native v1 manifest is not runnable")
    if "reference" in raw or "base_output_dir" in raw:
        raise ValueError("native v1 diagnostic cannot load frozen reference")
    prompt = raw.get("prompt")
    if not isinstance(prompt, dict) or prompt.get("view") != (
        "v1-qualification-linked-exact-windows-v2"
    ) or prompt.get("task") not in {
        "native-v1-qualification-observation-v2",
        "native-v1-explicit-state-observation-v3",
        "native-v1-restriction-axis-observation-v4",
        "native-v1-bidder-relation-observation-v5",
    }:
        raise ValueError("native v1 prompt/view selection differs")
    provider = raw["provider"]
    if provider["model"] != "google/gemma-4-26b-a4b-it" or provider["temperature"] != 0:
        raise ValueError("native v1 provider model/generation differs")
    if provider["max_tokens"] != 1536 or raw["runtime"]["prompt_budget"] != 14848:
        raise ValueError("native v1 token budget differs")
    config = NativeV1DiagnosticConfig(
        path=path.resolve(), root=root.resolve(), raw=raw,
        input_path=_resolved(root, raw["data"]["input_path"]),
        labels_path=_resolved(root, raw["data"]["labels_path"]),
        cards_path=_resolved(root, raw["data"]["cards_path"]),
        audit_path=_resolved(root, raw["data"]["source_audit_path"]),
        panel_path=_resolved(root, raw["evaluation"]["fast_panel_path"]),
        tokenizer_dir=_resolved(root, raw["runtime"]["tokenizer_dir"]),
        output_dir=_resolved(root, raw["output_dir"]),
        budget=raw["runtime"]["prompt_budget"],
        provider=ProviderConfig(
            model=provider["model"], embedding_model="", api_url=provider["api_url"],
            embedding_url="", api_key_env=provider["api_key_env"],
            temperature=provider["temperature"], max_tokens=provider["max_tokens"],
            seed=provider["seed"], timeout_seconds=provider["timeout_seconds"],
            request_retries=provider["request_retries"], concurrency=provider["concurrency"],
            min_request_interval_seconds=provider["min_request_interval_seconds"],
            provider_sort=provider["provider_sort"],
            require_parameters=provider["require_parameters"],
        ),
    )
    for input_path in (
        config.input_path, config.labels_path, config.cards_path,
        config.audit_path, config.panel_path, config.tokenizer_dir,
    ):
        if not input_path.exists():
            raise FileNotFoundError(input_path)
    return config


def prepare_native_v1_fast(
    config: NativeV1DiagnosticConfig,
) -> tuple[dict[str, dict[str, Any]], dict[str, V1QualificationView], dict[str, Any]]:
    manifest_diff = compare_manifests(config.path, config.root)
    if manifest_diff["status"] != "PASS":
        raise ValueError("native v1 manifest diff failed")
    audit = json.loads(config.audit_path.read_text(encoding="utf-8"))
    expected_task_version = {
        "native-v1-qualification-observation-v2": "v2",
        "native-v1-explicit-state-observation-v3": "v3",
        "native-v1-restriction-axis-observation-v4": "v4",
        "native-v1-bidder-relation-observation-v5": "v5",
    }[config.raw["prompt"]["task"]]
    if (
        audit.get("view_version") != "v2"
        or audit.get("task_version", "v2") != expected_task_version
        or audit.get("records") != 200
    ):
        raise ValueError("v1 source audit is not the dev200 v2 audit")
    for path, key in (
        (config.input_path, "input_sha256"),
        (config.labels_path, "labels_sha256"),
        (config.cards_path, "cards_sha256"),
    ):
        if hashlib.sha256(path.read_bytes()).hexdigest() != audit[key]:
            raise ValueError(f"source audit input hash differs: {path}")
    panel = json.loads(config.panel_path.read_text(encoding="utf-8"))
    ids = panel["ids"]
    if len(ids) != 20 or len(set(ids)) != 20:
        raise ValueError("fast panel must contain 20 unique IDs")
    records = {record.notice_id: record for record in load_notice_records(config.input_path)}
    if not set(ids) <= set(records):
        raise ValueError("fast panel has unknown notice IDs")
    card = load_card_texts(config.cards_path)["v1"]
    counter = GemmaTokenCounter(config.tokenizer_dir)
    tasks: dict[str, dict[str, Any]] = {}
    views: dict[str, V1QualificationView] = {}
    tokens: dict[str, int] = {}
    for notice_id in ids:
        record = records[notice_id]
        view = build_v1_qualification_view_v2(record)
        task_builder = {
            "v2": build_v1_qualification_task,
            "v3": build_v1_qualification_task_v3,
            "v4": build_v1_qualification_axis_task,
            "v5": build_v1_bidder_relation_task,
        }[expected_task_version]
        task = task_builder(record, card, view)
        count = counter.count(task["messages"])
        if count > config.budget:
            raise ValueError(f"{notice_id}: prompt exceeds exact token budget")
        if counter.task_sha256(task) != audit["task_hashes"].get(notice_id):
            raise ValueError(f"{notice_id}: audited task hash differs")
        tasks[notice_id], views[notice_id], tokens[notice_id] = task, view, count
    attachment_ids = [
        notice_id for notice_id in ids
        if len(views[notice_id].document_coverage) > 1
    ]
    sample_ids = {
        "short_complete": min(tokens, key=tokens.get),
        "attachment_complete": min(attachment_ids, key=tokens.get),
        "largest_complete": max(tokens, key=tokens.get),
    }
    rendered_paths: dict[str, str] = {}
    semantic_checks: dict[str, dict[str, bool]] = {}
    rendered_root = config.output_dir / "fast20" / "rendered_inputs"
    for role, notice_id in sample_ids.items():
        task = tasks[notice_id]
        system = str(task["messages"][0]["content"])
        user = str(task["messages"][1]["content"])
        checks = {
            "applicability_order": (
                "현재 입찰자 자신" in system
                if expected_task_version == "v5" else
                "실제 입찰 참가자격" in system
                if expected_task_version == "v4" else
                "실제 입찰 참가" in system and "가능 여부" in system
            ),
            "positive_condition": "1 조건:" in user,
            "material_zero_condition": "0 조건:" in user,
            "uncertainty_contract": (
                "U는 제공된 참가자격 후보가" in system
                if expected_task_version == "v3" else
                "불명하면 U" in system
                if expected_task_version in {"v4", "v5"} else
                "U로 답한다" in system
            ),
            "state_mapping": (
                "Y는 카드의 1 조건" in system and "N은 카드의 0 조건" in system
                if expected_task_version == "v3" else
                "target=Y는 실제 참가자격" in system
                if expected_task_version == "v5" else
                "target=Y는 실제 입찰 참가자격" in system
                if expected_task_version == "v4" else True
            ),
            "quote_mapping": (
                "N 또는 U일 때 quote는 반드시 null" in system
                if expected_task_version == "v3" else
                "target=N/U이면 quote는 null" in system
                if expected_task_version in {"v4", "v5"} else True
            ),
            "source_provenance": "탐색범주=" in user and " | 공고문/" in user,
            "no_metadata_dump": "[주최측 전자조달 입력 사실]" not in user,
        }
        semantic_checks[role] = checks
        if not all(checks.values()):
            failed = [name for name, passed in checks.items() if not passed]
            raise ValueError(f"{role}: rendered semantic contract differs: {failed}")
        path = rendered_root / f"{role}_{notice_id}.json"
        atomic_json(path, {
            "role": role, "id": notice_id, "tokens": tokens[notice_id],
            "budget": config.budget, "task": task,
            "document_coverage": list(views[notice_id].document_coverage),
            "semantic_checks": checks,
        })
        rendered_paths[role] = str(path)
    report = {
        "status": "PASS",
        "experiment_id": config.raw["experiment_id"],
        "cohort": "fast20",
        "records": len(tasks),
        "documents_inspected": sum(len(view.document_coverage) for view in views.values()),
        "candidate_spans": sum(len(view.candidates) for view in views.values()),
        "logical_calls": len(tasks),
        "token_min": min(tokens.values()),
        "token_max": max(tokens.values()),
        "token_sum": sum(tokens.values()),
        "token_by_notice": tokens,
        "task_hashes_match": len(tasks),
        "rendered_paths": rendered_paths,
        "semantic_checks": semantic_checks,
        "overflow_tasks": 0,
        "manifest_diff": manifest_diff,
    }
    return tasks, views, report


def parse_v1_response(response: dict[str, Any], view: V1QualificationView) -> dict[str, Any]:
    if response.get("finish_reason") != "stop" or response.get("invalid"):
        return {"state": "U", "quote": None, "valid": False, "reason": "transport_or_length"}
    try:
        value = json.loads(response["content"])
    except (KeyError, TypeError, ValueError):
        return {"state": "U", "quote": None, "valid": False, "reason": "json_parse"}
    if not isinstance(value, dict) or set(value) != {"state", "quote"}:
        return {"state": "U", "quote": None, "valid": False, "reason": "schema_shape"}
    state, quote = value["state"], value["quote"]
    if state not in {"Y", "N", "U"}:
        return {"state": "U", "quote": None, "valid": False, "reason": "invalid_state"}
    if state == "Y":
        if not isinstance(quote, str) or not 1 <= len(quote) <= 500:
            return {"state": "U", "quote": None, "valid": False, "reason": "missing_quote"}
        matched = [candidate.source_id for candidate in view.candidates
                   if quote in candidate.span.exact_text]
        if not matched:
            return {"state": "U", "quote": None, "valid": False, "reason": "quote_not_in_source"}
        return {"state": state, "quote": quote, "valid": True, "source_ids": matched}
    if quote not in (None, ""):
        return {"state": "U", "quote": None, "valid": False, "reason": "quote_for_nonpositive"}
    return {"state": state, "quote": None, "valid": True, "source_ids": []}


def parse_v1_axis_response(
    response: dict[str, Any], view: V1QualificationView,
) -> dict[str, Any]:
    if response.get("finish_reason") != "stop" or response.get("invalid"):
        return {"state": "U", "quote": None, "valid": False,
                "reason": "transport_or_length", "axes": None}
    try:
        value = json.loads(response["content"])
    except (KeyError, TypeError, ValueError):
        return {"state": "U", "quote": None, "valid": False,
                "reason": "json_parse", "axes": None}
    if not isinstance(value, dict) or set(value) != {"target", "allowed", "quote"}:
        return {"state": "U", "quote": None, "valid": False,
                "reason": "schema_shape", "axes": None}
    target, allowed, quote = value["target"], value["allowed"], value["quote"]
    if target not in {"Y", "N", "U"} or allowed not in {"Y", "N", "U"}:
        return {"state": "U", "quote": None, "valid": False,
                "reason": "invalid_axis", "axes": None}
    axes = {"target": target, "allowed": allowed}
    if target == "Y":
        if not isinstance(quote, str) or not 1 <= len(quote) <= 500:
            return {"state": "U", "quote": None, "valid": False,
                    "reason": "missing_quote", "axes": axes}
        matched = [candidate.source_id for candidate in view.candidates
                   if quote in candidate.span.exact_text]
        if not matched:
            return {"state": "U", "quote": None, "valid": False,
                    "reason": "quote_not_in_source", "axes": axes}
        state = "Y" if allowed == "N" else "N" if allowed == "Y" else "U"
        return {"state": state, "quote": quote, "valid": True,
                "source_ids": matched, "axes": axes}
    if quote not in (None, ""):
        return {"state": "U", "quote": None, "valid": False,
                "reason": "quote_for_nontarget", "axes": axes}
    if target == "N" and allowed != "U":
        return {"state": "U", "quote": None, "valid": False,
                "reason": "allowed_must_be_unknown", "axes": axes}
    return {"state": "N" if target == "N" else "U", "quote": None,
            "valid": True, "source_ids": [], "axes": axes}


def run_native_v1_fast(config: NativeV1DiagnosticConfig, *, mock: bool) -> dict[str, Any]:
    started = time.monotonic()
    tasks, views, preflight = prepare_native_v1_fast(config)
    output = config.output_dir / ("fast20-mock" if mock else "fast20")
    atomic_json(output / "preflight.json", preflight)
    response_dir = output / "responses"
    responses: dict[str, dict[str, Any]] = {}
    pending: list[str] = []
    axis_mode = config.raw["prompt"]["task"] in {
        "native-v1-restriction-axis-observation-v4",
        "native-v1-bidder-relation-observation-v5",
    }
    for notice_id in tasks:
        path = response_dir / f"{notice_id}.json"
        if path.is_file():
            responses[notice_id] = json.loads(path.read_text(encoding="utf-8"))
        else:
            pending.append(notice_id)
    if mock:
        for notice_id in pending:
            response = {
                "content": (
                    '{"target":"U","allowed":"U","quote":null}'
                    if axis_mode else '{"state":"U","quote":null}'
                ),
                "finish_reason": "stop", "invalid": False,
                "model": "mock", "usage": {}, "latency_seconds": 0.0,
            }
            atomic_json(response_dir / f"{notice_id}.json", response)
            responses[notice_id] = response
    elif pending:
        runtime = OpenRouterRuntime(config.provider, os.environ.get(config.provider.api_key_env, ""))
        with ThreadPoolExecutor(max_workers=config.provider.concurrency) as executor:
            futures = {executor.submit(runtime.complete, tasks[notice_id]): notice_id
                       for notice_id in pending}
            for future in as_completed(futures):
                notice_id = futures[future]
                response = future.result()
                atomic_json(response_dir / f"{notice_id}.json", response)
                responses[notice_id] = response
    parser = parse_v1_axis_response if axis_mode else parse_v1_response
    observations = {
        notice_id: parser(responses[notice_id], views[notice_id])
        for notice_id in tasks
    }
    atomic_json(output / "observations.json", observations)
    with config.labels_path.open(encoding="utf-8", newline="") as handle:
        gold = {row["id"]: int(row["v1"]) for row in csv.DictReader(handle)}
    counts: Counter[str] = Counter()
    per_notice = []
    for notice_id, result in observations.items():
        state = result["state"]
        actual = gold[notice_id]
        counts["unknown"] += int(state == "U")
        counts["unknown_positive"] += int(state == "U" and actual == 1)
        counts["unknown_negative"] += int(state == "U" and actual == 0)
        counts["invalid"] += int(not result["valid"])
        counts["tp"] += int(state == "Y" and actual == 1)
        counts["fp"] += int(state == "Y" and actual == 0)
        counts["fn_if_unknown_zero"] += int(state != "Y" and actual == 1)
        per_notice.append({
            "id": notice_id, "gold": actual, "state": state,
            "valid": result["valid"], "reason": result.get("reason"),
            "source_ids": result.get("source_ids", []),
            "axes": result.get("axes"),
        })
    tp, fp, fn = (counts[key] for key in ("tp", "fp", "fn_if_unknown_zero"))
    denominator = 2 * tp + fp + fn
    usage = {
        "prompt_tokens_sum": sum(int((response.get("usage") or {}).get("prompt_tokens") or 0)
                                 for response in responses.values()),
        "completion_tokens_sum": sum(int((response.get("usage") or {}).get("completion_tokens") or 0)
                                     for response in responses.values()),
    }
    report = {
        "status": "MOCK" if mock else "DIAGNOSTIC",
        "experiment_id": config.raw["experiment_id"],
        "cohort": "fast20",
        "records": len(tasks),
        "logical_calls": len(tasks),
        "new_calls": len(pending),
        "counts": dict(counts),
        "f1_if_unknown_zero_diagnostic": 2 * tp / denominator if denominator else 0.0,
        "full_v1_score_valid": counts["unknown"] == 0 and counts["invalid"] == 0,
        "usage": usage,
        "seconds": round(time.monotonic() - started, 3),
        "per_notice": per_notice,
        "preflight_path": str(output / "preflight.json"),
    }
    atomic_json(output / "run_report.json", report)
    return report
