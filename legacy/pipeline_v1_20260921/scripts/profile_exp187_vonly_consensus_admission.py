#!/usr/bin/env python3
"""Exact-token admission profile for EXP187's two V-only drafts and resolver."""

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
from src.prompt import append_untrusted_vonly_drafts  # noqa: E402
from src.schema import ITEMS  # noqa: E402


def make_token_counter(tokenizer_source: str):
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(tokenizer_source)

    def count(messages: list[dict[str, str]]) -> int:
        encoded = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True)
        token_ids = encoded["input_ids"] if isinstance(encoded, Mapping) else encoded
        return len(token_ids)

    return count


def token_summary(values: list[int]) -> dict[str, int]:
    if not values:
        return {"count": 0, "total": 0, "min": 0, "p50": 0, "p95": 0, "max": 0}
    ordered = sorted(values)
    return {
        "count": len(values), "total": sum(values), "min": ordered[0],
        "p50": ordered[ceil(len(ordered) * .50) - 1],
        "p95": ordered[ceil(len(ordered) * .95) - 1], "max": ordered[-1],
    }


def profile(config_path: Path, batch_size: int) -> dict[str, Any]:
    config = load_config(config_path)
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    pipeline = build_pipeline_for_preview(config)
    count_tokens = make_token_counter(config.llm.tokenizer_source or config.llm.model)
    pipeline.count_tokens = count_tokens
    draft_pipeline = pipeline._labels_only_draft_pipeline()
    records = load_records(config.data.input_path)
    budget = config.max_model_len - config.output_reserve_tokens
    draft_tokens: list[int] = []
    final_tokens: list[int] = []
    draft_calls = final_calls = 0
    draft_omissions: list[dict[str, Any]] = []
    final_omissions: list[dict[str, Any]] = []
    final_distribution: Counter[int] = Counter()
    zero_draft = {item: {"위반여부": 0, "근거문구": None} for item in ITEMS}
    for record in records:
        visible = pipeline._visible_record(record)
        draft_contexts = draft_pipeline.contexts_for_record(record)
        draft_calls += 2 * len(draft_contexts)
        per_draft_tokens = [
            count_tokens(draft_pipeline.messages_for_context(record, context))
            for context in draft_contexts
        ]
        draft_tokens.extend(per_draft_tokens * 2)
        draft_omissions.extend(
            {"id": record["id"], **gap}
            for gap in source_coverage_gaps(visible, draft_contexts)
        )

        def messages_for(context: str | None) -> list[dict[str, str]]:
            return append_untrusted_vonly_drafts(
                pipeline.messages_for_context(record, context),
                (zero_draft, zero_draft), ITEMS,
            )

        contexts = pack_contexts_to_token_budget(
            visible, pipeline.system_prompt_for_record(record), count_tokens, budget,
            pipeline.notice_anchor_chars, message_builder=messages_for,
        )
        final_calls += len(contexts)
        final_distribution[len(contexts)] += 1
        final_tokens.extend(count_tokens(messages_for(context)) for context in contexts)
        final_omissions.extend(
            {"id": record["id"], **gap}
            for gap in source_coverage_gaps(visible, contexts)
        )
    return {
        "experiment_id": config.experiment_id,
        "method": "exact Gemma tokenizer admission; no labels or provider calls",
        "record_count": len(records), "prompt_budget_tokens": budget,
        "batch_size": batch_size, "draft_calls": draft_calls, "final_calls": final_calls,
        "total_calls": draft_calls + final_calls,
        "draft_batch_rounds": ceil(draft_calls / batch_size),
        "final_batch_rounds": ceil(final_calls / batch_size),
        "total_batch_rounds": ceil(draft_calls / batch_size) + ceil(final_calls / batch_size),
        "final_pass_distribution": dict(sorted(final_distribution.items())),
        "draft_prompt_tokens": token_summary(draft_tokens),
        "final_prompt_tokens": token_summary(final_tokens),
        "draft_source_document_omission_count": len(draft_omissions),
        "final_source_document_omission_count": len(final_omissions),
        "draft_source_document_omissions": draft_omissions,
        "final_source_document_omissions": final_omissions,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()
    result = profile(args.config, args.batch_size)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
