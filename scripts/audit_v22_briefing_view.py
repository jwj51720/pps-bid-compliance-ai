#!/usr/bin/env python3
"""No-call v22 source provenance, evidence coverage, and tokenizer audit."""

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
from src.pps_ai.runtime.openrouter import atomic_json
from src.pps_ai.runtime.tokenizer import GemmaTokenCounter
from src.pps_ai.views.native_full_prompt import load_card_texts
from src.pps_ai.views.v22_briefing import (
    build_v22_briefing_task, build_v22_briefing_view, build_v22_phase_task,
)


def _csv_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["id"]: row for row in csv.DictReader(handle)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--cards", type=Path, required=True)
    parser.add_argument("--tokenizer-dir", type=Path, required=True)
    parser.add_argument("--budget", type=int, default=14848)
    parser.add_argument("--task-version", choices=("v1", "v2"), default="v1")
    parser.add_argument("--review-id", action="append", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    records = load_notice_records(args.input)
    labels = _csv_rows(args.labels)
    ids = {record.notice_id for record in records}
    if set(labels) != ids:
        raise ValueError("input/label ID mismatch")
    card = load_card_texts(args.cards)["v22"]
    tokenizer = GemmaTokenCounter(args.tokenizer_dir.expanduser())
    tasks: dict[str, dict[str, Any]] = {}
    views = {}
    tokens: dict[str, int] = {}
    document_types: Counter[str] = Counter()
    evidence_total = 0
    evidence_covered = 0
    for record in records:
        view = build_v22_briefing_view(record)
        task_builder = (
            build_v22_phase_task if args.task_version == "v2"
            else build_v22_briefing_task
        )
        task = task_builder(record, card, view)
        tasks[record.notice_id] = task
        views[record.notice_id] = view
        tokens[record.notice_id] = tokenizer.count(task["messages"])
        document_types.update(document.document_type for document in record.documents)
        evidence = labels[record.notice_id]["e22"]
        if evidence:
            evidence_total += 1
            if any(evidence in candidate.span.exact_text for candidate in view.candidates):
                evidence_covered += 1

    fitting = {notice_id: value for notice_id, value in tokens.items()
               if value <= args.budget}
    overflow = {notice_id: value for notice_id, value in tokens.items()
                if value > args.budget}
    attachment = {notice_id: value for notice_id, value in fitting.items()
                  if len(views[notice_id].document_coverage) > 1}
    samples = {
        "short_complete": min(fitting, key=fitting.get) if fitting else None,
        "attachment_complete": min(attachment, key=attachment.get) if attachment else None,
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
        atomic_json(path, {
            "id": notice_id, "role": role, "tokens": tokens[notice_id],
            "budget": args.budget, "task": tasks[notice_id],
            "document_coverage": list(views[notice_id].document_coverage),
        })
        rendered_paths[role] = str(path)

    report = {
        "kind": "zero_call_v22_briefing_input_probe",
        "view_version": "v1",
        "task_version": args.task_version,
        "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "labels_sha256": hashlib.sha256(args.labels.read_bytes()).hexdigest(),
        "cards_sha256": hashlib.sha256(args.cards.read_bytes()).hexdigest(),
        "records": len(records),
        "inspected_documents": sum(document_types.values()),
        "document_types": dict(sorted(document_types.items())),
        "candidate_spans": sum(len(view.candidates) for view in views.values()),
        "fits_one_call": len(fitting),
        "over_budget": len(overflow),
        "token_min": min(tokens.values()),
        "token_max": max(tokens.values()),
        "gold_e22_nonempty": evidence_total,
        "gold_e22_covered": evidence_covered,
        "tokens_by_notice": tokens,
        "task_hashes": {
            notice_id: tokenizer.task_sha256(task)
            for notice_id, task in tasks.items()
        },
        "coverage_by_notice": {
            notice_id: {
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
            for notice_id, view in views.items()
        },
        "rendered_paths": rendered_paths,
        "model_calls": 0,
    }
    atomic_json(args.output_dir / "audit.json", report)
    print(json.dumps({key: report[key] for key in (
        "records", "inspected_documents", "candidate_spans", "fits_one_call",
        "over_budget", "token_min", "token_max", "gold_e22_nonempty",
        "gold_e22_covered", "rendered_paths", "model_calls",
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
