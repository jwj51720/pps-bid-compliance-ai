#!/usr/bin/env python3
"""Export every exact group message for one notice without provider calls."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.inspect_prompt import _request_preview
from scripts.run_grouped_experiment import (
    _group_competition_products,
    _group_context_policy,
    _group_decision_cards,
    _group_prompt_profiles,
)
from src.config import load_config
from src.data import (
    load_competition_product_index,
    load_decision_cards,
    load_item_table,
    load_record_id_panel,
    load_records,
    select_records_by_id,
)
from src.law_bundles import FourProfileGroupLawBundleRouter, MetadataLawBundleRouter
from src.legal_groups import groups_for_scheme
from src.pipeline import BaselinePipeline


def _exact_counter(tokenizer_source: str):
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(tokenizer_source)

    def count(messages: list[dict[str, str]]) -> int:
        encoded = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True
        )
        token_ids = encoded["input_ids"] if isinstance(encoded, Mapping) else encoded
        return len(token_ids)

    return count


def build_grouped_previews(
    config: Any,
    record: dict[str, Any],
    token_counter: Any | None = None,
) -> list[dict[str, Any]]:
    """Mirror grouped execution's pipeline construction for one exact record."""
    grouped_run = config.raw.get("grouped_run", {})
    if not isinstance(grouped_run, dict):
        raise ValueError("grouped_run must be a mapping")
    grouping = str(grouped_run.get("grouping", "law_overlap_12"))
    reference_mode = str(grouped_run.get("reference_mode", "group_bundle"))
    reference_navigation = str(grouped_run.get("reference_navigation", "per_item"))
    if reference_mode not in {"none", "group_bundle"}:
        raise ValueError("invalid grouped_run.reference_mode")
    if reference_navigation not in {"none", "per_item"}:
        raise ValueError("invalid grouped_run.reference_navigation")
    item_groups = groups_for_scheme(grouping)
    prompt_profiles = _group_prompt_profiles(config, grouped_run, item_groups)
    policies = {
        group.group_id: _group_context_policy(config, grouped_run, group.group_id, group.items)
        for group in item_groups
    }
    item_table = load_item_table(config.data.item_table_path)
    cards_by_group, _ = _group_decision_cards(
        config, grouped_run, item_groups, item_table
    )
    products_by_group, _ = _group_competition_products(config, grouped_run, item_groups)
    router = None
    if reference_mode == "group_bundle":
        if not config.reference_bundle_dir:
            raise ValueError("group_bundle requires prompt.reference_bundle_dir")
        router = (
            FourProfileGroupLawBundleRouter(config.reference_bundle_dir)
            if config.reference_routing == "metadata_profile_group_v2"
            else MetadataLawBundleRouter(config.reference_bundle_dir)
        )
    token_counter = token_counter or _exact_counter(
        config.llm.tokenizer_source or config.llm.model
    )
    route = router.route(record) if router else None
    previews: list[dict[str, Any]] = []
    for group in item_groups:
        reference_text = None
        if router:
            reference_text = router.group_bundle(record, group.group_id).reference_text
        policy = policies[group.group_id]
        pipeline = BaselinePipeline(
            item_table=item_table,
            client=None,
            max_document_chars=policy["max_document_chars"],
            prompt_mode=config.prompt_mode,
            include_normalized_facts=config.include_normalized_facts,
            context_strategy=policy["context_strategy"],
            notice_anchor_chars=config.notice_anchor_chars,
            overflow_split_enabled=policy["overflow_split_enabled"],
            strict_document_evidence=config.strict_document_evidence,
            absence_detection_strategy=policy["absence_detection_strategy"],
            decision_cards=cards_by_group[group.group_id],
            competition_products=products_by_group[group.group_id],
            competition_product_context_mode=config.competition_product_context_mode,
            organizer_input_semantics_mode=config.organizer_input_semantics_mode,
            count_tokens=token_counter,
            prompt_budget_tokens=config.max_model_len - config.output_reserve_tokens,
            reference_text=reference_text,
            active_items=group.items,
            prompt_layout=config.prompt_layout,
            prompt_profile=prompt_profiles[group.group_id],
            role_directive=config.role_directive,
            item_catalog_style=config.item_catalog_style,
            metadata_style=config.metadata_style,
            output_mode=config.output_mode,
            visible_document_types=config.visible_document_types,
            v8_composite_merge_enabled=config.v8_composite_merge_enabled,
            v8_composite_merge_mode=config.v8_composite_merge_mode,
        )
        for pass_index, context in enumerate(pipeline.contexts_for_record(record), 1):
            messages = pipeline.messages_for_context(record, context)
            previews.append(
                {
                    "group": group.group_id,
                    "items": list(group.items),
                    "pass_index": pass_index,
                    "context_policy": policy,
                    "route_profile": route.profile if route else None,
                    "prompt_profile": prompt_profiles[group.group_id],
                    "token_count": token_counter(messages),
                    "messages": messages,
                    "response_schema": pipeline.response_schema,
                }
            )
    return previews


def _markdown(record_id: str, config: Any, previews: list[dict[str, Any]]) -> str:
    lines = [f"# Grouped Actual LLM Input: {record_id}", ""]
    for preview in previews:
        lines.extend(
            [
                f"## {preview['group']} — {', '.join(preview['items'])} — context {preview['pass_index']}",
                "",
                f"- Tokenizer input tokens: `{preview['token_count']}`",
                f"- Context policy: `{json.dumps(preview['context_policy'], ensure_ascii=False, sort_keys=True)}`",
                f"- Prompt profile: `{preview['prompt_profile']}`",
                "",
                "### System Message",
                "",
                "```text",
                preview["messages"][0]["content"],
                "```",
                "",
                "### User Message",
                "",
                "```text",
                preview["messages"][1]["content"],
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--record-id")
    selection.add_argument("--ids-file", help="JSON list or panel manifest")
    selection.add_argument("--all-records", action="store_true")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    records = load_records(config.data.input_path)
    if args.all_records:
        selected = records
    elif args.ids_file:
        selected = select_records_by_id(records, load_record_id_panel(args.ids_file))
    else:
        selected = [row for row in records if row["id"] == args.record_id]
        if not selected:
            raise ValueError(f"record not found: {args.record_id}")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    token_counter = _exact_counter(config.llm.tokenizer_source or config.llm.model)
    summary_rows: list[dict[str, Any]] = []
    for record in selected:
        previews = build_grouped_previews(config, record, token_counter)
        stem = record["id"].lower()
        request_rows = [
            {
                "group": preview["group"],
                "items": preview["items"],
                "pass_index": preview["pass_index"],
                "token_count": preview["token_count"],
                "request": _request_preview(config, preview["messages"], preview["response_schema"]),
            }
            for preview in previews
        ]
        (output_dir / f"{stem}.grouped.request.json").write_text(
            json.dumps(request_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (output_dir / f"{stem}.grouped.messages.md").write_text(
            _markdown(record["id"], config, previews), encoding="utf-8"
        )
        summary_rows.extend(
            {
                "id": record["id"], "group": preview["group"],
                "pass_index": preview["pass_index"], "token_count": preview["token_count"],
            }
            for preview in previews
        )
        print(output_dir / f"{stem}.grouped.messages.md")
    if args.ids_file or args.all_records:
        summary = {
            "record_count": len(selected),
            "call_count": len(summary_rows),
            "max_input_tokens": max(row["token_count"] for row in summary_rows),
            "rows": summary_rows,
        }
        (output_dir / "admission.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(output_dir / "admission.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
