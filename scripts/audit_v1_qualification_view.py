"""No-call v1 qualification view provenance and tokenizer audit."""

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

from src.pps_ai.ingest.jsonl import load_notice_records
from src.pps_ai.runtime.tokenizer import GemmaTokenCounter
from src.pps_ai.views.native_full_prompt import load_card_texts
from src.pps_ai.views.v1_qualification import (
    build_v1_qualification_view, build_v1_qualification_view_v2,
    build_v1_qualification_task, build_v1_qualification_task_v3,
    build_v1_qualification_axis_task,
    build_v1_bidder_relation_task,
    render_v1_qualification_view,
    OBSERVATION_SCHEMA, SYSTEM_MESSAGE,
)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _csv_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["id"]: row for row in csv.DictReader(handle)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--base-submission", type=Path, required=True)
    parser.add_argument("--cards", type=Path, required=True)
    parser.add_argument("--tokenizer-dir", type=Path, required=True)
    parser.add_argument("--budget", type=int, default=14848)
    parser.add_argument("--view-version", choices=("v1", "v2"), default="v1")
    parser.add_argument("--task-version", choices=("v2", "v3", "v4", "v5"), default="v2")
    parser.add_argument("--review-id", action="append", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    records = load_notice_records(args.input)
    labels = _csv_rows(args.labels)
    base = _csv_rows(args.base_submission)
    ids = {record.notice_id for record in records}
    if set(labels) != ids or set(base) != ids:
        raise ValueError("input/label/base ID mismatch")
    card = load_card_texts(args.cards)["v1"]
    tokenizer = GemmaTokenCounter(args.tokenizer_dir.expanduser())
    tasks: dict[str, dict[str, Any]] = {}
    tokens: dict[str, int] = {}
    coverage: dict[str, Any] = {}
    types: Counter[str] = Counter()
    quote_total = Counter()
    quote_covered = Counter()
    for record in records:
        view = (
            build_v1_qualification_view_v2(record)
            if args.view_version == "v2"
            else build_v1_qualification_view(record)
        )
        task_builder = {
            "v2": build_v1_qualification_task,
            "v3": build_v1_qualification_task_v3,
            "v4": build_v1_qualification_axis_task,
            "v5": build_v1_bidder_relation_task,
        }[args.task_version]
        task = (
            task_builder(record, card, view)
            if view.version == "v2"
            else {
                "id": record.notice_id,
                "arm": "NATIVE_V1_QUALIFICATION_SOURCE_AUDIT_V1",
                "messages": [
                    {"role": "system", "content": SYSTEM_MESSAGE},
                    {"role": "user", "content": (
                        f"[공고] {record.notice_id}\n\n[v1 판정 계약]\n{card}\n\n"
                        f"[모든 제공 문서의 source-grounded 후보]\n"
                        f"{render_v1_qualification_view(view)}"
                    )},
                ],
                "schema": OBSERVATION_SCHEMA,
            }
        )
        tasks[record.notice_id] = task
        tokens[record.notice_id] = tokenizer.count(task["messages"])
        types.update(document.document_type for document in record.documents)
        coverage[record.notice_id] = {
            "documents": list(view.document_coverage),
            "candidate_count": len(view.candidates),
            "source_spans": [
                {
                    "source_id": candidate.source_id,
                    "doc_id": candidate.span.document_id,
                    "start": candidate.span.start,
                    "end": candidate.span.end,
                    "sha256": candidate.span.document_sha256,
                    "categories": candidate.categories,
                }
                for candidate in view.candidates
            ],
        }
        for origin, row in (("gold", labels[record.notice_id]), ("base", base[record.notice_id])):
            quote = row["e1"]
            if not quote:
                continue
            quote_total[origin] += 1
            if any(quote in candidate.span.exact_text for candidate in view.candidates):
                quote_covered[origin] += 1
    fitting = {notice_id: value for notice_id, value in tokens.items() if value <= args.budget}
    overflow = {notice_id: value for notice_id, value in tokens.items() if value > args.budget}
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
            raise ValueError(f"unknown review ID: {notice_id}")
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
        "kind": "zero_call_v1_qualification_input_probe",
        "view_version": args.view_version,
        "task_version": args.task_version,
        "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "labels_sha256": hashlib.sha256(args.labels.read_bytes()).hexdigest(),
        "base_sha256": hashlib.sha256(args.base_submission.read_bytes()).hexdigest(),
        "cards_sha256": hashlib.sha256(args.cards.read_bytes()).hexdigest(),
        "records": len(records),
        "inspected_documents": sum(types.values()),
        "document_types": dict(sorted(types.items())),
        "candidate_spans": sum(row["candidate_count"] for row in coverage.values()),
        "fits_one_call": len(fitting),
        "over_budget": len(overflow),
        "token_min": min(tokens.values()),
        "token_max": max(tokens.values()),
        "gold_e1_nonempty": quote_total["gold"],
        "gold_e1_covered": quote_covered["gold"],
        "base_e1_nonempty": quote_total["base"],
        "base_e1_covered": quote_covered["base"],
        "tokens_by_notice": tokens,
        "task_hashes": {
            notice_id: tokenizer.task_sha256(task)
            for notice_id, task in tasks.items()
        },
        "coverage_by_notice": coverage,
        "rendered_paths": rendered_paths,
        "model_calls": 0,
    }
    _write_json(args.output_dir / "audit.json", report)
    print(json.dumps({key: report[key] for key in (
        "records", "inspected_documents", "candidate_spans", "fits_one_call",
        "over_budget", "token_min", "token_max", "gold_e1_nonempty",
        "gold_e1_covered", "base_e1_nonempty", "base_e1_covered",
        "rendered_paths", "model_calls",
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
