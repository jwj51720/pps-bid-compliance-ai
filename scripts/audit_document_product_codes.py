"""Zero-call exact-code audit across all organizer notice documents."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai.facts.document_product_codes import (
    collect_document_product_mentions, render_document_product_mentions,
)
from src.pps_ai.facts.product_codes import (
    load_product_index, parse_supplied_product_codes,
)
from src.pps_ai.ingest.jsonl import load_notice_records
from src.pps_ai.runtime.tokenizer import GemmaTokenCounter


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--products", type=Path, required=True)
    parser.add_argument("--tokenizer-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    records = load_notice_records(args.input)
    product_index = load_product_index(args.products)
    counter = GemmaTokenCounter(args.tokenizer_dir.expanduser())
    document_types: Counter[str] = Counter()
    mention_types: Counter[str] = Counter()
    matched_types: Counter[str] = Counter()
    mention_total = 0
    matched_total = 0
    matched_with_note = 0
    document_only_matched: set[tuple[str, str]] = set()
    metadata_matched: set[tuple[str, str]] = set()
    tokens: list[int] = []
    by_notice: dict[str, dict[str, object]] = {}
    for record in records:
        document_types.update(document.document_type for document in record.documents)
        metadata_codes = {
            code for code, _ in parse_supplied_product_codes(
                record.metadata.get("세부품명번호목록")
            )
        }
        metadata_matched.update(
            (record.notice_id, code)
            for code in metadata_codes if code in product_index
        )
        mentions = collect_document_product_mentions(record, product_index)
        mention_total += len(mentions)
        mention_types.update(mention.code_span.document_type for mention in mentions)
        matched = [mention for mention in mentions if mention.csv_name is not None]
        matched_total += len(matched)
        matched_with_note += sum(bool(mention.special_note) for mention in matched)
        matched_types.update(mention.code_span.document_type for mention in matched)
        for mention in matched:
            if mention.code not in metadata_codes:
                document_only_matched.add((record.notice_id, mention.code))
        token_count = counter.count([{
            "role": "user", "content": render_document_product_mentions(mentions),
        }])
        tokens.append(token_count)
        by_notice[record.notice_id] = {
            "documents": len(record.documents),
            "mentions": len(mentions),
            "csv_matched_mentions": len(matched),
            "document_only_matched_codes": sorted({
                mention.code for mention in matched
                if mention.code not in metadata_codes
            }),
            "all_mention_render_tokens": token_count,
        }
    report = {
        "kind": "zero_call_document_product_fact_audit",
        "records": len(records),
        "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "products_sha256": hashlib.sha256(args.products.read_bytes()).hexdigest(),
        "all_documents": sum(document_types.values()),
        "document_types": dict(sorted(document_types.items())),
        "document_code_mentions": mention_total,
        "document_code_mentions_by_type": dict(sorted(mention_types.items())),
        "csv_matched_document_mentions": matched_total,
        "csv_matched_mentions_by_type": dict(sorted(matched_types.items())),
        "csv_matched_mentions_with_special_note": matched_with_note,
        "distinct_metadata_matched_notice_codes": len(metadata_matched),
        "distinct_document_only_matched_notice_codes": len(document_only_matched),
        "document_only_matched_notice_codes": [
            {"id": notice_id, "code": code}
            for notice_id, code in sorted(document_only_matched)
        ],
        "all_mention_render_token_min": min(tokens),
        "all_mention_render_token_max": max(tokens),
        "all_mention_render_token_sum": sum(tokens),
        "by_notice": by_notice,
        "model_calls": 0,
        "product_applicability_labels_assigned": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        key: report[key] for key in (
            "records", "all_documents", "document_code_mentions",
            "csv_matched_document_mentions",
            "csv_matched_mentions_with_special_note",
            "distinct_metadata_matched_notice_codes",
            "distinct_document_only_matched_notice_codes",
            "all_mention_render_token_max", "model_calls",
        )
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
