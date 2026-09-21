#!/usr/bin/env python3
"""Profile exact tokenizer admission and adaptive-pass counts without LLM calls."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.data import (
    load_competition_product_index,
    load_decision_cards,
    load_item_table,
    load_record_id_panel,
    load_records,
    select_records_by_id,
)
from src.pipeline import BaselinePipeline
from scripts.audit_complete_fact_admission import source_coverage_gaps


def _token_counter(tokenizer):
    def count(messages: list[dict[str, str]]) -> int:
        encoded = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True
        )
        token_ids = encoded["input_ids"] if isinstance(encoded, Mapping) else encoded
        return len(token_ids)

    return count


def _pipeline_for_policy(
    config, item_table, cards, products, count_tokens, *,
    active_items=None, prompt_mode=None, prompt_profile=None,
):
    return BaselinePipeline(
        item_table=item_table,
        client=None,
        max_document_chars=config.max_document_chars,
        prompt_mode=prompt_mode or config.prompt_mode,
        include_normalized_facts=config.include_normalized_facts,
        context_strategy=config.context_strategy,
        notice_anchor_chars=config.notice_anchor_chars,
        overflow_split_enabled=config.overflow_split_enabled,
        strict_document_evidence=config.strict_document_evidence,
        absence_detection_strategy=config.absence_detection_strategy,
        decision_cards=cards,
        competition_products=products,
        competition_product_context_mode=config.competition_product_context_mode,
        organizer_input_semantics_mode=config.organizer_input_semantics_mode,
        count_tokens=count_tokens,
        prompt_budget_tokens=config.max_model_len - config.output_reserve_tokens,
        active_items=active_items or config.active_items,
        prompt_layout=config.prompt_layout,
        prompt_profile=prompt_profile or config.prompt_profile,
        role_directive=config.role_directive,
        item_catalog_style=config.item_catalog_style,
        metadata_style=config.metadata_style,
        output_mode=config.output_mode,
        visible_document_types=config.visible_document_types,
    )


def _profile_policy(pipeline, records, count_tokens, budget):
    rows = []
    source_document_count = 0
    source_omissions = []
    for record in records:
        full_tokens = count_tokens(pipeline.messages_for_context(record, None))
        contexts = pipeline.contexts_for_record(record)
        source_document_count += len(record["docs"])
        source_omissions.extend(
            {"id": record["id"], **gap}
            for gap in source_coverage_gaps(pipeline._visible_record(record), contexts)
        )
        pass_tokens = [
            count_tokens(pipeline.messages_for_context(record, context))
            for context in contexts
        ]
        rows.append(
            {
                "id": record["id"],
                "full_prompt_tokens": full_tokens,
                "fits_one_pass": full_tokens <= budget,
                "pass_count": len(contexts),
                "pass_prompt_tokens": pass_tokens,
                "document_types": [document["type"] for document in record["docs"]],
            }
        )
    rows.sort(key=lambda row: (-row["full_prompt_tokens"], row["id"]))
    return {
        "record_count": len(rows),
        "one_pass_count": sum(row["fits_one_pass"] for row in rows),
        "overflow_count": sum(not row["fits_one_pass"] for row in rows),
        "call_count": sum(row["pass_count"] for row in rows),
        "source_document_count": source_document_count,
        "source_document_omission_count": len(source_omissions),
        "source_document_omissions": source_omissions,
        "pass_count_distribution": dict(
            sorted(Counter(row["pass_count"] for row in rows).items())
        ),
        "largest_rows": rows[:20],
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--all-records", action="store_true",
        help="ignore a configured fast panel/local limit for label-blind full-input profiling",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    if config.context_strategy != "single":
        raise ValueError("this diagnostic is for prompt.context_strategy: single")
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        config.llm.tokenizer_source or config.llm.model
    )
    count_tokens = _token_counter(tokenizer)
    item_table = load_item_table(config.data.item_table_path)
    cards = (
        load_decision_cards(config.decision_cards_path, item_table)
        if config.decision_cards_path
        else None
    )
    products = (
        load_competition_product_index(config.competition_products_path)
        if config.competition_products_path
        else None
    )
    pipeline = _pipeline_for_policy(
        config, item_table, cards, products, count_tokens,
    )
    budget = config.max_model_len - config.output_reserve_tokens
    records = load_records(config.data.input_path)
    if args.all_records:
        pass
    elif config.data.fast_panel_ids_path:
        records = select_records_by_id(
            records, load_record_id_panel(config.data.fast_panel_ids_path)
        )
    elif config.local_limit is not None:
        records = records[:config.local_limit]
    base_profile = _profile_policy(pipeline, records, count_tokens, budget)
    specialist_section = config.raw.get("specialist_run", {}) or {}
    specialist_mode = str(specialist_section.get("mode", "off"))
    specialist_profiles = []
    if specialist_mode == "replace_items_v1":
        for specialist in specialist_section.get("specialists", []):
            specialist_cards_path = ROOT / str(specialist["decision_cards_path"])
            specialist_cards = load_decision_cards(specialist_cards_path, item_table)
            specialist_pipeline = _pipeline_for_policy(
                config,
                item_table,
                specialist_cards,
                products,
                count_tokens,
                active_items=tuple(str(item) for item in specialist["active_items"]),
                prompt_mode=str(specialist["mode"]),
                prompt_profile=str(specialist["profile"]),
            )
            profile = _profile_policy(
                specialist_pipeline, records, count_tokens, budget
            )
            specialist_profiles.append(
                {
                    "id": str(specialist["id"]),
                    "active_items": list(specialist["active_items"]),
                    **{key: value for key, value in profile.items() if key != "rows"},
                }
            )
    elif specialist_mode != "off":
        raise ValueError(f"unsupported specialist_run.mode: {specialist_mode}")

    declared_call_count = base_profile["call_count"] + sum(
        profile["call_count"] for profile in specialist_profiles
    )
    result = {
        "experiment_id": config.experiment_id,
        "method": "Gemma tokenizer.apply_chat_template on final shared-pipeline messages",
        "tokenizer_source": config.llm.tokenizer_source or config.llm.model,
        "prompt_budget_tokens": budget,
        **{key: value for key, value in base_profile.items() if key != "rows"},
        "base_call_count": base_profile["call_count"],
        "specialist_runs": specialist_profiles,
        "declared_execution_call_count": declared_call_count,
        "call_count": declared_call_count,
        "rows": base_profile["rows"],
    }
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in result if key != "rows"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
