"""V22-only panel diagnostic with no frozen or reference dependency."""

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
from .decisions.v22_briefing import decide_v22_briefing, decide_v22_phase
from .ingest.jsonl import load_notice_records
from .preflight import compare_manifests
from .runtime.openrouter import OpenRouterRuntime, atomic_json
from .runtime.tokenizer import GemmaTokenCounter
from .views.native_full_prompt import load_card_texts
from .views.v22_briefing import (
    V22BriefingView, build_v22_briefing_task, build_v22_briefing_view,
    build_v22_phase_task,
)


@dataclass(frozen=True)
class NativeV22DiagnosticConfig:
    path: Path
    root: Path
    raw: dict[str, Any]
    input_path: Path
    labels_path: Path
    cards_path: Path
    audit_path: Path
    panel_path: Path | None
    tokenizer_dir: Path
    output_dir: Path
    cohort: str
    budget: int
    provider: ProviderConfig


def _resolved(root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else root / path


def load_native_v22_config(path: Path, root: Path) -> NativeV22DiagnosticConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != "clean-native-v22-diagnostic":
        raise ValueError("not a native v22 diagnostic manifest")
    if raw.get("run") != {"mode": "panel_observation"}:
        raise ValueError("audit-only or unknown native v22 manifest is not runnable")
    if "reference" in raw or "base_output_dir" in raw:
        raise ValueError("native v22 diagnostic cannot load frozen reference")
    prompt = raw.get("prompt")
    if (
        not isinstance(prompt, dict)
        or prompt.get("view") != "v22-briefing-exact-windows-v1"
        or prompt.get("task") not in {
            "native-v22-briefing-observation-v1",
            "native-v22-phase-relation-observation-v2",
        }
    ):
        raise ValueError("native v22 prompt/view selection differs")
    decision = raw.get("decision")
    allowed_decisions = ({
        "owner": "v22-briefing-binary-conjunction-v1",
        "positive_if": "negotiated=Y AND briefing=Y AND exclusion=Y",
        "otherwise": 0,
    }, {
        "owner": "v22-phase-binary-conjunction-v2",
        "positive_if": (
            "negotiated=Y AND pre_submission_briefing=Y "
            "AND pre_submission_bar=Y"
        ),
        "otherwise": 0,
    })
    if decision is not None and decision not in allowed_decisions:
        raise ValueError("native v22 decision policy differs")
    cohort = raw.get("evaluation", {}).get("cohort")
    if cohort not in {"fast20", "holdout20", "dev200"}:
        raise ValueError("native v22 cohort differs")
    panel_value = raw["evaluation"].get("panel_path")
    if cohort == "dev200" and panel_value is not None:
        raise ValueError("dev200 must use the complete input, not a panel")
    if cohort != "dev200" and not isinstance(panel_value, str):
        raise ValueError("panel cohort requires a panel path")
    provider = raw["provider"]
    if provider["model"] != "google/gemma-4-26b-a4b-it" or provider["temperature"] != 0:
        raise ValueError("native v22 provider model/generation differs")
    if provider["max_tokens"] != 1024 or raw["runtime"]["prompt_budget"] != 14848:
        raise ValueError("native v22 token budget differs")
    config = NativeV22DiagnosticConfig(
        path=path.resolve(), root=root.resolve(), raw=raw,
        input_path=_resolved(root, raw["data"]["input_path"]),
        labels_path=_resolved(root, raw["data"]["labels_path"]),
        cards_path=_resolved(root, raw["data"]["cards_path"]),
        audit_path=_resolved(root, raw["data"]["source_audit_path"]),
        panel_path=_resolved(root, panel_value) if panel_value is not None else None,
        tokenizer_dir=_resolved(root, raw["runtime"]["tokenizer_dir"]),
        output_dir=_resolved(root, raw["output_dir"]),
        cohort=cohort, budget=raw["runtime"]["prompt_budget"],
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
        config.audit_path, config.tokenizer_dir,
    ):
        if not input_path.exists():
            raise FileNotFoundError(input_path)
    if config.panel_path is not None and not config.panel_path.exists():
        raise FileNotFoundError(config.panel_path)
    return config


def prepare_native_v22_panel(
    config: NativeV22DiagnosticConfig,
) -> tuple[dict[str, dict[str, Any]], dict[str, V22BriefingView], dict[str, Any]]:
    manifest_diff = compare_manifests(config.path, config.root)
    if manifest_diff["status"] != "PASS":
        raise ValueError("native v22 manifest diff failed")
    audit = json.loads(config.audit_path.read_text(encoding="utf-8"))
    expected_task_version = (
        "v2" if config.raw["prompt"]["task"] ==
        "native-v22-phase-relation-observation-v2" else "v1"
    )
    if (
        audit.get("view_version") != "v1"
        or audit.get("task_version") != expected_task_version
        or audit.get("records") != 200
    ):
        raise ValueError("v22 source audit is not the dev200 v1 audit")
    for file_path, key in (
        (config.input_path, "input_sha256"),
        (config.labels_path, "labels_sha256"),
        (config.cards_path, "cards_sha256"),
    ):
        if hashlib.sha256(file_path.read_bytes()).hexdigest() != audit[key]:
            raise ValueError(f"source audit input hash differs: {file_path}")
    records = {record.notice_id: record for record in load_notice_records(config.input_path)}
    if config.cohort == "dev200":
        ids = list(records)
        if len(ids) != 200:
            raise ValueError("dev200 requires exactly 200 input records")
    else:
        if config.panel_path is None:
            raise ValueError("panel path missing")
        panel = json.loads(config.panel_path.read_text(encoding="utf-8"))
        ids = panel["ids"]
        if len(ids) != 20 or len(set(ids)) != 20:
            raise ValueError("panel must contain 20 unique IDs")
    if not set(ids) <= set(records):
        raise ValueError("panel has unknown notice IDs")
    card = load_card_texts(config.cards_path)["v22"]
    counter = GemmaTokenCounter(config.tokenizer_dir)
    tasks: dict[str, dict[str, Any]] = {}
    views: dict[str, V22BriefingView] = {}
    tokens: dict[str, int] = {}
    for notice_id in ids:
        record = records[notice_id]
        view = build_v22_briefing_view(record)
        task_builder = (
            build_v22_phase_task if expected_task_version == "v2"
            else build_v22_briefing_task
        )
        task = task_builder(record, card, view)
        count = counter.count(task["messages"])
        if count > config.budget:
            raise ValueError(f"{notice_id}: prompt exceeds exact token budget")
        if counter.task_sha256(task) != audit["task_hashes"].get(notice_id):
            raise ValueError(f"{notice_id}: audited task hash differs")
        tasks[notice_id], views[notice_id], tokens[notice_id] = task, view, count

    attachment_ids = [notice_id for notice_id in ids
                      if len(views[notice_id].document_coverage) > 1]
    sample_ids = {
        "short_complete": min(tokens, key=tokens.get),
        "attachment_complete": min(attachment_ids, key=tokens.get),
        "largest_complete": max(tokens, key=tokens.get),
    }
    rendered_paths: dict[str, str] = {}
    semantic_checks: dict[str, dict[str, bool]] = {}
    rendered_root = config.output_dir / config.cohort / "rendered_inputs"
    for role, notice_id in sample_ids.items():
        task = tasks[notice_id]
        system = str(task["messages"][0]["content"])
        user = str(task["messages"][1]["content"])
        metadata_section = user.split(
            "[v22에 필요한 주최측 입력 사실]\n", 1,
        )[1].split("\n\n[모든 제공 문서의 source-grounded 후보]", 1)[0]
        axis_terms = (
            ("negotiated", "pre_submission_briefing", "pre_submission_bar",
             "proposal_evaluation_session")
            if expected_task_version == "v2"
            else ("negotiated", "briefing", "exclusion")
        )
        checks = {
            "required_axes": all(term in system for term in axis_terms),
            "positive_condition": "1 조건:" in user,
            "material_zero_condition": "0 조건:" in user,
            "metadata_contract": "낙찰방식 입력:" in user,
            "presentation_exclusion": (
                "proposal_evaluation_session" in system
                if expected_task_version == "v2"
                else "제안서 발표·평가" in system
            ),
            "uncertainty_contract": "불명하면 U" in system,
            "quote_contract": "변경 없는 연속 1~500자" in system,
            "source_provenance": "탐색범주=" in user and " | 공고문/" in user,
            "no_raw_metadata": (
                '"낙찰방법"' not in metadata_section
                and "{" not in metadata_section
                and "}" not in metadata_section
            ),
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
        "status": "PASS", "experiment_id": config.raw["experiment_id"],
        "cohort": config.cohort, "records": len(tasks),
        "documents_inspected": sum(len(view.document_coverage) for view in views.values()),
        "candidate_spans": sum(len(view.candidates) for view in views.values()),
        "logical_calls": len(tasks), "token_min": min(tokens.values()),
        "token_max": max(tokens.values()), "token_sum": sum(tokens.values()),
        "token_by_notice": tokens, "task_hashes_match": len(tasks),
        "rendered_paths": rendered_paths, "semantic_checks": semantic_checks,
        "overflow_tasks": 0, "manifest_diff": manifest_diff,
    }
    return tasks, views, report


def parse_v22_response(
    response: dict[str, Any], view: V22BriefingView,
) -> dict[str, Any]:
    invalid = {
        "state": "U", "quote": None, "valid": False,
        "reason": "transport_or_length", "axes": None,
    }
    if response.get("finish_reason") != "stop" or response.get("invalid"):
        return invalid
    try:
        value = json.loads(response["content"])
    except (KeyError, TypeError, ValueError):
        return {**invalid, "reason": "json_parse"}
    keys = {"negotiated", "briefing", "exclusion", "quote"}
    if not isinstance(value, dict) or set(value) != keys:
        return {**invalid, "reason": "schema_shape"}
    axes = {key: value[key] for key in ("negotiated", "briefing", "exclusion")}
    if any(axis not in {"Y", "N", "U"} for axis in axes.values()):
        return {**invalid, "reason": "invalid_axis", "axes": axes}
    quote = value["quote"]
    source_ids: list[str] = []
    if axes["exclusion"] == "Y":
        if not isinstance(quote, str) or not 1 <= len(quote) <= 500:
            return {**invalid, "reason": "missing_quote", "axes": axes}
        source_ids = [candidate.source_id for candidate in view.candidates
                      if quote in candidate.span.exact_text]
        if not source_ids:
            return {**invalid, "reason": "quote_not_in_source", "axes": axes}
    elif quote not in (None, ""):
        return {**invalid, "reason": "quote_for_nonexclusion", "axes": axes}
    if all(axis == "Y" for axis in axes.values()):
        state = "Y"
    elif any(axis == "N" for axis in axes.values()):
        state = "N"
    else:
        state = "U"
    return {
        "state": state, "quote": quote if state == "Y" else None,
        "valid": True, "source_ids": source_ids, "axes": axes,
    }


def parse_v22_phase_response(
    response: dict[str, Any], view: V22BriefingView,
) -> dict[str, Any]:
    invalid = {
        "state": "U", "quote": None, "valid": False,
        "reason": "transport_or_length", "axes": None,
    }
    if response.get("finish_reason") != "stop" or response.get("invalid"):
        return invalid
    try:
        value = json.loads(response["content"])
    except (KeyError, TypeError, ValueError):
        return {**invalid, "reason": "json_parse"}
    axis_names = (
        "negotiated", "pre_submission_briefing", "pre_submission_bar",
        "proposal_evaluation_session",
    )
    if not isinstance(value, dict) or set(value) != {*axis_names, "quote"}:
        return {**invalid, "reason": "schema_shape"}
    axes = {key: value[key] for key in axis_names}
    if any(axis not in {"Y", "N", "U"} for axis in axes.values()):
        return {**invalid, "reason": "invalid_axis", "axes": axes}
    quote = value["quote"]
    source_ids: list[str] = []
    if axes["pre_submission_bar"] == "Y":
        if not isinstance(quote, str) or not 1 <= len(quote) <= 500:
            return {**invalid, "reason": "missing_quote", "axes": axes}
        source_ids = [candidate.source_id for candidate in view.candidates
                      if quote in candidate.span.exact_text]
        if not source_ids:
            return {**invalid, "reason": "quote_not_in_source", "axes": axes}
    elif quote not in (None, ""):
        return {**invalid, "reason": "quote_for_nonbar", "axes": axes}
    required = (
        axes["negotiated"], axes["pre_submission_briefing"],
        axes["pre_submission_bar"],
    )
    if all(axis == "Y" for axis in required):
        state = "Y"
    elif any(axis == "N" for axis in required):
        state = "N"
    else:
        state = "U"
    return {
        "state": state, "quote": quote if state == "Y" else None,
        "valid": True, "source_ids": source_ids, "axes": axes,
    }


def run_native_v22_panel(
    config: NativeV22DiagnosticConfig, *, mock: bool,
) -> dict[str, Any]:
    started = time.monotonic()
    tasks, views, preflight = prepare_native_v22_panel(config)
    output = config.output_dir / (f"{config.cohort}-mock" if mock else config.cohort)
    atomic_json(output / "preflight.json", preflight)
    response_dir = output / "responses"
    responses: dict[str, dict[str, Any]] = {}
    pending: list[str] = []
    for notice_id in tasks:
        path = response_dir / f"{notice_id}.json"
        if path.is_file():
            responses[notice_id] = json.loads(path.read_text(encoding="utf-8"))
        else:
            pending.append(notice_id)
    phase_mode = config.raw["prompt"]["task"] == (
        "native-v22-phase-relation-observation-v2"
    )
    if mock:
        for notice_id in pending:
            response = {
                "content": (
                    '{"negotiated":"U","pre_submission_briefing":"U",'
                    '"pre_submission_bar":"U",'
                    '"proposal_evaluation_session":"U","quote":null}'
                    if phase_mode else
                    '{"negotiated":"U","briefing":"U",'
                    '"exclusion":"U","quote":null}'
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
    response_parser = parse_v22_phase_response if phase_mode else parse_v22_response
    observations = {
        notice_id: response_parser(responses[notice_id], views[notice_id])
        for notice_id in tasks
    }
    atomic_json(output / "observations.json", observations)
    with config.labels_path.open(encoding="utf-8", newline="") as handle:
        gold = {row["id"]: int(row["v22"]) for row in csv.DictReader(handle)}
    counts: Counter[str] = Counter()
    per_notice = []
    for notice_id, result in observations.items():
        raw_state = result["state"]
        if config.raw.get("decision") is not None and result["valid"]:
            decision = (
                decide_v22_phase(result["axes"])
                if config.raw["decision"]["owner"] ==
                "v22-phase-binary-conjunction-v2"
                else decide_v22_briefing(result["axes"])
            )
            state = "Y" if decision else "N"
        else:
            state = raw_state
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
            "raw_state": raw_state,
            "valid": result["valid"], "reason": result.get("reason"),
            "source_ids": result.get("source_ids", []), "axes": result.get("axes"),
        })
    tp, fp, fn = (counts[key] for key in ("tp", "fp", "fn_if_unknown_zero"))
    denominator = 2 * tp + fp + fn
    report = {
        "status": "MOCK" if mock else "DIAGNOSTIC",
        "experiment_id": config.raw["experiment_id"], "cohort": config.cohort,
        "records": len(tasks), "logical_calls": len(tasks), "new_calls": len(pending),
        "counts": dict(counts),
        "f1_if_unknown_zero_diagnostic": 2 * tp / denominator if denominator else 0.0,
        "full_v22_score_valid": counts["unknown"] == 0 and counts["invalid"] == 0,
        "usage": {
            "prompt_tokens_sum": sum(int((response.get("usage") or {}).get("prompt_tokens") or 0)
                                     for response in responses.values()),
            "completion_tokens_sum": sum(int((response.get("usage") or {}).get("completion_tokens") or 0)
                                         for response in responses.values()),
        },
        "seconds": round(time.monotonic() - started, 3), "per_notice": per_notice,
        "preflight_path": str(output / "preflight.json"),
    }
    atomic_json(output / "run_report.json", report)
    return report
