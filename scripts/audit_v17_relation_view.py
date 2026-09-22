"""No-call v17 relation-view coverage and exact-token admission audit."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
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
    build_v17_relation_task, eligible_v17_full_source,
)
from src.pps_ai.views.v17_relation_view import (
    build_v17_relation_view, build_v17_relation_view_v2,
    build_v17_relation_view_v3,
)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["id"]: row for row in csv.DictReader(handle)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--base-submission", type=Path, required=True)
    parser.add_argument("--cards", type=Path, required=True)
    parser.add_argument("--products", type=Path, required=True)
    parser.add_argument("--tokenizer-dir", type=Path, required=True)
    parser.add_argument("--budget", type=int, default=14848)
    parser.add_argument("--view-version", choices=("v1", "v2", "v3"), default="v1")
    parser.add_argument("--review-id", action="append", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    records = load_notice_records(args.input)
    labels = _rows(args.labels)
    base = _rows(args.base_submission)
    if set(labels) != set(base) or set(base) != {record.notice_id for record in records}:
        raise ValueError("input/label/base ID mismatch")
    card = load_card_texts(args.cards)["v17"]
    product_index = load_product_index(args.products)
    tokenizer = GemmaTokenCounter(args.tokenizer_dir.expanduser())
    tasks: dict[str, dict[str, Any]] = {}
    tokens: dict[str, int] = {}
    notice_views: dict[str, Any] = {}
    types: Counter[str] = Counter()
    gold_evidence = 0
    gold_covered = 0
    base_evidence = 0
    base_covered = 0
    misses: list[dict[str, str]] = []
    for record in records:
        if not eligible_v17_full_source(record):
            continue
        view_builder = {
            "v1": build_v17_relation_view,
            "v2": build_v17_relation_view_v2,
            "v3": build_v17_relation_view_v3,
        }[args.view_version]
        view = view_builder(record)
        task = build_v17_relation_task(record, card, product_index, view)
        notice_id = record.notice_id
        tasks[notice_id] = task
        tokens[notice_id] = tokenizer.count(task["messages"])
        types.update(document.document_type for document in record.documents)
        notice_views[notice_id] = {
            "documents": list(view.document_coverage),
            "candidate_count": len(view.candidates),
            "source_spans": [
                {"source_id": candidate.source_id,
                 "doc_id": candidate.span.document_id,
                 "type": candidate.span.document_type,
                 "start": candidate.span.start,
                 "end": candidate.span.end,
                 "sha256": candidate.span.document_sha256,
                 "categories": candidate.categories}
                for candidate in view.candidates
            ],
        }
        for origin, row in (("gold", labels[notice_id]), ("base", base[notice_id])):
            evidence = row["e17"]
            if not evidence:
                continue
            if origin == "gold":
                gold_evidence += 1
            else:
                base_evidence += 1
            if any(evidence in candidate.span.exact_text for candidate in view.candidates):
                if origin == "gold":
                    gold_covered += 1
                else:
                    base_covered += 1
            else:
                misses.append({"id": notice_id, "origin": origin})
    fitting = {notice_id: value for notice_id, value in tokens.items()
               if value <= args.budget}
    overflow = {notice_id: value for notice_id, value in tokens.items()
                if value > args.budget}
    record_map = {record.notice_id: record for record in records}
    attachment_fit = {notice_id: value for notice_id, value in fitting.items()
                      if len(record_map[notice_id].documents) > 1}
    samples = {
        "short_complete": min(fitting, key=fitting.get) if fitting else None,
        "attachment_complete": min(attachment_fit, key=attachment_fit.get)
        if attachment_fit else None,
        "largest": max(tokens, key=tokens.get),
        "overflow": max(overflow, key=overflow.get) if overflow else None,
    }
    for notice_id in args.review_id:
        if notice_id not in tasks:
            raise ValueError(f"review ID does not have an eligible v17 task: {notice_id}")
        samples[f"review_{notice_id}"] = notice_id
    rendered_paths: dict[str, str] = {}
    for role, notice_id in samples.items():
        if notice_id is None:
            continue
        path = args.output_dir / "rendered_inputs" / f"{role}_{notice_id}.json"
        _write_json(path, {
            "id": notice_id, "role": role, "tokens": tokens[notice_id],
            "budget": args.budget, "task": tasks[notice_id],
        })
        rendered_paths[role] = str(path)
    report = {
        "kind": "zero_call_v17_relation_view_probe",
        "view_version": args.view_version,
        "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "labels_sha256": hashlib.sha256(args.labels.read_bytes()).hexdigest(),
        "base_sha256": hashlib.sha256(args.base_submission.read_bytes()).hexdigest(),
        "cards_sha256": hashlib.sha256(args.cards.read_bytes()).hexdigest(),
        "products_sha256": hashlib.sha256(args.products.read_bytes()).hexdigest(),
        "records": len(records),
        "eligible_tasks": len(tasks),
        "inspected_documents": sum(types.values()),
        "document_types": dict(sorted(types.items())),
        "candidate_spans": sum(row["candidate_count"] for row in notice_views.values()),
        "fits_one_call": len(fitting),
        "over_budget": len(overflow),
        "token_min": min(tokens.values()),
        "token_max": max(tokens.values()),
        "token_sum": sum(tokens.values()),
        "gold_nonempty_e17": gold_evidence,
        "gold_e17_covered": gold_covered,
        "base_nonempty_e17": base_evidence,
        "base_e17_covered": base_covered,
        "evidence_misses": misses,
        "tokens_by_notice": tokens,
        "task_hashes": {notice_id: tokenizer.task_sha256(task)
                        for notice_id, task in tasks.items()},
        "views_by_notice": notice_views,
        "rendered_paths": rendered_paths,
        "model_calls": 0,
    }
    _write_json(args.output_dir / "audit.json", report)
    print(json.dumps({
        key: report[key] for key in (
            "records", "eligible_tasks", "inspected_documents", "candidate_spans",
            "fits_one_call", "over_budget", "token_min", "token_max",
            "gold_nonempty_e17", "gold_e17_covered",
            "base_nonempty_e17", "base_e17_covered", "rendered_paths", "model_calls",
        )
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
