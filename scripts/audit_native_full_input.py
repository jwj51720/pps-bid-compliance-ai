"""No-call exact-token feasibility audit for the independent full-source prompt."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai.facts.product_codes import load_product_index
from src.pps_ai.ingest.jsonl import load_notice_records
from src.pps_ai.runtime.tokenizer import GemmaTokenCounter
from src.pps_ai.views.native_full_prompt import (
    build_native_full_task, load_card_texts,
)


def _p95(values: list[int]) -> int:
    ordered = sorted(values)
    return ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)]


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--cards", type=Path, required=True)
    parser.add_argument("--products", type=Path, required=True)
    parser.add_argument("--tokenizer-dir", type=Path, required=True)
    parser.add_argument("--budget", type=int, default=14848)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.budget < 1:
        raise ValueError("positive prompt budget required")

    records = load_notice_records(args.input)
    cards = load_card_texts(args.cards)
    products = load_product_index(args.products)
    counter = GemmaTokenCounter(args.tokenizer_dir.expanduser())
    tasks: dict[str, dict[str, Any]] = {}
    tokens: dict[str, int] = {}
    document_types: Counter[str] = Counter()
    document_ledger: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        task = build_native_full_task(record, cards, products)
        tasks[record.notice_id] = task
        tokens[record.notice_id] = counter.count(task["messages"])
        document_ledger[record.notice_id] = [
            {
                "doc_id": document.doc_id, "type": document.document_type,
                "order": document.order, "characters": len(document.text),
                "sha256": document.sha256,
            }
            for document in record.documents
        ]
        document_types.update(document.document_type for document in record.documents)

    fitting = {key: value for key, value in tokens.items() if value <= args.budget}
    overflow = {key: value for key, value in tokens.items() if value > args.budget}
    attachment_fit = {
        record.notice_id: tokens[record.notice_id] for record in records
        if len(record.documents) > 1 and record.notice_id in fitting
    }
    selections = {
        "short_complete": min(fitting, key=fitting.get) if fitting else None,
        "attachment_complete": min(attachment_fit, key=attachment_fit.get)
        if attachment_fit else None,
        "largest": max(tokens, key=tokens.get),
        "overflow": max(overflow, key=overflow.get) if overflow else None,
    }
    rendered_paths: dict[str, str] = {}
    for role, notice_id in selections.items():
        if notice_id is None:
            continue
        path = args.output_dir / "rendered_inputs" / f"{role}_{notice_id}.json"
        _write_json(path, {
            "id": notice_id, "role": role, "prompt_tokens": tokens[notice_id],
            "budget": args.budget, "task": tasks[notice_id],
        })
        rendered_paths[role] = str(path)

    report = {
        "kind": "zero_call_input_feasibility_only",
        "input": str(args.input),
        "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "cards": str(args.cards),
        "cards_sha256": hashlib.sha256(args.cards.read_bytes()).hexdigest(),
        "products": str(args.products),
        "products_sha256": hashlib.sha256(args.products.read_bytes()).hexdigest(),
        "records": len(records),
        "all_source_documents": sum(document_types.values()),
        "document_types": dict(sorted(document_types.items())),
        "rendered_source_documents": sum(len(row) for row in document_ledger.values()),
        "card_items": len(cards),
        "prompt_budget": args.budget,
        "fits_one_call": len(fitting),
        "over_budget": len(overflow),
        "token_min": min(tokens.values()),
        "token_p95": _p95(list(tokens.values())),
        "token_max": max(tokens.values()),
        "token_sum": sum(tokens.values()),
        "max_excess_tokens": max((value - args.budget for value in overflow.values()), default=0),
        "task_hashes": {
            notice_id: counter.task_sha256(task)
            for notice_id, task in tasks.items()
        },
        "tokens_by_notice": tokens,
        "source_ledger": document_ledger,
        "rendered_paths": rendered_paths,
        "model_calls": 0,
    }
    _write_json(args.output_dir / "audit.json", report)
    print(json.dumps({
        key: report[key] for key in (
            "records", "all_source_documents", "card_items", "prompt_budget",
            "fits_one_call", "over_budget", "token_min", "token_p95",
            "token_max", "token_sum", "max_excess_tokens", "rendered_paths",
        )
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
