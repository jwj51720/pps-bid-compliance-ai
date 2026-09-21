#!/usr/bin/env python3
"""Label-blind exact-token capacity gate for EXP188's 24 one-excerpt slots."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from math import ceil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_complete_fact_admission import source_coverage_gaps  # noqa: E402
from scripts.inspect_prompt import build_pipeline_for_preview  # noqa: E402
from src.config import load_config  # noqa: E402
from src.context_budget import pack_contexts_to_token_budget  # noqa: E402
from src.data import load_records  # noqa: E402
from src.schema import ITEMS  # noqa: E402


def make_counter(source: str):
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(source)

    def count(messages: list[dict[str, str]]) -> int:
        encoded = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True)
        ids = encoded["input_ids"] if isinstance(encoded, Mapping) else encoded
        return len(ids)

    return count


def append_upper_bound(messages: list[dict[str, str]], chars: int) -> list[dict[str, str]]:
    """Append synthetic, non-source slots only to measure worst prompt capacity."""
    lines = ["[항목별 원문 관계 후보 — 최종 판정 아님]",
             "아래 후보는 source-only navigation의 용량 상한을 나타낸다."]
    for item in ITEMS:
        lines.append(f"- {item}: [D0] {'가' * chars}")
    return [*messages, {"role": "user", "content": "\n".join(lines)}]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--excerpt-chars", type=int, default=180)
    args = parser.parse_args()
    if args.excerpt_chars < 1:
        raise ValueError("excerpt-chars must be positive")
    config = load_config(args.config)
    pipeline = build_pipeline_for_preview(config)
    counter = make_counter(config.llm.tokenizer_source or config.llm.model)
    budget = config.max_model_len - config.output_reserve_tokens
    calls = 0
    tokens: list[int] = []
    omissions: list[dict[str, str]] = []
    distribution: dict[int, int] = {}
    for record in load_records(config.data.input_path):
        visible = pipeline._visible_record(record)

        def messages_for(context: str | None) -> list[dict[str, str]]:
            return append_upper_bound(pipeline.messages_for_context(record, context), args.excerpt_chars)

        contexts = pack_contexts_to_token_budget(
            visible, pipeline.system_prompt_for_record(record), counter, budget,
            pipeline.notice_anchor_chars, message_builder=messages_for,
        )
        calls += len(contexts)
        distribution[len(contexts)] = distribution.get(len(contexts), 0) + 1
        tokens.extend(counter(messages_for(context)) for context in contexts)
        omissions.extend({"id": record["id"], **gap} for gap in source_coverage_gaps(visible, contexts))
    result = {
        "kind": "label_blind_synthetic_upper_bound",
        "record_count": 200, "slot_count": len(ITEMS), "excerpt_chars": args.excerpt_chars,
        "prompt_budget_tokens": budget, "final_calls": calls,
        "batch64_rounds": ceil(calls / 64), "pass_distribution": distribution,
        "max_prompt_tokens": max(tokens), "p50_prompt_tokens": sorted(tokens)[len(tokens) // 2],
        "source_document_omission_count": len(omissions), "source_document_omissions": omissions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
