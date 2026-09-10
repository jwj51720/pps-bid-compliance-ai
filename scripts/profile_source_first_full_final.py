#!/usr/bin/env python3
"""Profile a source-first architecture whose final stage still sees all source.

No provider is called.  The script proves the runtime consequence of appending
an untrusted fact-navigation ledger to a complete-source final V/E message.
It intentionally distinguishes actual saved ledger lengths from a schema-sized
upper bound; neither is allowed to masquerade as an accuracy result.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping
from math import ceil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.inspect_prompt import build_pipeline_for_preview
from scripts.audit_complete_fact_admission import source_coverage_gaps
from src.config import load_config
from src.context_budget import pack_contexts_to_token_budget
from src.data import load_records
from src.prompt import (
    append_fact_inventory,
    build_fact_inventory_system_prompt,
    build_messages,
    build_official_baseline_context,
)
from src.schema import FACT_INVENTORY_CATEGORIES


def make_token_counter(tokenizer_source: str):
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(tokenizer_source)

    def count(messages: list[dict[str, str]]) -> int:
        encoded = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True
        )
        token_ids = encoded["input_ids"] if isinstance(encoded, Mapping) else encoded
        return len(token_ids)

    return count


def _inventory_from_saved_prediction(row: dict[str, Any]) -> dict[str, tuple[tuple[str, str], ...]]:
    saved = row.get("staged_run", {}).get("inventory", {}).get("by_category", {})
    return {
        category: tuple((str(doc_id), str(text)) for doc_id, text in saved.get(category, []))
        for category in FACT_INVENTORY_CATEGORIES
    }


def _synthetic_inventory(chars_per_excerpt: int, excerpts_per_category: int) -> dict[str, tuple[tuple[str, str], ...]]:
    # Token-only upper/lower profile.  The string is never a model input and is
    # deliberately marked synthetic in the output report.
    text = "가" * chars_per_excerpt
    return {
        category: tuple(("synthetic", text) for _ in range(excerpts_per_category))
        for category in FACT_INVENTORY_CATEGORIES
    }


def _token_summary(values: list[int]) -> dict[str, int | float]:
    """Return compact exact-token distribution facts without model calls."""
    if not values:
        return {"count": 0, "total": 0, "min": 0, "p50": 0, "p95": 0, "max": 0}
    ordered = sorted(values)

    def percentile(percent: float) -> int:
        return ordered[min(len(ordered) - 1, ceil(percent * len(ordered)) - 1)]

    return {
        "count": len(values), "total": sum(values), "min": ordered[0],
        "p50": percentile(0.50), "p95": percentile(0.95), "max": ordered[-1],
    }


def profile(
    config_path: Path, saved_predictions: Path | None,
    input_path: Path | None = None,
    batch_size: int = 64,
) -> dict[str, Any]:
    config = load_config(config_path)
    if config.max_document_chars is not None or not config.overflow_split_enabled:
        raise ValueError("profile requires complete-source exact-token admission")
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    pipeline = build_pipeline_for_preview(config)
    count_tokens = make_token_counter(config.llm.tokenizer_source or config.llm.model)
    pipeline.count_tokens = count_tokens
    effective_input = input_path or config.data.input_path
    records = load_records(effective_input)
    saved: dict[str, dict[str, Any]] = {}
    if saved_predictions:
        saved = {row["id"]: row for row in map(json.loads, saved_predictions.read_text(encoding="utf-8").splitlines())}
    budget = config.max_model_len - config.output_reserve_tokens

    scenarios: dict[str, tuple[str, dict[str, dict[str, tuple[tuple[str, str], ...]]], list[dict[str, Any]]]] = {
        "empty_navigation": ("no navigation ledger; confirms base final packing", {}, records),
        "saved_fast_inventory": ("actual saved EXP157 navigation, limited to its matching fast records", {
            record_id: _inventory_from_saved_prediction(row) for record_id, row in saved.items()
        }, [record for record in records if record["id"] in saved]),
        "moderate_upper": ("synthetic 1 excerpt × 160 chars × 7 categories", {}, records),
        "schema_upper": ("synthetic schema maximum: 3 excerpts × 360 chars × 7 categories", {}, records),
    }
    report: dict[str, Any] = {
        "experiment_id": config.experiment_id,
        "method": "exact Gemma chat-template token admission; no provider or labels",
        "input_path": str(effective_input),
        "batch_size": batch_size,
        "prompt_budget_tokens": budget,
        "stage_one_complete_source_calls": sum(len(pipeline.contexts_for_record(record)) for record in records),
        "record_count": len(records),
        "scenarios": {},
    }
    for name, (description, by_id, scenario_records) in scenarios.items():
        rows = []
        stage_one_tokens: list[int] = []
        stage_one_source_omissions: list[dict[str, Any]] = []
        final_source_omissions: list[dict[str, Any]] = []
        for record in scenario_records:
            if name == "moderate_upper":
                inventory = _synthetic_inventory(160, 1)
            elif name == "schema_upper":
                inventory = _synthetic_inventory(360, 3)
            else:
                inventory = by_id.get(record["id"], {category: () for category in FACT_INVENTORY_CATEGORIES})
            system = pipeline.system_prompt_for_record(record)

            for stage_context in pipeline.contexts_for_record(record):
                stage_source = (
                    stage_context.text if hasattr(stage_context, "text") else (
                        stage_context if stage_context is not None
                        else build_official_baseline_context(pipeline._visible_record(record), None)
                    )
                )
                stage_messages = build_messages(
                    pipeline._visible_record(record), build_fact_inventory_system_prompt(),
                    pipeline.max_document_chars, document_context=stage_source,
                    prompt_profile=pipeline.prompt_profile,
                    metadata_style=pipeline.metadata_style,
                    output_mode="labels_only",
                )
                stage_one_tokens.append(count_tokens(stage_messages))

            def messages_for(context: str | None) -> list[dict[str, str]]:
                return append_fact_inventory(pipeline.messages_for_context(record, context), inventory)

            contexts = pack_contexts_to_token_budget(
                pipeline._visible_record(record), system, count_tokens, budget,
                pipeline.notice_anchor_chars, message_builder=messages_for,
            )
            final_messages = [messages_for(context) for context in contexts]
            tokens = [count_tokens(messages) for messages in final_messages]
            if any(value > budget for value in tokens):
                raise AssertionError(f"over-budget final pack: {record['id']}")
            visible = pipeline._visible_record(record)
            stage_one_source_omissions.extend(
                {"id": record["id"], **gap}
                for gap in source_coverage_gaps(visible, pipeline.contexts_for_record(record))
            )
            final_source_omissions.extend(
                {"id": record["id"], **gap}
                for gap in source_coverage_gaps(visible, contexts)
            )
            rows.append({"id": record["id"], "final_passes": len(contexts), "final_pack_tokens": tokens})
        final_calls = sum(row["final_passes"] for row in rows)
        stage_one_calls = sum(len(pipeline.contexts_for_record(record)) for record in scenario_records)
        report["scenarios"][name] = {
            "description": description,
            "record_count": len(scenario_records),
            "records_with_saved_inventory": sum(record["id"] in by_id for record in scenario_records),
            "stage_one_calls": stage_one_calls,
            "final_calls": final_calls,
            "total_stage_one_plus_final_calls": stage_one_calls + final_calls,
            "stage_one_batch_rounds": ceil(stage_one_calls / batch_size),
            "final_batch_rounds": ceil(final_calls / batch_size),
            "total_independent_batch_rounds": (
                ceil(stage_one_calls / batch_size) + ceil(final_calls / batch_size)
            ),
            "final_pass_distribution": dict(sorted(Counter(row["final_passes"] for row in rows).items())),
            "stage_one_prompt_tokens": _token_summary(stage_one_tokens),
            "final_prompt_tokens": _token_summary(
                [token for row in rows for token in row["final_pack_tokens"]]
            ),
            "stage_one_source_document_omission_count": len(stage_one_source_omissions),
            "final_source_document_omission_count": len(final_source_omissions),
            "stage_one_source_document_omissions": stage_one_source_omissions,
            "final_source_document_omissions": final_source_omissions,
            "rows": rows,
        }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--saved-predictions")
    parser.add_argument(
        "--input",
        help="Optional organizer-format JSONL/JSONL.GZ input to profile without changing policy config.",
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()
    report = profile(
        Path(args.config),
        Path(args.saved_predictions) if args.saved_predictions else None,
        Path(args.input) if args.input else None,
        args.batch_size,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    compact = {**report, "scenarios": {
        name: {key: value for key, value in scenario.items() if key != "rows"}
        for name, scenario in report["scenarios"].items()
    }}
    print(json.dumps(compact, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
