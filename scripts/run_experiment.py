#!/usr/bin/env python3
"""Run a resumable local experiment and evaluate a submission-shaped result."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import ExperimentConfig, load_config
from src.data import (
    load_competition_product_index,
    load_decision_cards,
    load_item_table,
    load_record_id_panel,
    load_records,
    select_records_by_id,
)
from src.evaluate import evaluate_submission, write_rows
from src.external.openrouter import MockClient, OpenRouterClient
from src.external.openai import OpenAIClient
from src.law_bundles import MetadataLawBundleRouter
from src.pipeline import (
    BaselinePipeline,
    ContextAdmissionError,
    FactInventoryThenFinalPrediction,
    FactInventoryFullFinalPrediction,
    LocatorThenFinalPrediction,
    InventoryThenFinalPrediction,
    Prediction,
    PredictionError,
    TriageThenStrictPrediction,
    TwoPassAdjudicationPrediction,
    VOnlyDraftFullFinalPrediction,
    judgment_to_row,
)
from src.submission import validate_submission, write_submission
from src.schema import FACT_INVENTORY_CATEGORIES, FACT_INVENTORY_CATEGORIES_V2


def _logger(output_dir: Path) -> logging.Logger:
    logger = logging.getLogger("experiment")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    for handler in (logging.StreamHandler(), logging.FileHandler(output_dir / "run.log", encoding="utf-8")):
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _source_hashes() -> dict[str, str]:
    paths = sorted((ROOT / "src").rglob("*.py")) + [Path(__file__).resolve()]
    return {str(path.relative_to(ROOT)): _sha256(path) for path in paths}


def _tree_hashes(path: Path | None) -> dict[str, str] | None:
    if path is None:
        return None
    return {
        str(value.relative_to(ROOT)): _sha256(value)
        for value in sorted(path.rglob("*"))
        if value.is_file()
    }


def _run_signature(
    config: ExperimentConfig,
    mock: bool,
    *,
    limit: int | None,
    selected_ids: list[str] | None,
) -> str:
    identity = {
        "config": config.raw,
        "effective_model": "mock" if mock else config.llm.model,
        "input_sha256": _sha256(config.data.input_path),
        "item_table_sha256": _sha256(config.data.item_table_path),
        "reference_sha256": _sha256(config.reference_path) if config.reference_path else None,
        "reference_bundle_sha256": _tree_hashes(config.reference_bundle_dir),
        "source_sha256": _source_hashes(),
        "selection": {"limit": limit, "ids": selected_ids},
    }
    encoded = json.dumps(identity, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _git_commit() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _usage_number(value: Any) -> float:
    """Normalize provider usage/cost values before staged-run aggregation."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, dict):
        for key in ("cost", "total_cost", "total"):
            nested = value.get(key)
            if isinstance(nested, (int, float)) and not isinstance(nested, bool):
                return float(nested)
    return 0.0


def _prediction_to_json(
    prediction: Prediction | TwoPassAdjudicationPrediction | VOnlyDraftFullFinalPrediction | TriageThenStrictPrediction | LocatorThenFinalPrediction | InventoryThenFinalPrediction | FactInventoryThenFinalPrediction | FactInventoryFullFinalPrediction,
) -> dict[str, Any]:
    if isinstance(prediction, VOnlyDraftFullFinalPrediction):
        final = prediction.final
        stages = [prediction.draft.usage, final.usage]
        return {
            "id": final.record_id,
            "judgment": final.judgment,
            "row": judgment_to_row(final.record_id, final.judgment),
            "raw_response": final.raw_response,
            "model": final.model,
            "latency_seconds": prediction.draft.latency_seconds + final.latency_seconds,
            "usage": {
                key: sum(_usage_number(stage.get(key, 0)) for stage in stages)
                for key in set().union(*(set(stage) for stage in stages))
            },
            "finish_reason": final.finish_reason,
            "pass_judgments": list(final.pass_judgments),
            "v8_observations": list(final.v8_observations),
            "parse_errors": list(final.parse_errors),
            "staged_run": {
                "mode": "vonly_draft_full_final_v1",
                "vonly_draft": {
                    "raw_response": prediction.draft.raw_response,
                    "judgment": prediction.draft.judgment,
                    "usage": prediction.draft.usage,
                    "latency_seconds": prediction.draft.latency_seconds,
                    "parse_errors": list(prediction.draft.parse_errors),
                    "messages_by_context": [
                        list(messages) for messages in prediction.draft_messages_by_context
                    ],
                    "available_to_final": prediction.draft_available,
                },
                "final": {
                    "messages_by_context": [
                        list(messages) for messages in prediction.final_messages_by_context
                    ],
                    "judgment": final.judgment,
                },
                "final_recovery_used": prediction.final_recovery_used,
            },
        }
    if isinstance(prediction, FactInventoryFullFinalPrediction):
        final = prediction.final
        stages = [*prediction.inventory_usage, *prediction.timeline_usage, final.usage]
        navigation_key = "procedure" if prediction.procedure_navigation else "inventory"
        navigation_payload = {
            "raw_responses": list(prediction.inventory_raw_responses),
            ("by_field" if prediction.procedure_navigation else "by_category"): {
                key: list(value)
                for key, value in prediction.inventory_by_category.items()
            },
            "parse_errors": list(prediction.inventory_parse_errors),
            "messages": [list(value) for value in prediction.inventory_messages],
        }
        return {
            "id": final.record_id, "judgment": final.judgment,
            "row": judgment_to_row(final.record_id, final.judgment),
            "raw_response": final.raw_response, "model": final.model,
            "latency_seconds": (
                sum(prediction.inventory_latency_seconds)
                + sum(prediction.timeline_latency_seconds)
                + final.latency_seconds
            ),
            "usage": {key: sum(_usage_number(stage.get(key, 0)) for stage in stages)
                      for key in set().union(*(set(stage) for stage in stages))},
            "finish_reason": final.finish_reason, "pass_judgments": list(final.pass_judgments),
            "v8_observations": list(final.v8_observations), "parse_errors": list(final.parse_errors),
            "staged_run": {"mode": (
                "procedure_inventory_full_final_v1"
                if prediction.procedure_navigation
                else "fact_inventory_full_final_source_only_v1"
                if prediction.source_only_inventory
                else "fact_inventory_full_final_timeline_v23"
                if prediction.timeline_by_role is not None
                else "fact_inventory_full_final_v4"
                if prediction.inventory_categories == FACT_INVENTORY_CATEGORIES_V2
                else "fact_inventory_full_final_v3"
                if prediction.inventory_position == "before_source"
                else "fact_inventory_full_final_v2"
                if prediction.inventory_max_items == 4
                else "fact_inventory_full_final_v1"
            ),
                navigation_key: navigation_payload,
                "timeline": ({"raw_responses": list(prediction.timeline_raw_responses),
                    "by_role": {k: list(v) for k, v in prediction.timeline_by_role.items()},
                    "parse_errors": list(prediction.timeline_parse_errors),
                    "messages": [list(value) for value in prediction.timeline_messages]}
                    if prediction.timeline_by_role is not None else None),
                "final": {"messages_by_context": [list(value) for value in prediction.final_messages_by_context],
                          "judgment": final.judgment},
                "final_recovery_used": prediction.final_recovery_used},
        }
    if isinstance(prediction, FactInventoryThenFinalPrediction):
        final = prediction.final
        stages = [*prediction.inventory_usage, final.usage]
        return {
            "id": final.record_id, "judgment": final.judgment,
            "row": judgment_to_row(final.record_id, final.judgment),
            "raw_response": final.raw_response, "model": final.model,
            "latency_seconds": sum(prediction.inventory_latency_seconds) + final.latency_seconds,
            "usage": {key: sum(_usage_number(stage.get(key, 0)) for stage in stages)
                      for key in set().union(*(set(stage) for stage in stages))},
            "finish_reason": final.finish_reason, "pass_judgments": list(final.pass_judgments),
            "v8_observations": list(final.v8_observations), "parse_errors": list(final.parse_errors),
            "staged_run": {"mode": "fact_inventory_then_final_v1",
                "inventory": {"raw_responses": list(prediction.inventory_raw_responses),
                    "by_category": {k: list(v) for k, v in prediction.inventory_by_category.items()},
                    "parse_errors": list(prediction.inventory_parse_errors),
                    "messages": [list(value) for value in prediction.inventory_messages]},
                "final": {"messages": list(prediction.final_messages), "judgment": final.judgment},
                "final_recovery_used": prediction.final_recovery_used},
        }
    if isinstance(prediction, InventoryThenFinalPrediction):
        final = prediction.final
        stages = [*prediction.inventory_usage, final.usage]
        return {
            "id": final.record_id, "judgment": final.judgment,
            "row": judgment_to_row(final.record_id, final.judgment),
            "raw_response": final.raw_response, "model": final.model,
            "latency_seconds": sum(prediction.inventory_latency_seconds) + final.latency_seconds,
            "usage": {key: sum(_usage_number(stage.get(key, 0)) for stage in stages)
                      for key in set().union(*(set(stage) for stage in stages))},
            "finish_reason": final.finish_reason, "pass_judgments": list(final.pass_judgments),
            "v8_observations": list(final.v8_observations), "parse_errors": list(final.parse_errors),
            "staged_run": {"mode": "inventory_then_final_v1",
                "inventory": {"raw_responses": list(prediction.inventory_raw_responses),
                    "by_item": {k: list(v) for k, v in prediction.inventory_by_item.items()},
                    "absence_summary": prediction.absence_pack_summary,
                    "parse_errors": list(prediction.inventory_parse_errors),
                    "messages": [list(value) for value in prediction.inventory_messages]},
                "final": {"messages": list(prediction.final_messages), "judgment": final.judgment},
                "final_recovery_used": prediction.final_recovery_used},
        }
    if isinstance(prediction, LocatorThenFinalPrediction):
        final = prediction.final
        stages = [prediction.locator_usage, final.usage]
        latencies = [prediction.locator_latency_seconds, final.latency_seconds]
        if prediction.final_recovery_used:
            stages.append(final.usage)
            latencies.append(final.latency_seconds)
        combined_usage = {
            key: sum(_usage_number(stage.get(key, 0)) for stage in stages)
            for key in set().union(*(set(stage) for stage in stages))
        }
        return {
            "id": final.record_id,
            "judgment": final.judgment,
            "row": judgment_to_row(final.record_id, final.judgment),
            "raw_response": final.raw_response,
            "model": final.model,
            "latency_seconds": sum(latencies),
            "usage": combined_usage,
            "finish_reason": final.finish_reason,
            "pass_judgments": list(final.pass_judgments),
            "v8_observations": list(final.v8_observations),
            "parse_errors": list(final.parse_errors),
            "staged_run": {
                "mode": "locator_then_final_v1",
                "locator": {
                    "raw_response": prediction.locator_raw_response,
                    "snippets": prediction.locator_snippets,
                    "latency_seconds": prediction.locator_latency_seconds,
                    "usage": prediction.locator_usage,
                    "finish_reason": prediction.locator_finish_reason,
                    "parse_error": prediction.locator_parse_error,
                    "messages": list(prediction.locator_messages),
                },
                "final": {
                    "raw_response": final.raw_response,
                    "judgment": final.judgment,
                    "latency_seconds": final.latency_seconds,
                    "usage": final.usage,
                    "parse_errors": list(final.parse_errors),
                    "messages": list(prediction.final_messages),
                },
                "final_recovery_used": prediction.final_recovery_used,
            },
        }
    if isinstance(prediction, TriageThenStrictPrediction):
        final = prediction.final
        stages = [prediction.triage_usage, prediction.strict.usage]
        latencies = [prediction.triage_latency_seconds, prediction.strict.latency_seconds]
        if prediction.strict_recovery_used:
            stages.append(final.usage)
            latencies.append(final.latency_seconds)
        combined_usage = {
            key: sum(_usage_number(stage.get(key, 0)) for stage in stages)
            for key in set().union(*(set(stage) for stage in stages))
        }
        return {
            "id": final.record_id,
            "judgment": final.judgment,
            "row": judgment_to_row(final.record_id, final.judgment),
            "raw_response": final.raw_response,
            "model": final.model,
            "latency_seconds": sum(latencies),
            "usage": combined_usage,
            "finish_reason": final.finish_reason,
            "pass_judgments": list(final.pass_judgments),
            "v8_observations": list(final.v8_observations),
            "parse_errors": list(final.parse_errors),
            "staged_run": {
                "mode": "triage_then_strict_v1",
                "triage": {
                    "raw_response": prediction.triage_raw_response,
                    "states": prediction.triage_states,
                    "latency_seconds": prediction.triage_latency_seconds,
                    "usage": prediction.triage_usage,
                    "finish_reason": prediction.triage_finish_reason,
                    "parse_error": prediction.triage_parse_error,
                    "messages": list(prediction.triage_messages),
                },
                "strict": {
                    "items": list(prediction.strict_items),
                    "raw_response": prediction.strict.raw_response,
                    "judgment": prediction.strict.judgment,
                    "latency_seconds": prediction.strict.latency_seconds,
                    "usage": prediction.strict.usage,
                    "parse_errors": list(prediction.strict.parse_errors),
                    "messages": list(prediction.strict_messages),
                },
                "strict_recovery_used": prediction.strict_recovery_used,
            },
        }
    if isinstance(prediction, TwoPassAdjudicationPrediction):
        final = prediction.final
        combined_usage = {
            key: _usage_number(prediction.pass_a.usage.get(key, 0))
            + _usage_number(prediction.pass_b.usage.get(key, 0))
            for key in set(prediction.pass_a.usage) | set(prediction.pass_b.usage)
        }
        return {
            "id": final.record_id,
            "judgment": final.judgment,
            "row": judgment_to_row(final.record_id, final.judgment),
            "raw_response": final.raw_response,
            "model": final.model,
            "latency_seconds": prediction.pass_a.latency_seconds + prediction.pass_b.latency_seconds,
            "usage": combined_usage,
            "finish_reason": final.finish_reason,
            "pass_judgments": list(final.pass_judgments),
            "v8_observations": list(final.v8_observations),
            "parse_errors": list(final.parse_errors),
            "two_pass": {
                "final_source": prediction.final_source,
                "pass_a": {
                    "raw_response": prediction.pass_a.raw_response,
                    "judgment": prediction.pass_a.judgment,
                    "latency_seconds": prediction.pass_a.latency_seconds,
                    "usage": prediction.pass_a.usage,
                    "parse_errors": list(prediction.pass_a.parse_errors),
                },
                "pass_b": {
                    "raw_response": prediction.pass_b.raw_response,
                    "judgment": prediction.pass_b.judgment,
                    "latency_seconds": prediction.pass_b.latency_seconds,
                    "usage": prediction.pass_b.usage,
                    "parse_errors": list(prediction.pass_b.parse_errors),
                },
            },
        }
    return {
        "id": prediction.record_id,
        "judgment": prediction.judgment,
        "row": judgment_to_row(prediction.record_id, prediction.judgment),
        "raw_response": prediction.raw_response,
        "model": prediction.model,
        "latency_seconds": prediction.latency_seconds,
        "usage": prediction.usage,
        "finish_reason": prediction.finish_reason,
        "pass_judgments": list(prediction.pass_judgments),
        "v8_observations": list(prediction.v8_observations),
        "parse_errors": list(prediction.parse_errors),
        "applicability_inactive_items": dict(prediction.applicability_inactive_items),
    }


def _load_checkpoint(path: Path) -> dict[str, dict[str, Any]]:
    checkpoint: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return checkpoint
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
                checkpoint[value["id"]] = value
            except (json.JSONDecodeError, KeyError) as exc:
                raise ValueError(f"invalid checkpoint line {line_number}: {exc}") from exc
    return checkpoint


def _write_input_examples_markdown(path: Path, entries: list[dict[str, Any]]) -> None:
    """Write inspectable final chat text without JSONL transport wrappers."""
    lines = ["# 모델 입력 예시", "", "아래 fenced block만 모델에 실제로 전달한 메시지 내용입니다.", ""]
    for entry in entries:
        lines.extend(
            [
                f"## {entry['id']} — 문서 조각 {entry['pass_index']}",
                "",
                f"Tokenizer input tokens: {entry['token_count']}",
                "",
                "### System message",
                "",
                "````text",
                entry["messages"][0]["content"],
                "````",
                "",
                "### User message",
                "",
                "````text",
                entry["messages"][1]["content"],
                "````",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_staged_input_examples_markdown(
    path: Path, values: list[dict[str, Any]], limit: int
) -> None:
    """Export actual messages for every supported staged execution mode."""
    lines = [
        "# Staged 모델 입력 예시",
        "",
        "각 fenced block은 해당 stage에서 모델에 실제 전달된 메시지 내용이다.",
        "1차 stage의 결과는 final label이나 evidence가 아니며, 2차 stage만 최종 V/E를 낸다.",
        "",
    ]
    for value in values[:limit]:
        staged = value.get("staged_run", {})
        mode = staged.get("mode")
        inventory_mode = mode in {
            "inventory_then_final_v1",
            "fact_inventory_then_final_v1",
            "fact_inventory_full_final_v1",
            "fact_inventory_full_final_v2",
            "fact_inventory_full_final_v3",
            "fact_inventory_full_final_v4",
            "fact_inventory_full_final_source_only_v1",
        }
        procedure_mode = mode == "procedure_inventory_full_final_v1"
        vonly_draft_mode = mode == "vonly_draft_full_final_v1"
        if inventory_mode or procedure_mode or vonly_draft_mode:
            first_name, first = (
                ("V-only draft", staged.get("vonly_draft", {}))
                if vonly_draft_mode
                else
                ("Procedure relation ledger", staged.get("procedure", {}))
                if procedure_mode
                else ("Fact inventory", staged.get("inventory", {}))
            )
            second_name, second = "Final V/E", staged.get("final", {})
            first_result: Any = (
                first.get("judgment", {}) if vonly_draft_mode else {
                field: len(excerpts)
                for field, excerpts in first.get(
                    "by_field" if procedure_mode else "by_category", {}
                ).items()
                }
            )
            first_messages = first.get(
                "messages_by_context" if vonly_draft_mode else "messages", []
            )
            second_messages = second.get("messages_by_context", second.get("messages", []))
        else:
            first_name, first = (
                ("Triage", staged.get("triage", {}))
                if mode == "triage_then_strict_v1"
                else ("Locator", staged.get("locator", {}))
            )
            second_name, second = (
                ("Strict final", staged.get("strict", {}))
                if mode == "triage_then_strict_v1"
                else ("Final V/E", staged.get("final", {}))
            )
            first_result = first.get("states", first.get("snippets", {}))
            first_messages = first.get("messages", [])
            second_messages = second.get("messages", [])

        def flatten_message_packs(messages: list[Any]) -> list[dict[str, Any]]:
            """Flatten source-pack message lists while preserving their order."""
            flattened: list[dict[str, Any]] = []
            for message_or_pack in messages:
                if isinstance(message_or_pack, list):
                    flattened.extend(
                        message for message in message_or_pack
                        if isinstance(message, dict)
                    )
                elif isinstance(message_or_pack, dict):
                    flattened.append(message_or_pack)
            return flattened

        lines.extend([
            f"## {value['id']}",
            "",
            f"- mode: `{mode}`",
            f"- first-stage result: `{json.dumps(first_result, ensure_ascii=False)}`",
            f"- strict items: `{', '.join(second.get('items', []))}`",
            f"- recovery used: `{staged.get('strict_recovery_used', staged.get('final_recovery_used'))}`",
            "",
        ])
        for title, messages in (
            (first_name, flatten_message_packs(first_messages)),
            (second_name, flatten_message_packs(second_messages)),
        ):
            lines.extend([f"### {title}", ""])
            for message in messages:
                lines.extend([
                    f"#### {message.get('role', 'unknown')}",
                    "",
                    "```text",
                    str(message.get("content", "")),
                    "```",
                    "",
                ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _make_client(config: ExperimentConfig, mock: bool):
    if mock:
        return MockClient()
    api_key = os.environ.get(config.llm.api_key_env, "")
    if not api_key:
        raise RuntimeError(f"missing environment variable: {config.llm.api_key_env}")
    if config.llm.provider == "openai":
        return OpenAIClient(
            api_key=api_key,
            api_url=config.llm.api_url,
            model=config.llm.model,
            max_tokens=config.llm.max_tokens,
            timeout_seconds=config.llm.timeout_seconds,
            request_retries=config.llm.request_retries,
            min_request_interval_seconds=config.llm.min_request_interval_seconds,
            reasoning_effort=config.llm.reasoning_effort,
        )
    return OpenRouterClient(
        api_key=api_key,
        api_url=config.llm.api_url,
        model=config.llm.model,
        temperature=config.llm.temperature,
        max_tokens=config.llm.max_tokens,
        seed=config.llm.seed,
        timeout_seconds=config.llm.timeout_seconds,
        request_retries=config.llm.request_retries,
        provider_sort=config.llm.provider_sort,
        require_parameters=config.llm.require_parameters,
        min_request_interval_seconds=config.llm.min_request_interval_seconds,
    )


def _make_token_counter(config: ExperimentConfig, mock: bool, *, force: bool = False):
    if not force and (
        config.max_document_chars is not None
        or config.context_strategy == "split"
        or (
            config.context_strategy == "single"
            and not config.overflow_split_enabled
        )
    ):
        return None
    from transformers import AutoTokenizer

    tokenizer_source = (
        config.llm.tokenizer_source
        or os.environ.get("PPS_MODEL_DIR")
        or config.llm.model
    )
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_source)

    def count_tokens(messages: list[dict[str, str]]) -> int:
        encoded = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True
        )
        token_ids = encoded["input_ids"] if hasattr(encoded, "keys") else encoded
        return len(token_ids)

    return count_tokens


def _predict_with_retries(
    pipeline: BaselinePipeline,
    record: dict[str, Any],
    attempts: int,
    two_pass_adjudication: bool = False,
    triage_then_strict: bool = False,
    locator_then_final: bool = False,
    inventory_then_final: bool = False,
    fact_inventory_then_final: bool = False,
    fact_inventory_full_final: bool = False,
    fact_inventory_max_items: int = 3,
    fact_inventory_position: str = "after_source",
    fact_inventory_categories: tuple[str, ...] = FACT_INVENTORY_CATEGORIES,
    fact_inventory_timeline_v23: bool = False,
    procedure_inventory_full_final: bool = False,
    source_only_inventory: bool = False,
    vonly_draft_full_final: bool = False,
) -> tuple[Prediction | TwoPassAdjudicationPrediction | VOnlyDraftFullFinalPrediction | TriageThenStrictPrediction | LocatorThenFinalPrediction | InventoryThenFinalPrediction | FactInventoryThenFinalPrediction | None, list[dict[str, Any]]]:
    failed_attempts: list[dict[str, Any]] = []
    for attempt in range(1, attempts + 1):
        try:
            prediction = (
                pipeline.predict_with_untrusted_label_review(record)
                if two_pass_adjudication
                else pipeline.predict_with_triage_then_strict(record)
                if triage_then_strict
                else pipeline.predict_with_locator_then_final(record)
                if locator_then_final
                else pipeline.predict_with_inventory_then_final(record)
                if inventory_then_final
                else pipeline.predict_with_fact_inventory_then_final(record)
                if fact_inventory_then_final
                else pipeline.predict_with_fact_inventory_then_full_final(
                    record,
                    inventory_max_items=fact_inventory_max_items,
                    inventory_position=fact_inventory_position,
                    inventory_categories=fact_inventory_categories,
                    timeline_v23=fact_inventory_timeline_v23,
                    procedure_navigation=procedure_inventory_full_final,
                    source_only_inventory=source_only_inventory,
                )
                if fact_inventory_full_final
                else pipeline.predict_with_vonly_draft_then_full_final(record)
                if vonly_draft_full_final
                else pipeline.predict(record)
            )
            return prediction, failed_attempts
        except Exception as exc:
            failed_attempts.append(
                {
                    "id": record["id"],
                    "attempt": attempt,
                    "error": str(exc),
                    "raw_response": exc.raw_response
                    if isinstance(exc, PredictionError) and exc.raw_response is not None
                    else None,
                }
            )
    return None, failed_attempts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--ids-file", help="JSON list, or object with ids, selecting input records")
    parser.add_argument("--mock", action="store_true")
    parser.add_argument(
        "--dump-inputs",
        action="store_true",
        help="write every final chat message/pass to inputs.jsonl before model calls",
    )
    parser.add_argument(
        "--dump-inputs-markdown",
        action="store_true",
        help="also write exact final message text to input_examples.md (requires --dump-inputs)",
    )
    parser.add_argument("--fresh", action="store_true", help="discard the existing prediction checkpoint")
    parser.add_argument("--input-example-limit", type=int, default=3)
    args = parser.parse_args()
    if args.dump_inputs_markdown and not args.dump_inputs:
        parser.error("--dump-inputs-markdown requires --dump-inputs")
    if args.input_example_limit < 1:
        parser.error("--input-example-limit must be positive")

    load_dotenv(ROOT / ".env")
    config = load_config(args.config)
    if config.raw.get("experiment", {}).get("lifecycle") == "preview" and not args.mock:
        raise ValueError("lifecycle: preview config may only run with --mock")
    output_dir = config.output_dir if not args.mock else config.output_dir.with_name(config.output_dir.name + "-mock")
    output_dir.mkdir(parents=True, exist_ok=True)
    logger = _logger(output_dir)
    checkpoint_path = output_dir / "predictions.jsonl"
    checkpoint_meta_path = output_dir / "checkpoint_meta.json"
    failed_response_path = output_dir / "failed_responses.jsonl"
    if args.fresh and checkpoint_path.exists():
        checkpoint_path.unlink()
    if args.fresh and checkpoint_meta_path.exists():
        checkpoint_meta_path.unlink()
    if args.fresh and failed_response_path.exists():
        failed_response_path.unlink()
    selected_ids = (
        load_record_id_panel(args.ids_file)
        if args.ids_file
        else (
            load_record_id_panel(config.data.fast_panel_ids_path)
            if config.data.fast_panel_ids_path
            else None
        )
    )
    effective_limit = args.limit if args.limit is not None else config.local_limit
    if selected_ids is not None and effective_limit is not None:
        source = "--limit" if args.limit is not None else "run.local_limit"
        raise ValueError(f"record ID panel and {source} are mutually exclusive")
    if args.limit is not None and config.local_limit is not None:
        logger.info("command-line --limit overrides run.local_limit=%d", config.local_limit)
    run_signature = _run_signature(
        config,
        args.mock,
        limit=effective_limit,
        selected_ids=selected_ids,
    )
    if checkpoint_path.exists():
        if not checkpoint_meta_path.exists():
            raise RuntimeError("checkpoint metadata is missing; use --fresh to restart safely")
        checkpoint_meta = json.loads(checkpoint_meta_path.read_text(encoding="utf-8"))
        if checkpoint_meta.get("run_signature") != run_signature:
            raise RuntimeError("checkpoint does not match current code/config/data; use --fresh")
    else:
        checkpoint_meta_path.write_text(
            json.dumps({"run_signature": run_signature}, indent=2) + "\n", encoding="utf-8"
        )
    checkpoint = _load_checkpoint(checkpoint_path) if config.resume else {}
    records = load_records(config.data.input_path)
    if selected_ids is not None:
        records = select_records_by_id(records, selected_ids)
    elif effective_limit is not None:
        records = records[:effective_limit]
    item_table = load_item_table(config.data.item_table_path)
    decision_cards = (
        load_decision_cards(config.decision_cards_path, item_table)
        if config.decision_cards_path
        else None
    )
    competition_products = (
        load_competition_product_index(config.competition_products_path)
        if config.competition_products_path
        else None
    )
    client = _make_client(config, args.mock)
    reference_text = (
        config.reference_path.read_text(encoding="utf-8") if config.reference_path else None
    )
    law_bundle_router = (
        MetadataLawBundleRouter(config.reference_bundle_dir)
        if config.reference_bundle_dir
        else None
    )
    pipeline = BaselinePipeline(
        item_table=item_table,
        client=client,
        max_document_chars=config.max_document_chars,
        prompt_mode=config.prompt_mode,
        include_normalized_facts=config.include_normalized_facts,
        context_strategy=config.context_strategy,
        notice_anchor_chars=config.notice_anchor_chars,
        overflow_split_enabled=config.overflow_split_enabled,
        strict_document_evidence=config.strict_document_evidence,
        absence_detection_strategy=config.absence_detection_strategy,
        decision_cards=decision_cards,
        competition_products=competition_products,
        count_tokens=_make_token_counter(config, args.mock),
        prompt_budget_tokens=config.max_model_len - config.output_reserve_tokens,
        reference_text=reference_text,
        law_bundle_router=law_bundle_router,
        v8_composite_merge_enabled=config.v8_composite_merge_enabled,
        v8_composite_merge_mode=config.v8_composite_merge_mode,
        candidate_detection=config.candidate_detection,
        active_items=config.active_items,
        prompt_layout=config.prompt_layout,
        prompt_profile=config.prompt_profile,
        role_directive=config.role_directive,
        item_catalog_style=config.item_catalog_style,
        metadata_style=config.metadata_style,
        output_mode=config.output_mode,
        visible_document_types=config.visible_document_types,
        frozen_rule_set=config.frozen_rule_set,
        locator_policy=(config.staged_run.locator_policy
                        if config.staged_run and config.staged_run.locator_policy
                        else "strict_v1"),
        applicability_gate_mode=config.applicability_gate_mode,
    )
    excluded_admissions: list[dict[str, str]] = []
    if config.context_strategy == "single_no_split":
        admitted_records: list[dict[str, Any]] = []
        for record in records:
            try:
                pipeline.contexts_for_record(record)
            except ContextAdmissionError as exc:
                excluded_admissions.append({"id": record["id"], "reason": str(exc)})
            else:
                admitted_records.append(record)
        records = admitted_records
        (output_dir / "admission.json").write_text(
            json.dumps(
                {
                    "strategy": "single_no_split",
                    "admitted_ids": [record["id"] for record in records],
                    "excluded": excluded_admissions,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    shutil.copy2(config.path, output_dir / "config.yaml")
    if config.reference_path:
        shutil.copy2(config.reference_path, output_dir / "reference_context.txt")
    if config.reference_bundle_dir:
        shutil.copytree(config.reference_bundle_dir, output_dir / "law_bundles", dirs_exist_ok=True)
        (output_dir / "law_bundle_routing.json").write_text(
            json.dumps(
                [law_bundle_router.audit_row(record) for record in records],
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    if config.decision_cards_path:
        shutil.copy2(config.decision_cards_path, output_dir / "decision_cards.json")
    if config.competition_products_path:
        shutil.copy2(config.competition_products_path, output_dir / "competition_products.json")
    if args.dump_inputs:
        dump_path = output_dir / "inputs.jsonl"
        input_entries: list[dict[str, Any]] = []
        with dump_path.open("w", encoding="utf-8") as handle:
            for record in records:
                for pass_index, context in enumerate(pipeline.contexts_for_record(record), 1):
                    messages = pipeline.messages_for_context(record, context)
                    entry = {
                        "id": record["id"],
                        "pass_index": pass_index,
                        "token_count": pipeline.count_tokens(messages)
                        if pipeline.count_tokens
                        else None,
                        "messages": messages,
                    }
                    input_entries.append(entry)
                    handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        if args.dump_inputs_markdown:
            _write_input_examples_markdown(
                output_dir / "input_examples.md", input_entries[:args.input_example_limit]
            )
    started = time.monotonic()
    failures: list[dict[str, str]] = []
    logger.info(
        "experiment=%s records=%d model=%s resumed=%d concurrency=%d",
        config.experiment_id,
        len(records),
        getattr(client, "model", config.llm.model),
        len(checkpoint),
        config.concurrency,
    )

    pending = [
        (position, record)
        for position, record in enumerate(records, 1)
        if record["id"] not in checkpoint
    ]
    for position, record in enumerate(records, 1):
        if record["id"] in checkpoint:
            logger.info("[%d/%d] %s cached", position, len(records), record["id"])

    with checkpoint_path.open("a", encoding="utf-8") as checkpoint_handle:
        with ThreadPoolExecutor(max_workers=config.concurrency) as executor:
            futures = {
                executor.submit(
                    _predict_with_retries,
                    pipeline,
                    record,
                    config.llm.prediction_attempts,
                    config.review_run is not None,
                    config.staged_run is not None and config.staged_run.mode == "triage_then_strict_v1",
                    config.staged_run is not None and config.staged_run.mode == "locator_then_final_v1",
                    config.staged_run is not None and config.staged_run.mode == "inventory_then_final_v1",
                    config.staged_run is not None and config.staged_run.mode == "fact_inventory_then_final_v1",
                    config.staged_run is not None and config.staged_run.mode in {"fact_inventory_full_final_v1", "fact_inventory_full_final_v2", "fact_inventory_full_final_v3", "fact_inventory_full_final_v4", "fact_inventory_full_final_timeline_v23", "procedure_inventory_full_final_v1", "fact_inventory_full_final_source_only_v1"},
                    4 if config.staged_run is not None and config.staged_run.mode == "fact_inventory_full_final_v2" else 3,
                    "before_source" if config.staged_run is not None and config.staged_run.mode == "fact_inventory_full_final_v3" else "after_source",
                    FACT_INVENTORY_CATEGORIES_V2 if config.staged_run is not None and config.staged_run.mode == "fact_inventory_full_final_v4" else FACT_INVENTORY_CATEGORIES,
                    config.staged_run is not None and config.staged_run.mode == "fact_inventory_full_final_timeline_v23",
                    config.staged_run is not None and config.staged_run.mode == "procedure_inventory_full_final_v1",
                    config.staged_run is not None and config.staged_run.mode == "fact_inventory_full_final_source_only_v1",
                    config.staged_run is not None and config.staged_run.mode == "vonly_draft_full_final_v1",
                ): (position, record)
                for position, record in pending
            }
            for future in as_completed(futures):
                position, record = futures[future]
                prediction, failed_attempts = future.result()
                if failed_attempts:
                    with failed_response_path.open("a", encoding="utf-8") as failed_handle:
                        for failed_attempt in failed_attempts:
                            failed_handle.write(json.dumps(failed_attempt, ensure_ascii=False) + "\n")
                            logger.warning(
                                "[%d/%d] %s attempt %d/%d failed: %s",
                                position,
                                len(records),
                                record["id"],
                                failed_attempt["attempt"],
                                config.llm.prediction_attempts,
                                failed_attempt["error"],
                            )
                if prediction is None:
                    failures.append({"id": record["id"], "error": failed_attempts[-1]["error"]})
                    continue
                value = _prediction_to_json(prediction)
                checkpoint[record["id"]] = value
                checkpoint_handle.write(json.dumps(value, ensure_ascii=False) + "\n")
                checkpoint_handle.flush()
                total_latency = float(value["latency_seconds"])
                logged_usage = value["usage"]
                logger.info(
                    "[%d/%d] %s %.2fs prompt=%s completion=%s",
                    position,
                    len(records),
                    record["id"],
                    total_latency,
                    logged_usage.get("prompt_tokens", "?"),
                    logged_usage.get("completion_tokens", "?"),
                )

    if failures:
        (output_dir / "failures.json").write_text(
            json.dumps(failures, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        raise RuntimeError(f"{len(failures)} predictions failed; rerun to resume")

    ordered_values = [checkpoint[record["id"]] for record in records]
    if args.dump_inputs and config.staged_run is not None:
        _write_staged_input_examples_markdown(
            output_dir / "staged_input_examples.md", ordered_values, args.input_example_limit
        )
    submission_path = output_dir / "submission.csv"
    write_submission([value["row"] for value in ordered_values], submission_path)
    validation = validate_submission(submission_path, records)
    (output_dir / "validation.json").write_text(
        json.dumps(
            {"passed": validation.passed, "errors": validation.errors, "warnings": validation.warnings},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if not validation.passed:
        raise RuntimeError(f"submission validation failed: {validation.errors[:5]}")

    metrics: dict[str, Any] | None = None
    if config.data.labels_path is not None:
        metrics, per_item, errors = evaluate_submission(
            submission_path,
            config.data.labels_path,
            records,
        )
        metrics = {"experiment_id": config.experiment_id, **metrics}
        (output_dir / "metrics.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        write_rows(output_dir / "per_item_metrics.csv", per_item)
        write_rows(output_dir / "errors.csv", errors)

    usage_keys = ("prompt_tokens", "completion_tokens", "total_tokens", "cost")
    usage = {
        key: sum(_usage_number(value.get("usage", {}).get(key, 0)) for value in ordered_values)
        for key in usage_keys
    }
    run_meta = {
        "experiment_id": config.experiment_id,
        "git_commit": _git_commit(),
        "input": str(config.data.input_path.relative_to(ROOT)),
        "input_sha256": _sha256(config.data.input_path),
        "labels_sha256": _sha256(config.data.labels_path) if config.data.labels_path else None,
        "run_signature": run_signature,
        "source_sha256": _source_hashes(),
        "input_count": len(records),
        "local_limit": config.local_limit,
        "fast_panel_ids_path": str(config.data.fast_panel_ids_path.relative_to(ROOT))
        if config.data.fast_panel_ids_path
        else None,
        "derived_data": list(config.derived_data),
        "reference_path": str(config.reference_path.relative_to(ROOT))
        if config.reference_path
        else None,
        "reference_sha256": _sha256(config.reference_path) if config.reference_path else None,
        "reference_bundle_dir": str(config.reference_bundle_dir.relative_to(ROOT))
        if config.reference_bundle_dir
        else None,
        "reference_bundle_sha256": _tree_hashes(config.reference_bundle_dir),
        "decision_cards_path": str(config.decision_cards_path.relative_to(ROOT))
        if config.decision_cards_path
        else None,
        "decision_cards_sha256": _sha256(config.decision_cards_path)
        if config.decision_cards_path
        else None,
        "competition_products_path": str(config.competition_products_path.relative_to(ROOT))
        if config.competition_products_path
        else None,
        "competition_products_sha256": _sha256(config.competition_products_path)
        if config.competition_products_path
        else None,
        "llm_provider": "mock" if args.mock else config.llm.provider,
        "review_run": (
            {
                "mode": config.review_run.mode,
                "final_judgment_source": config.review_run.final_judgment_source,
            }
            if config.review_run
            else None
        ),
        "staged_run": (
            {"mode": config.staged_run.mode}
            if config.staged_run
            else None
        ),
        "model": getattr(client, "model", config.llm.model),
        "rag_enabled": bool(config.reference_path or config.reference_bundle_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "runtime_seconds": round(time.monotonic() - started, 3),
        "usage": usage,
        "validation_warning_count": len(validation.warnings),
        "macro_f1": metrics["leaderboard_metric"]["macro_f1"] if metrics else None,
    }
    (output_dir / "run_meta.json").write_text(
        json.dumps(run_meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    logger.info("completed in %.1fs macro_f1=%s", run_meta["runtime_seconds"], run_meta["macro_f1"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
