#!/usr/bin/env python3
"""No-call v2 all-document source-view coverage and token-headroom audit."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai.facts.metadata import build_metadata_facts, render_metadata_facts
from src.pps_ai.ingest.jsonl import load_notice_records
from src.pps_ai.runtime.openrouter import atomic_json
from src.pps_ai.runtime.tokenizer import GemmaTokenCounter
from src.pps_ai.views.native_full_prompt import load_card_texts
from src.pps_ai.views.v2_performance import (
    build_v2_performance_task, build_v2_performance_task_v2,
    build_v2_performance_view,
    build_v2_performance_view_v2,
    render_v2_performance_view,
)


TASK_CONTRACT_RESERVE = 1200


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
    parser.add_argument("--view-version", choices=("v1", "v2"), default="v1")
    parser.add_argument("--actual-task", action="store_true")
    parser.add_argument("--task-version", choices=("v1", "v2"), default="v1")
    parser.add_argument("--review-id", action="append", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    records = load_notice_records(args.input)
    labels = _csv_rows(args.labels)
    if set(labels) != {record.notice_id for record in records}:
        raise ValueError("input/label ID mismatch")
    card = load_card_texts(args.cards)["v2"]
    tokenizer = GemmaTokenCounter(args.tokenizer_dir.expanduser())
    views = {}
    envelopes = {}
    tasks = {}
    tokens = {}
    document_types: Counter[str] = Counter()
    evidence_total = 0
    evidence_covered = 0
    for record in records:
        view = (
            build_v2_performance_view_v2(record)
            if args.view_version == "v2" else build_v2_performance_view(record)
        )
        metadata = render_metadata_facts(build_metadata_facts(record.metadata, ("v2",)))
        envelope = (
            f"[공고] {record.notice_id}\n\n[v2 판정 계약]\n{card}\n\n"
            f"[v2에 필요한 주최측 입력 사실]\n{metadata}\n\n"
            f"[모든 제공 문서의 source-grounded 후보]\n"
            f"{render_v2_performance_view(view)}"
        )
        views[record.notice_id] = view
        envelopes[record.notice_id] = envelope
        if args.actual_task:
            builder = (
                build_v2_performance_task_v2 if args.task_version == "v2"
                else build_v2_performance_task
            )
            task = builder(record, card, view)
            tasks[record.notice_id] = task
            messages = task["messages"]
        else:
            messages = [
                {"role": "system", "content": "v2 source-view no-call admission envelope"},
                {"role": "user", "content": envelope},
            ]
        tokens[record.notice_id] = tokenizer.count(messages)
        if args.actual_task and tokens[record.notice_id] > args.budget:
            raise ValueError(f"{record.notice_id}: exact tokenizer admission failed")
        document_types.update(document.document_type for document in record.documents)
        evidence = labels[record.notice_id]["e2"]
        if evidence:
            evidence_total += 1
            if any(evidence in candidate.span.exact_text for candidate in view.candidates):
                evidence_covered += 1

    headroom = {notice_id: args.budget - value for notice_id, value in tokens.items()}
    feasible = {notice_id: value for notice_id, value in headroom.items()
                if value >= TASK_CONTRACT_RESERVE}
    insufficient = {notice_id: value for notice_id, value in headroom.items()
                    if value < TASK_CONTRACT_RESERVE}
    record_map = {record.notice_id: record for record in records}
    attachment = {notice_id: tokens[notice_id] for notice_id in tokens
                  if len(record_map[notice_id].documents) > 1}
    samples = {
        "short_complete": min(tokens, key=tokens.get),
        "attachment_complete": min(attachment, key=attachment.get),
        "largest_envelope": max(tokens, key=tokens.get),
    }
    for notice_id in args.review_id:
        if notice_id not in views:
            raise ValueError(f"unknown review ID: {notice_id}")
        samples[f"review_{notice_id}"] = notice_id
    rendered_paths = {}
    for role, notice_id in samples.items():
        path = args.output_dir / "rendered_inputs" / f"{role}_{notice_id}.json"
        atomic_json(path, {
            "id": notice_id, "role": role,
            "envelope_tokens": tokens[notice_id], "budget": args.budget,
            "task_contract_reserve": TASK_CONTRACT_RESERVE,
            "remaining_tokens": headroom[notice_id],
            "user_envelope": envelopes[notice_id],
            "task": tasks.get(notice_id),
            "document_coverage": list(views[notice_id].document_coverage),
        })
        rendered_paths[role] = str(path)
    report = {
        "kind": (
            "zero_call_v2_performance_actual_task_audit" if args.actual_task
            else "zero_call_v2_performance_source_view_probe"
        ),
        "view_version": args.view_version,
        "task_version": args.task_version if args.actual_task else None,
        "actual_task": args.actual_task,
        "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "labels_sha256": hashlib.sha256(args.labels.read_bytes()).hexdigest(),
        "cards_sha256": hashlib.sha256(args.cards.read_bytes()).hexdigest(),
        "records": len(records),
        "inspected_documents": sum(document_types.values()),
        "document_types": dict(sorted(document_types.items())),
        "candidate_spans": sum(len(view.candidates) for view in views.values()),
        "candidate_characters": sum(
            len(candidate.span.exact_text)
            for view in views.values() for candidate in view.candidates
        ),
        "gold_e2_nonempty": evidence_total,
        "gold_e2_covered": evidence_covered,
        "envelope_token_min": min(tokens.values()),
        "envelope_token_max": max(tokens.values()),
        "task_contract_reserve": TASK_CONTRACT_RESERVE,
        "reserve_feasible": len(feasible),
        "reserve_insufficient": len(insufficient),
        "insufficient_by_notice": insufficient,
        "tokens_by_notice": tokens,
        "headroom_by_notice": headroom,
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
        "records", "inspected_documents", "candidate_spans",
        "candidate_characters", "gold_e2_nonempty", "gold_e2_covered",
        "envelope_token_min", "envelope_token_max", "task_contract_reserve",
        "reserve_feasible", "reserve_insufficient", "rendered_paths", "model_calls",
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
