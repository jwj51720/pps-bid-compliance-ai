"""V2-only clean panel diagnostic; no legacy or reference response dependency."""

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
from .decisions.v2_performance import AXES, ROLES, decide_v2_performance
from .ingest.jsonl import load_notice_records
from .preflight import compare_manifests
from .runtime.openrouter import OpenRouterRuntime, atomic_json
from .runtime.tokenizer import GemmaTokenCounter
from .views.native_full_prompt import load_card_texts
from .views.v2_performance import (
    V2PerformanceView, build_v2_performance_task,
    build_v2_performance_task_v2,
    build_v2_performance_view_v2,
)


@dataclass(frozen=True)
class NativeV2Config:
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


def load_native_v2_config(path: Path, root: Path) -> NativeV2Config:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != "clean-native-v2-diagnostic":
        raise ValueError("not a native v2 diagnostic manifest")
    if raw.get("run") != {"mode": "panel_observation"}:
        raise ValueError("unknown native v2 run mode")
    if "reference" in raw or "base_output_dir" in raw:
        raise ValueError("native v2 cannot load reference responses")
    if raw.get("prompt") not in ({
        "view": "v2-performance-bounded-windows-v2",
        "task": "native-v2-performance-observation-v1",
    }, {
        "view": "v2-performance-bounded-windows-v2",
        "task": "native-v2-performance-observation-v2",
    }):
        raise ValueError("native v2 prompt selection differs")
    if raw.get("decision") != {
        "owner": "v2-performance-binary-conjunction-v1",
        "positive_if": (
            "performance_participation=Y AND procurement_role in goods/service "
            "AND explicit_allowance=N AND estimated_price<applicable_threshold "
            "AND valid_quote"
        ),
        "otherwise": 0,
    }:
        raise ValueError("native v2 decision policy differs")
    evaluation = raw.get("evaluation", {})
    panels = {
        "fast20": "configs/dev_fast_panel_v1.json",
        "holdout20": "configs/dev_prompt_holdout_v1.json",
    }
    cohort = evaluation.get("cohort")
    if cohort == "dev200":
        if evaluation.get("panel_path") is not None:
            raise ValueError("dev200 cannot select a panel")
    elif cohort not in panels or evaluation.get("panel_path") != panels[cohort]:
        raise ValueError("native v2 requires a fixed versioned 20-notice panel")
    provider = raw["provider"]
    if provider["model"] != "google/gemma-4-26b-a4b-it" or provider["temperature"] != 0:
        raise ValueError("native v2 model/generation differs")
    if provider["max_tokens"] != 1024 or raw["runtime"]["prompt_budget"] != 14848:
        raise ValueError("native v2 token policy differs")
    config = NativeV2Config(
        path=path.resolve(), root=root.resolve(), raw=raw,
        input_path=_resolved(root, raw["data"]["input_path"]),
        labels_path=_resolved(root, raw["data"]["labels_path"]),
        cards_path=_resolved(root, raw["data"]["cards_path"]),
        audit_path=_resolved(root, raw["data"]["source_audit_path"]),
        panel_path=(
            _resolved(root, evaluation["panel_path"])
            if evaluation["panel_path"] is not None else None
        ),
        tokenizer_dir=_resolved(root, raw["runtime"]["tokenizer_dir"]),
        output_dir=_resolved(root, raw["output_dir"]),
        cohort=cohort,
        budget=raw["runtime"]["prompt_budget"],
        provider=ProviderConfig(
            model=provider["model"], embedding_model="", api_url=provider["api_url"],
            embedding_url="", api_key_env=provider["api_key_env"],
            temperature=provider["temperature"], max_tokens=provider["max_tokens"],
            seed=provider["seed"], timeout_seconds=provider["timeout_seconds"],
            request_retries=provider["request_retries"],
            concurrency=provider["concurrency"],
            min_request_interval_seconds=provider["min_request_interval_seconds"],
            provider_sort=provider["provider_sort"],
            require_parameters=provider["require_parameters"],
        ),
    )
    for required in (
        config.input_path, config.labels_path, config.cards_path,
        config.audit_path, config.tokenizer_dir,
    ):
        if not required.exists():
            raise FileNotFoundError(required)
    if config.panel_path is not None and not config.panel_path.exists():
        raise FileNotFoundError(config.panel_path)
    return config


def prepare_native_v2_panel(
    config: NativeV2Config,
) -> tuple[dict[str, dict[str, Any]], dict[str, V2PerformanceView], dict[str, Any]]:
    manifest_diff = compare_manifests(config.path, config.root)
    if manifest_diff["status"] != "PASS":
        raise ValueError("native v2 manifest diff failed")
    audit = json.loads(config.audit_path.read_text(encoding="utf-8"))
    task_version = (
        "v2" if config.raw["prompt"]["task"] ==
        "native-v2-performance-observation-v2" else "v1"
    )
    if (
        audit.get("kind") != "zero_call_v2_performance_actual_task_audit"
        or audit.get("actual_task") is not True
        or audit.get("view_version") != "v2"
        or audit.get("task_version", "v1") != task_version
        or audit.get("records") != 200
    ):
        raise ValueError("native v2 exact task audit differs")
    for source, key in (
        (config.input_path, "input_sha256"),
        (config.labels_path, "labels_sha256"),
        (config.cards_path, "cards_sha256"),
    ):
        if hashlib.sha256(source.read_bytes()).hexdigest() != audit[key]:
            raise ValueError(f"v2 audit source hash differs: {source}")
    records = {record.notice_id: record for record in load_notice_records(config.input_path)}
    if len(records) != 200:
        raise ValueError("dev200 input must contain exactly 200 unique IDs")
    if config.cohort == "dev200":
        ids = list(records)
    else:
        if config.panel_path is None:
            raise ValueError("panel path missing")
        panel = json.loads(config.panel_path.read_text(encoding="utf-8"))
        ids = panel["ids"]
        if len(ids) != 20 or len(set(ids)) != 20 or not set(ids) <= set(records):
            raise ValueError("panel IDs or dev200 input differ")
    card = load_card_texts(config.cards_path)["v2"]
    counter = GemmaTokenCounter(config.tokenizer_dir)
    tasks: dict[str, dict[str, Any]] = {}
    views: dict[str, V2PerformanceView] = {}
    tokens: dict[str, int] = {}
    for notice_id in ids:
        record = records[notice_id]
        view = build_v2_performance_view_v2(record)
        builder = (
            build_v2_performance_task_v2 if task_version == "v2"
            else build_v2_performance_task
        )
        task = builder(record, card, view)
        count = counter.count(task["messages"])
        if count > config.budget:
            raise ValueError(f"{notice_id}: exact task exceeds budget")
        if counter.task_sha256(task) != audit["task_hashes"].get(notice_id):
            raise ValueError(f"{notice_id}: audited task hash differs")
        if len(view.document_coverage) != len(record.documents):
            raise ValueError(f"{notice_id}: document coverage differs")
        tasks[notice_id], views[notice_id], tokens[notice_id] = task, view, count
    attachment_ids = [notice_id for notice_id in ids
                      if len(views[notice_id].document_coverage) > 1]
    samples = {
        "short_complete": min(tokens, key=tokens.get),
        "largest_complete": max(tokens, key=tokens.get),
    }
    if attachment_ids:
        samples["attachment_complete"] = min(attachment_ids, key=tokens.get)
    rendered_paths = {}
    for role, notice_id in samples.items():
        path = config.output_dir / f"{config.cohort}-preflight" / "rendered_inputs" / (
            f"{role}_{notice_id}.json"
        )
        atomic_json(path, {
            "role": role, "id": notice_id, "tokens": tokens[notice_id],
            "task": tasks[notice_id],
            "document_coverage": list(views[notice_id].document_coverage),
        })
        rendered_paths[role] = str(path)
    report = {
        "status": "PASS", "experiment_id": config.raw["experiment_id"],
        "cohort": config.cohort,
        "records": len(tasks), "logical_calls": len(tasks),
        "documents_inspected": sum(len(view.document_coverage) for view in views.values()),
        "candidate_spans": sum(len(view.candidates) for view in views.values()),
        "token_min": min(tokens.values()), "token_max": max(tokens.values()),
        "task_hashes_match": len(tasks), "rendered_paths": rendered_paths,
        "manifest_diff": manifest_diff,
    }
    return tasks, views, report


def parse_v2_response(
    response: dict[str, Any], view: V2PerformanceView,
) -> dict[str, Any]:
    invalid = {"valid": False, "reason": "transport_or_length", "axes": None,
               "quote": None, "source_ids": []}
    if response.get("finish_reason") != "stop" or response.get("invalid"):
        return invalid
    try:
        value = json.loads(response["content"])
    except (KeyError, TypeError, ValueError):
        return {**invalid, "reason": "json_parse"}
    if not isinstance(value, dict) or set(value) != {*AXES, "quote"}:
        return {**invalid, "reason": "schema_shape"}
    axes = {key: value[key] for key in AXES}
    if any(not isinstance(axis, str) for axis in axes.values()) or (
        axes["performance_participation"] not in {"Y", "N", "U"}
        or axes["procurement_role"] not in ROLES
        or axes["explicit_allowance"] not in {"Y", "N", "U"}
        or axes["enterprise_rule_applies"] not in {"Y", "N", "U"}
    ):
        return {**invalid, "reason": "invalid_axis", "axes": axes}
    quote = value["quote"]
    source_ids: list[str] = []
    if axes["performance_participation"] == "Y":
        if not isinstance(quote, str) or not 1 <= len(quote) <= 500:
            return {**invalid, "reason": "missing_quote", "axes": axes}
        source_ids = [candidate.source_id for candidate in view.candidates
                      if quote in candidate.span.exact_text]
        if not source_ids:
            return {**invalid, "reason": "quote_not_in_source", "axes": axes}
    elif quote not in (None, ""):
        return {**invalid, "reason": "quote_for_nonpositive_axis", "axes": axes}
    return {"valid": True, "reason": None, "axes": axes,
            "quote": quote if isinstance(quote, str) else None,
            "source_ids": source_ids}


def run_native_v2_panel(config: NativeV2Config, *, mock: bool) -> dict[str, Any]:
    started = time.monotonic()
    tasks, views, preflight = prepare_native_v2_panel(config)
    output = config.output_dir / (f"{config.cohort}-mock" if mock else config.cohort)
    atomic_json(output / "config.json", config.raw)
    atomic_json(output / "preflight.json", preflight)
    response_dir = output / "responses"
    responses: dict[str, dict[str, Any]] = {}
    pending = []
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
                    '{"performance_participation":"U","procurement_role":"U",'
                    '"explicit_allowance":"U","enterprise_rule_applies":"U",'
                    '"quote":null}'
                ),
                "finish_reason": "stop", "invalid": False,
                "model": "mock", "usage": {}, "latency_seconds": 0.0,
            }
            atomic_json(response_dir / f"{notice_id}.json", response)
            responses[notice_id] = response
    elif pending:
        runtime = OpenRouterRuntime(
            config.provider, os.environ.get(config.provider.api_key_env, "")
        )
        with ThreadPoolExecutor(max_workers=config.provider.concurrency) as executor:
            futures = {executor.submit(runtime.complete, tasks[notice_id]): notice_id
                       for notice_id in pending}
            for future in as_completed(futures):
                notice_id = futures[future]
                response = future.result()
                atomic_json(response_dir / f"{notice_id}.json", response)
                responses[notice_id] = response
    observations = {
        notice_id: parse_v2_response(responses[notice_id], views[notice_id])
        for notice_id in tasks
    }
    atomic_json(output / "observations.json", observations)
    records = {record.notice_id: record for record in load_notice_records(config.input_path)}
    with config.labels_path.open(encoding="utf-8", newline="") as handle:
        gold = {row["id"]: int(row["v2"]) for row in csv.DictReader(handle)}
    counts: Counter[str] = Counter()
    per_notice = []
    for notice_id, observation in observations.items():
        label = 0
        if observation["valid"]:
            label = decide_v2_performance(
                observation["axes"], records[notice_id].metadata,
                valid_quote=bool(observation["source_ids"]),
            )
        actual = gold[notice_id]
        counts["tp"] += int(label == 1 and actual == 1)
        counts["fp"] += int(label == 1 and actual == 0)
        counts["fn"] += int(label == 0 and actual == 1)
        counts["tn"] += int(label == 0 and actual == 0)
        counts["invalid"] += int(not observation["valid"])
        counts["evidence_valid"] += int(label == 1 and bool(observation["source_ids"]))
        per_notice.append({
            "id": notice_id, "gold": actual, "v2": label,
            "e2": observation["quote"] if label == 1 else "",
            "valid": observation["valid"], "reason": observation["reason"],
            "axes": observation["axes"], "source_ids": observation["source_ids"],
        })
    tp, fp, fn = (counts[key] for key in ("tp", "fp", "fn"))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0
    report = {
        "status": "MOCK" if mock else "DIAGNOSTIC",
        "experiment_id": config.raw["experiment_id"], "cohort": config.cohort,
        "records": len(tasks), "logical_calls": len(tasks), "new_calls": len(pending),
        "counts": dict(counts), "precision": precision, "recall": recall, "f1": f1,
        "usage": {
            "prompt_tokens_sum": sum(int((response.get("usage") or {}).get("prompt_tokens") or 0)
                                     for response in responses.values()),
            "completion_tokens_sum": sum(int((response.get("usage") or {}).get("completion_tokens") or 0)
                                         for response in responses.values()),
        },
        "seconds": round(time.monotonic() - started, 3),
        "per_notice": per_notice, "preflight_path": str(output / "preflight.json"),
    }
    atomic_json(output / "run_report.json", report)
    return report
