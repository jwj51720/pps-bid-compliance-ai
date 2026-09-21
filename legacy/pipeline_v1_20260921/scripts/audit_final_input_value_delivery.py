#!/usr/bin/env python3
"""Verify exact notice facts reach every final prompt that requires them.

This audit is deliberately narrower than legal-card review.  It proves that
the selected card text, each notice's actual human-readable metadata values,
the condition-aware competition-product fact, and every organizer-supplied
document reach the final messages.  It does not claim that a card is legally
complete or that an upstream-unavailable attachment can be reconstructed.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_semantic_input_matrix import parse_contract, required_meta_fields  # noqa: E402
from scripts.audit_complete_fact_admission import source_coverage_gaps  # noqa: E402
from scripts.inspect_prompt import build_pipeline_for_preview  # noqa: E402
from src.config import load_config  # noqa: E402
from src.data import load_records  # noqa: E402
from src.prompt import format_official_baseline_meta  # noqa: E402
from src.schema import ITEMS  # noqa: E402


def _metadata_lines(record: dict[str, Any]) -> dict[str, str]:
    rendered = format_official_baseline_meta(record, human_readable_codes=True)
    return {
        line[2:].split(":", 1)[0]: line
        for line in rendered.splitlines()
        if line.startswith("- ") and ":" in line
    }


def audit(config_path: Path, contract_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    if config.metadata_style != "official_lines_human_v2":
        raise ValueError("value-delivery audit requires official_lines_human_v2")
    if config.staged_run and config.staged_run.mode not in {"off", None}:
        raise ValueError("audit a direct/full-final config, not an intermediate staged message")

    contract = parse_contract(contract_path)
    records = load_records(config.data.input_path)
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        config.llm.tokenizer_source or config.llm.model
    )

    def count_tokens(messages: list[dict[str, str]]) -> int:
        encoded = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True
        )
        token_ids = encoded["input_ids"] if isinstance(encoded, Mapping) else encoded
        return len(token_ids)

    pipeline = build_pipeline_for_preview(config, count_tokens=count_tokens)
    active_items = tuple(config.active_items or ITEMS)
    required_fields = sorted({
        field
        for item in active_items
        for field in required_meta_fields(contract[item]["required_facts"])
    })
    csv_items = tuple(
        item for item in active_items if "CSV" in contract[item]["required_facts"]
    )

    failures: list[dict[str, Any]] = []
    context_count = 0
    pass_histogram: Counter[int] = Counter()
    supplied_documents = 0
    upstream_unavailable_documents = 0
    upstream_incomplete_records = 0
    metadata_missing_values: Counter[str] = Counter()

    for record in records:
        effective, inactive = pipeline.effective_pipeline_for_record(record)
        if inactive:
            failures.append({
                "id": record["id"],
                "kind": "unexpected_applicability_gate",
                "detail": inactive,
            })
        contexts = effective.contexts_for_record(record)
        pass_histogram[len(contexts)] += 1
        context_count += len(contexts)
        messages = [effective.messages_for_context(record, context) for context in contexts]
        systems = [message[0]["content"] for message in messages]
        users = [message[1]["content"] for message in messages]
        aggregate_user = "\n".join(users)

        for item in active_items:
            card_text = effective._decision_cards[item]["prompt_text"]
            if any(card_text not in system for system in systems):
                failures.append({
                    "id": record["id"], "kind": "card_missing", "item": item,
                })

        metadata_lines = _metadata_lines(record)
        for field in required_fields:
            expected = metadata_lines.get(field)
            if expected is None:
                failures.append({
                    "id": record["id"], "kind": "metadata_field_not_renderable", "field": field,
                })
                continue
            if expected.endswith(": 미기재"):
                metadata_missing_values[field] += 1
            if any(expected not in user for user in users):
                failures.append({
                    "id": record["id"], "kind": "metadata_value_missing", "field": field,
                    "expected": expected,
                })

        if csv_items:
            expected_product = effective.competition_product_context_for_record(record)
            if not expected_product:
                failures.append({
                    "id": record["id"], "kind": "product_fact_not_renderable",
                    "items": list(csv_items),
                })
            elif any(expected_product not in user for user in users):
                failures.append({
                    "id": record["id"], "kind": "product_fact_missing",
                    "items": list(csv_items),
                })

        supplied_documents += len(record["docs"])
        for gap in source_coverage_gaps(record, contexts):
            failures.append({
                "id": record["id"], "kind": "supplied_document_missing", **gap,
            })

        unavailable = record.get("dropped_doc_counts") or {}
        unavailable_count = sum(int(value) for value in unavailable.values())
        upstream_unavailable_documents += unavailable_count
        if unavailable_count:
            upstream_incomplete_records += 1
            for document_type, count in unavailable.items():
                marker = f"{document_type} {count}건"
                if marker not in aggregate_user:
                    failures.append({
                        "id": record["id"], "kind": "upstream_unavailable_marker_missing",
                        "type": document_type, "count": count,
                    })

    return {
        "audit_version": 1,
        "config": str(config_path),
        "contract": str(contract_path),
        "record_count": len(records),
        "final_context_count": context_count,
        "tokenizer_source": config.llm.tokenizer_source or config.llm.model,
        "prompt_budget_tokens": config.max_model_len - config.output_reserve_tokens,
        "pass_histogram": {str(key): value for key, value in sorted(pass_histogram.items())},
        "active_items": list(active_items),
        "required_metadata_fields": required_fields,
        "metadata_missing_value_counts": dict(sorted(metadata_missing_values.items())),
        "supplied_document_count": supplied_documents,
        "upstream_incomplete_record_count": upstream_incomplete_records,
        "upstream_unavailable_document_count": upstream_unavailable_documents,
        "provider_called": False,
        "labels_or_predictions_read": False,
        "passed": not failures,
        "failure_count": len(failures),
        "failures": failures,
        "scope_note": (
            "PASS proves exact delivery of selected cards, actual rendered metadata values, "
            "condition-aware product facts, and organizer-supplied documents. It does not prove "
            "legal-card completeness or recover upstream-unavailable documents."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--contract", type=Path, default=ROOT / "docs/semantic_input_contract_v1.md"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.config, args.contract)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: report[key] for key in (
        "passed", "record_count", "final_context_count", "pass_histogram",
        "supplied_document_count", "upstream_incomplete_record_count",
        "upstream_unavailable_document_count", "metadata_missing_value_counts",
        "failure_count",
    )}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
