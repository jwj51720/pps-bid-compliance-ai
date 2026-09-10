#!/usr/bin/env python3
"""Prove that a complete-fact candidate actually exposes every supplied fact.

This is a label-blind, no-provider admission audit.  It complements the
three-record semantic review: the latter checks that each *item's meaning* is
present in a rendered message; this audit checks all records and all supplied
source strings are admitted across their exact-token packs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.inspect_prompt import build_pipeline_for_preview
from src.config import load_config
from src.data import load_records
from src.prompt import OFFICIAL_BASELINE_META_FIELDS
from src.prompt import _render_card_text, build_official_baseline_context
from src.schema import ITEMS


def make_token_counter(tokenizer_source: str):
    """Use the same chat-template counting convention as the runner."""
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(tokenizer_source)

    def count(messages: list[dict[str, str]]) -> int:
        encoded = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True
        )
        token_ids = encoded["input_ids"] if isinstance(encoded, Mapping) else encoded
        return len(token_ids)

    return count


def _metadata_marker(field: str, style: str) -> str:
    if style == "official_lines":
        return f"- {field}:"
    return f'"{field}"'


def source_coverage_gaps(record: dict[str, Any], contexts: list[Any]) -> list[dict[str, Any]]:
    """Verify source bytes across packs, including a document split at headers.

    A whole long document cannot be searched as one substring because an
    admitted pack inserts ``[계속 offset]`` headers between its exact source
    fragments.  Parse those headers and prove that their offsets cover each
    original document without a gap or altered payload.
    """
    doc_types = "|".join(re.escape(value) for value in ("공고문", "규격서", "과업지시서", "제안요청서", "예외공표서"))
    header = re.compile(rf"\[({doc_types}):([^\]\n]+)\](?: \[계속 (\d+)\])?\n")
    documents = {document["doc_id"]: document for document in record["docs"]}
    pieces: dict[str, list[tuple[int, str]]] = {doc_id: [] for doc_id in documents}
    for context in contexts:
        text = (
            context.text if hasattr(context, "text")
            else build_official_baseline_context(record, None) if context is None
            else str(context)
        )
        matches = list(header.finditer(text))
        for index, match in enumerate(matches):
            doc_id = match.group(2)
            if doc_id not in documents:
                continue
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            payload = text[match.end():end]
            if index + 1 < len(matches):
                # ``build_official_baseline_context`` and the adaptive packer
                # join adjacent source fragments with this delimiter.  It is
                # transport framing, not a source byte.
                if not payload.endswith("\n\n"):
                    raise ValueError("source framing delimiter is unexpectedly absent")
                payload = payload[:-2]
            # Only pack_contexts_to_token_budget can append this marker after
            # the final supplied source; it is not part of a source document.
            payload = payload.split("\n\n[미수록 문서]", 1)[0]
            pieces[doc_id].append((int(match.group(3) or 0), payload))

    gaps: list[dict[str, Any]] = []
    for doc_id, document in documents.items():
        expected = document["text"]
        cursor = 0
        for offset, payload in sorted(set(pieces[doc_id])):
            if offset != cursor or expected[offset:offset + len(payload)] != payload:
                gaps.append({
                    "doc_id": doc_id,
                    "type": document["type"],
                    "expected_offset": cursor,
                    "observed_offset": offset,
                    "payload_characters": len(payload),
                })
                break
            cursor += len(payload)
        if cursor != len(expected) and not any(gap["doc_id"] == doc_id for gap in gaps):
            gaps.append({
                "doc_id": doc_id,
                "type": document["type"],
                "expected_offset": cursor,
                "observed_offset": None,
                "payload_characters": 0,
            })
    return gaps


def audit(config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    if config.max_document_chars is not None or not config.overflow_split_enabled:
        raise ValueError(
            "complete-fact admission audit requires no character cap and exact-token overflow admission"
        )
    if config.context_strategy != "single":
        raise ValueError("complete-fact admission audit currently requires context_strategy: single")

    pipeline = build_pipeline_for_preview(config)
    pipeline.count_tokens = make_token_counter(config.llm.tokenizer_source or config.llm.model)
    records = load_records(config.data.input_path)
    budget = config.max_model_len - config.output_reserve_tokens
    rows: list[dict[str, Any]] = []
    omitted_documents: Counter[str] = Counter()
    missing_metadata: Counter[str] = Counter()
    over_budget_packs: list[dict[str, Any]] = []
    missing_cards: list[dict[str, Any]] = []

    for record in records:
        effective_pipeline, inactive = pipeline.effective_pipeline_for_record(record)
        contexts = effective_pipeline.contexts_for_record(record)
        rendered = "\n".join(
            "\n".join(
                message["content"]
                for message in effective_pipeline.messages_for_context(record, context)
            )
            for context in contexts
        )
        missing_docs = source_coverage_gaps(record, contexts)
        for document in missing_docs:
            omitted_documents[document["type"]] += 1
        missing_fields = [
            field for field in OFFICIAL_BASELINE_META_FIELDS
            if field in record["meta"] and _metadata_marker(field, config.metadata_style) not in rendered
        ]
        missing_metadata.update(missing_fields)
        pack_tokens = [
            pipeline.count_tokens(effective_pipeline.messages_for_context(record, context))
            for context in contexts
        ]
        if any(tokens > budget for tokens in pack_tokens):
            over_budget_packs.append({"id": record["id"], "pack_tokens": pack_tokens})
        system = effective_pipeline.system_prompt_for_record(record)
        for item in effective_pipeline.active_items:
            if not effective_pipeline._decision_cards:
                missing_cards.append({"id": record["id"], "item": item})
                continue
            source_card = effective_pipeline._decision_cards[item]["prompt_text"]
            rendered_card = (
                _render_card_text(source_card, indent="  ", output_mode=config.output_mode)
                if config.prompt_layout == "markdown_v2" else source_card
            )
            if rendered_card not in system:
                missing_cards.append({"id": record["id"], "item": item})
        rows.append({
            "id": record["id"],
            "source_document_count": len(record["docs"]),
            "pass_count": len(contexts),
            "pack_tokens": pack_tokens,
            "gated_items": inactive,
            "missing_documents": missing_docs,
            "missing_metadata_fields": missing_fields,
        })

    product_items = {f"v{number}" for number in range(10, 19)}
    product_fact_missing = (
        bool(product_items.intersection(config.active_items or ITEMS))
        and config.competition_products_path is None
    )
    result = {
        "experiment_id": config.experiment_id,
        "method": "exact final shared-pipeline messages; no labels or provider calls",
        "tokenizer_source": config.llm.tokenizer_source or config.llm.model,
        "prompt_budget_tokens": budget,
        "record_count": len(rows),
        "total_source_documents": sum(row["source_document_count"] for row in rows),
        "source_document_omission_count": sum(len(row["missing_documents"]) for row in rows),
        "source_document_omissions_by_type": dict(sorted(omitted_documents.items())),
        "metadata_field_omission_count": sum(len(row["missing_metadata_fields"]) for row in rows),
        "metadata_field_omissions": dict(sorted(missing_metadata.items())),
        "missing_active_cards": missing_cards,
        "competition_product_fact_configured": not product_fact_missing,
        "over_budget_packs": over_budget_packs,
        "pass_count_distribution": dict(sorted(Counter(row["pass_count"] for row in rows).items())),
        "rows": rows,
    }
    result["pass"] = not any((
        result["source_document_omission_count"],
        result["metadata_field_omission_count"],
        result["missing_active_cards"],
        not result["competition_product_fact_configured"],
        result["over_budget_packs"],
    ))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = audit(Path(args.config))
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, ensure_ascii=False, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
