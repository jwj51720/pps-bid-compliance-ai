"""Zero-call V17 full-source admission and provenance audit."""

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
from src.pps_ai.views.native_full_prompt import load_card_texts
from src.pps_ai.views.v17_full_source import (
    build_v17_full_source_task, eligible_v17_full_source,
)


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

    records = load_notice_records(args.input)
    card = load_card_texts(args.cards)["v17"]
    products = load_product_index(args.products)
    tokenizer = GemmaTokenCounter(args.tokenizer_dir.expanduser())
    tasks: dict[str, dict[str, Any]] = {}
    tokens: dict[str, int] = {}
    document_types: Counter[str] = Counter()
    for record in records:
        if not eligible_v17_full_source(record):
            continue
        task = build_v17_full_source_task(record, card, products)
        tasks[record.notice_id] = task
        tokens[record.notice_id] = tokenizer.count(task["messages"])
        document_types.update(document.document_type for document in record.documents)
    fitting = {notice_id: count for notice_id, count in tokens.items()
               if count <= args.budget}
    overflow = {notice_id: count for notice_id, count in tokens.items()
                if count > args.budget}
    record_map = {record.notice_id: record for record in records}
    attachment_fit = {notice_id: count for notice_id, count in fitting.items()
                      if len(record_map[notice_id].documents) > 1}
    selections = {
        "short_complete": min(fitting, key=fitting.get) if fitting else None,
        "attachment_complete": min(attachment_fit, key=attachment_fit.get)
        if attachment_fit else None,
        "overflow": max(overflow, key=overflow.get) if overflow else None,
    }
    rendered_paths: dict[str, str] = {}
    for role, notice_id in selections.items():
        if notice_id is None:
            continue
        path = args.output_dir / "rendered_inputs" / f"{role}_{notice_id}.json"
        _write_json(path, {
            "role": role, "id": notice_id, "tokens": tokens[notice_id],
            "budget": args.budget, "task": tasks[notice_id],
        })
        rendered_paths[role] = str(path)
    report = {
        "kind": "zero_call_v17_full_source_admission",
        "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "cards_sha256": hashlib.sha256(args.cards.read_bytes()).hexdigest(),
        "products_sha256": hashlib.sha256(args.products.read_bytes()).hexdigest(),
        "records": len(records),
        "eligible_notice_tasks": len(tasks),
        "eligible_source_documents": sum(document_types.values()),
        "eligible_document_types": dict(sorted(document_types.items())),
        "fits_one_call": len(fitting),
        "over_budget": len(overflow),
        "token_min": min(tokens.values()),
        "token_max": max(tokens.values()),
        "token_sum": sum(tokens.values()),
        "tokens_by_notice": tokens,
        "task_hashes": {notice_id: tokenizer.task_sha256(task)
                        for notice_id, task in tasks.items()},
        "rendered_paths": rendered_paths,
        "model_calls": 0,
    }
    _write_json(args.output_dir / "audit.json", report)
    print(json.dumps({
        key: report[key] for key in (
            "records", "eligible_notice_tasks", "eligible_source_documents",
            "fits_one_call", "over_budget", "token_min", "token_max",
            "token_sum", "rendered_paths", "model_calls",
        )
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
