#!/usr/bin/env python3
"""Export the exact sanitized request body for one local experiment record."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.data import (
    load_competition_product_index,
    load_decision_cards,
    load_item_table,
    load_records,
)
from src.external.openrouter import MockClient
from src.law_bundles import MetadataLawBundleRouter
from src.pipeline import BaselinePipeline


def _request_preview(
    config: Any, messages: list[dict[str, str]], response_schema: dict[str, Any]
) -> dict[str, Any]:
    return {
        "model": config.llm.model,
        "messages": messages,
        "temperature": config.llm.temperature,
        "max_tokens": config.llm.max_tokens,
        "seed": config.llm.seed,
        "stream": False,
        "provider": {
            "require_parameters": config.llm.require_parameters,
            "sort": config.llm.provider_sort,
        },
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "pps_compliance_judgment",
                "strict": True,
                "schema": response_schema,
            },
        },
    }


def _markdown_preview(
    record_id: str, config: Any, messages_by_context: list[list[dict[str, str]]]
) -> str:
    return (
        f"# Actual LLM Input: {record_id}\n\n"
        "This file is generated without making an API call. It is the exact `messages` "
        "content constructed by the current experiment configuration. The companion "
        "JSON also includes the non-secret request settings and response schema.\n\n"
        "## Effective Configuration\n\n"
        f"- Model: `{config.llm.model}`\n"
        f"- `prompt.max_document_chars`: `{config.max_document_chars}`\n"
        f"- `max_tokens`: `{config.llm.max_tokens}`\n"
        f"- Temperature: `{config.llm.temperature}`\n"
        f"- Seed: `{config.llm.seed}`\n\n"
        + "".join(
            "## System Message" + (f" (context {index})" if len(messages_by_context) > 1 else "") + "\n\n"
            f"```text\n{messages[0]['content']}\n```\n\n"
            "## User Message" + (f" (context {index})" if len(messages_by_context) > 1 else "") + "\n\n"
            f"```text\n{messages[1]['content']}\n```\n\n"
            for index, messages in enumerate(messages_by_context, 1)
        )
    )


def build_pipeline_for_preview(config: Any, count_tokens=None) -> BaselinePipeline:
    """Mirror the shared runner's pipeline construction without a provider call."""
    item_table = load_item_table(config.data.item_table_path)
    decision_cards = (
        load_decision_cards(config.decision_cards_path, item_table)
        if config.decision_cards_path else None
    )
    competition_products = (
        load_competition_product_index(config.competition_products_path)
        if config.competition_products_path else None
    )
    reference_text = config.reference_path.read_text(encoding="utf-8") if config.reference_path else None
    law_bundle_router = (
        MetadataLawBundleRouter(config.reference_bundle_dir)
        if config.reference_bundle_dir else None
    )
    return BaselinePipeline(
        item_table=item_table,
        client=MockClient(),
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
        competition_product_context_mode=config.competition_product_context_mode,
        count_tokens=count_tokens,
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--record-id", default="PPS-DEV-01")
    parser.add_argument("--output-dir", default="outputs/prompt-inspection")
    parser.add_argument(
        "--exact-tokenizer", action="store_true",
        help="use the configured Gemma tokenizer so overflow packs exactly match the experiment",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    record = next(
        (item for item in load_records(config.data.input_path) if item["id"] == args.record_id),
        None,
    )
    if record is None:
        raise ValueError(f"record not found: {args.record_id}")
    count_tokens = None
    if args.exact_tokenizer:
        from transformers import AutoTokenizer
        from scripts.profile_context_admission import _token_counter

        tokenizer = AutoTokenizer.from_pretrained(
            config.llm.tokenizer_source or config.llm.model
        )
        count_tokens = _token_counter(tokenizer)
    pipeline = build_pipeline_for_preview(config, count_tokens=count_tokens)
    effective_pipeline, inactive = pipeline.effective_pipeline_for_record(record)
    contexts = effective_pipeline.contexts_for_record(record)
    messages_by_context = [
        effective_pipeline.messages_for_context(record, context) for context in contexts
    ]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = args.record_id.lower()
    (output_dir / f"{stem}.request.json").write_text(
        json.dumps(
            {
                **_request_preview(
                    config, messages_by_context[0], effective_pipeline.response_schema
                ),
                "applicability_inactive_items": inactive,
            },
            ensure_ascii=False, indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    (output_dir / f"{stem}.messages.md").write_text(
        _markdown_preview(args.record_id, config, messages_by_context), encoding="utf-8"
    )
    print(output_dir / f"{stem}.messages.md")
    print(output_dir / f"{stem}.request.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
