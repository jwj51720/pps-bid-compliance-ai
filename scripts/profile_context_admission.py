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


def _token_counter(tokenizer):
    def count(messages: list[dict[str, str]]) -> int:
        encoded = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True
        )
        token_ids = encoded["input_ids"] if isinstance(encoded, Mapping) else encoded
        return len(token_ids)

    return count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
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
    pipeline = BaselinePipeline(
        item_table=item_table,
        client=None,
        max_document_chars=config.max_document_chars,
        prompt_mode=config.prompt_mode,
        include_normalized_facts=config.include_normalized_facts,
        context_strategy=config.context_strategy,
        notice_anchor_chars=config.notice_anchor_chars,
        overflow_split_enabled=config.overflow_split_enabled,
        strict_document_evidence=config.strict_document_evidence,
        absence_detection_strategy=config.absence_detection_strategy,
        decision_cards=cards,
        competition_products=products,
        competition_product_context_mode=config.competition_product_context_mode,
        count_tokens=count_tokens,
        prompt_budget_tokens=config.max_model_len - config.output_reserve_tokens,
        active_items=config.active_items,
        prompt_layout=config.prompt_layout,
        prompt_profile=config.prompt_profile,
        role_directive=config.role_directive,
        item_catalog_style=config.item_catalog_style,
        metadata_style=config.metadata_style,
        output_mode=config.output_mode,
        visible_document_types=config.visible_document_types,
    )
    budget = config.max_model_len - config.output_reserve_tokens
    records = load_records(config.data.input_path)
    if config.data.fast_panel_ids_path:
        records = select_records_by_id(
            records, load_record_id_panel(config.data.fast_panel_ids_path)
        )
    elif config.local_limit is not None:
        records = records[:config.local_limit]
    rows = []
    for record in records:
        full_tokens = count_tokens(pipeline.messages_for_context(record, None))
        contexts = pipeline.contexts_for_record(record)
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
    result = {
        "experiment_id": config.experiment_id,
        "method": "Gemma tokenizer.apply_chat_template on final shared-pipeline messages",
        "tokenizer_source": config.llm.tokenizer_source or config.llm.model,
        "prompt_budget_tokens": budget,
        "record_count": len(rows),
        "one_pass_count": sum(row["fits_one_pass"] for row in rows),
        "overflow_count": sum(not row["fits_one_pass"] for row in rows),
        "call_count": sum(row["pass_count"] for row in rows),
        "pass_count_distribution": dict(
            sorted(Counter(row["pass_count"] for row in rows).items())
        ),
        "largest_rows": rows[:20],
        "rows": rows,
    }
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in result if key != "rows"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
