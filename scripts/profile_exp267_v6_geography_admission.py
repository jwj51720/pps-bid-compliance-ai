#!/usr/bin/env python3
"""Exact-token capacity gate for EXP267's v6 source/final stages."""

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

from scripts.audit_complete_fact_admission import source_coverage_gaps  # noqa: E402
from scripts.inspect_prompt import build_pipeline_for_preview  # noqa: E402
from src.config import load_config  # noqa: E402
from src.context_budget import pack_contexts_to_token_budget  # noqa: E402
from src.data import load_records  # noqa: E402
from src.prompt import (  # noqa: E402
    append_fact_inventory,
    build_fact_inventory_system_prompt,
    build_official_baseline_context,
    build_source_only_fact_messages,
)
from src.schema import V6_GEOGRAPHY_FACT_FIELDS  # noqa: E402


def make_counter(source: str):
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(source)

    def count(messages: list[dict[str, str]]) -> int:
        encoded = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True
        )
        token_ids = encoded["input_ids"] if isinstance(encoded, Mapping) else encoded
        return len(token_ids)

    return count


def summary(values: list[int]) -> dict[str, int]:
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "total": sum(ordered),
        "min": ordered[0],
        "p50": ordered[ceil(len(ordered) * 0.5) - 1],
        "p95": ordered[ceil(len(ordered) * 0.95) - 1],
        "max": ordered[-1],
    }


def profile(config_path: Path, batch_size: int) -> dict[str, Any]:
    config = load_config(config_path)
    pipeline = build_pipeline_for_preview(config)
    count_tokens = make_counter(config.llm.tokenizer_source or config.llm.model)
    pipeline.count_tokens = count_tokens
    budget = config.max_model_len - config.output_reserve_tokens
    records = load_records(config.data.input_path)
    stage_tokens: list[int] = []
    final_tokens: list[int] = []
    stage_calls = 0
    final_calls = 0
    stage_distribution: Counter[int] = Counter()
    final_distribution: Counter[int] = Counter()
    stage_omissions: list[dict[str, Any]] = []
    final_omissions: list[dict[str, Any]] = []
    synthetic_inventory = {
        field: tuple(("D0", "가" * 360) for _ in range(3))
        for field in V6_GEOGRAPHY_FACT_FIELDS
    }
    stage_system = build_fact_inventory_system_prompt(
        categories=V6_GEOGRAPHY_FACT_FIELDS
    )

    for record in records:
        visible = pipeline._visible_record(record)
        stage_contexts = pipeline.contexts_for_record(record)
        stage_calls += len(stage_contexts)
        stage_distribution[len(stage_contexts)] += 1
        stage_omissions.extend(
            {"id": record["id"], **gap}
            for gap in source_coverage_gaps(visible, stage_contexts)
        )
        for context in stage_contexts:
            source = context.text if hasattr(context, "text") else (
                context
                if context is not None
                else build_official_baseline_context(visible, None)
            )
            messages = build_source_only_fact_messages(
                stage_system,
                source,
                pipeline.organizer_input_semantics_for_record(visible),
            )
            stage_tokens.append(count_tokens(messages))

        def final_messages_for(context):
            return append_fact_inventory(
                pipeline.messages_for_context(record, context),
                synthetic_inventory,
                categories=V6_GEOGRAPHY_FACT_FIELDS,
            )

        final_contexts = pack_contexts_to_token_budget(
            visible,
            pipeline.system_prompt_for_record(record),
            count_tokens,
            budget,
            pipeline.notice_anchor_chars,
            message_builder=final_messages_for,
        )
        final_calls += len(final_contexts)
        final_distribution[len(final_contexts)] += 1
        final_omissions.extend(
            {"id": record["id"], **gap}
            for gap in source_coverage_gaps(visible, final_contexts)
        )
        final_tokens.extend(
            count_tokens(final_messages_for(context)) for context in final_contexts
        )

    return {
        "experiment_id": config.experiment_id,
        "method": "label-blind exact Gemma tokenizer with maximum legal schema payload",
        "record_count": len(records),
        "prompt_budget_tokens": budget,
        "batch_size": batch_size,
        "stage_calls": stage_calls,
        "final_calls_upper_bound": final_calls,
        "total_calls_upper_bound": stage_calls + final_calls,
        "stage_batch_rounds": ceil(stage_calls / batch_size),
        "final_batch_rounds_upper_bound": ceil(final_calls / batch_size),
        "stage_pass_distribution": dict(sorted(stage_distribution.items())),
        "final_pass_distribution_upper_bound": dict(sorted(final_distribution.items())),
        "stage_prompt_tokens": summary(stage_tokens),
        "final_prompt_tokens_upper_bound": summary(final_tokens),
        "stage_source_document_omission_count": len(stage_omissions),
        "final_source_document_omission_count": len(final_omissions),
        "stage_source_document_omissions": stage_omissions,
        "final_source_document_omissions": final_omissions,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()
    if args.batch_size < 1:
        raise ValueError("batch-size must be positive")
    result = profile(args.config, args.batch_size)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
