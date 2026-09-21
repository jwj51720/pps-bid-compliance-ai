#!/usr/bin/env python3
"""Run the label-blind C006 v9 target-role observability audit."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai.ingest import load_notice_records
from src.pps_ai.runtime.openrouter import atomic_json
from src.pps_ai.runtime.tokenizer import GemmaTokenCounter
from src.pps_ai.views.v9_targets import build_v9_target_view, render_v9_candidates


def _read_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["id"]: row for row in csv.DictReader(handle)}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _percentile_95(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)]


def _candidate_row(candidate: Any) -> dict[str, Any]:
    return {
        "source_id": candidate.source_id,
        "doc_id": candidate.doc_id,
        "document_type": candidate.document_type,
        "document_order": candidate.document_order,
        "start": candidate.start,
        "end": candidate.end,
        "sha256": candidate.sha256,
        "trigger_kinds": list(candidate.trigger_kinds),
        "trigger_surfaces": list(candidate.trigger_surfaces),
        "text": candidate.text,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/raw/open/dev.jsonl.gz")
    parser.add_argument("--labels", default="data/raw/open/dev_labels.csv")
    parser.add_argument(
        "--baseline",
        default="outputs/clean-exp-c005d-v19-dev200-promotion-v1/dev200/submission.csv",
    )
    parser.add_argument("--item-table", default="data/raw/open/data/항목표.json")
    parser.add_argument(
        "--card", default="data/derived/decision_cards_v30_full_source_concordance.json",
    )
    parser.add_argument(
        "--tokenizer-dir",
        default=(
            "~/.cache/huggingface/hub/models--google--gemma-4-26B-A4B-it/"
            "snapshots/4d7ae4984b7db7de8f8457170b3f1a419ee76d52"
        ),
    )
    parser.add_argument(
        "--output", default="outputs/clean-exp-c006-v9-target-role-phase-a",
    )
    args = parser.parse_args()

    input_path = (ROOT / args.input).resolve()
    labels_path = (ROOT / args.labels).resolve()
    baseline_path = (ROOT / args.baseline).resolve()
    item_table_path = (ROOT / args.item_table).resolve()
    card_path = (ROOT / args.card).resolve()
    output_dir = (ROOT / args.output).resolve()
    tokenizer_dir = Path(args.tokenizer_dir).expanduser().resolve()

    records = load_notice_records(input_path)
    # Views are fully constructed before labels or baseline predictions are loaded.
    views = {record.notice_id: build_v9_target_view(record) for record in records}
    labels = _read_rows(labels_path)
    baseline = _read_rows(baseline_path)
    record_ids = {record.notice_id for record in records}
    if set(labels) != record_ids or set(baseline) != record_ids:
        raise ValueError("input/label/baseline ID coverage differs")
    counter = GemmaTokenCounter(tokenizer_dir)
    token_counts = {}
    candidate_ledger = []
    source_coverage = []
    for record in records:
        view = views[record.notice_id]
        if len(view["document_coverage"]) != len(record.documents):
            raise ValueError(f"{record.notice_id}: document coverage differs")
        if any(not row["inspected"] for row in view["document_coverage"]):
            raise ValueError(f"{record.notice_id}: uninspected document")
        rendered = render_v9_candidates(view["candidates"])
        token_counts[record.notice_id] = counter.count([
            {"role": "system", "content": "v9 source-only candidate audit"},
            {"role": "user", "content": rendered or "[NO CANDIDATE]"},
        ])
        source_coverage.append({
            "id": record.notice_id,
            "documents": view["document_coverage"],
            "candidate_count": len(view["candidates"]),
            "candidate_source_ids": [value.source_id for value in view["candidates"]],
            "candidate_only_tokens": token_counts[record.notice_id],
        })
        candidate_ledger.append({
            "id": record.notice_id,
            "candidates": [_candidate_row(value) for value in view["candidates"]],
        })

    positive_ids = {notice_id for notice_id, row in labels.items() if row["v9"] == "1"}
    error_ids = {
        notice_id for notice_id in record_ids
        if baseline[notice_id]["v9"] != labels[notice_id]["v9"]
    }
    review_ids = positive_ids | error_ids
    records_by_id = {record.notice_id: record for record in records}
    positive_rows = []
    for notice_id in sorted(positive_ids):
        evidence = labels[notice_id]["e9"]
        candidates = views[notice_id]["candidates"]
        evidence_source = None
        if evidence:
            for document in records_by_id[notice_id].documents:
                if evidence in document.text:
                    evidence_source = document.doc_id
                    break
        containing = [
            candidate.source_id for candidate in candidates
            if evidence and evidence in candidate.text
        ]
        positive_rows.append({
            "id": notice_id,
            "gold_evidence_nonempty": bool(evidence),
            "gold_evidence_source_doc_id": evidence_source,
            "candidate_count": len(candidates),
            "candidate_present": bool(candidates),
            "evidence_containing_candidate_ids": containing,
            "evidence_covered": bool(containing) if evidence else None,
            "requires_human_relevance_review": not bool(evidence),
        })

    for notice_id in sorted(review_ids):
        record = records_by_id[notice_id]
        atomic_json(output_dir / "error_review_packets" / f"{notice_id}.json", {
            "id": notice_id,
            "baseline_v9": int(baseline[notice_id]["v9"]),
            "gold_v9": int(labels[notice_id]["v9"]),
            "gold_e9": labels[notice_id]["e9"],
            "documents": [
                {
                    "doc_id": document.doc_id,
                    "type": document.document_type,
                    "order": document.order,
                    "sha256": document.sha256,
                    "text": document.text,
                }
                for document in record.documents
            ],
            "view": {
                "document_coverage": views[notice_id]["document_coverage"],
                "candidates": [
                    _candidate_row(value) for value in views[notice_id]["candidates"]
                ],
            },
        })

    item_table = json.loads(item_table_path.read_text(encoding="utf-8"))
    cards = json.loads(card_path.read_text(encoding="utf-8"))
    source_ledger = {
        "item_table": {
            "path": str(item_table_path),
            "sha256": _sha256(item_table_path),
            "v9": item_table["항목"]["v9"],
        },
        "decision_card": {
            "path": str(card_path),
            "sha256": _sha256(card_path),
            "v9": cards["cards"]["v9"],
        },
    }
    all_documents = [row for item in source_coverage for row in item["documents"]]
    nonempty_positive_rows = [row for row in positive_rows if row["gold_evidence_nonempty"]]
    report = {
        "status": "PASS",
        "phase": "offline_observability_only",
        "records": len(records),
        "documents_inspected": len(all_documents),
        "documents_uninspected": sum(not row["inspected"] for row in all_documents),
        "candidate_notices": sum(bool(item["candidate_count"]) for item in source_coverage),
        "candidate_count": sum(item["candidate_count"] for item in source_coverage),
        "candidate_only_tokens": {
            "sum": sum(token_counts.values()),
            "min": min(token_counts.values()),
            "p95": _percentile_95(list(token_counts.values())),
            "max": max(token_counts.values()),
            "over_14848": sum(value > 14848 for value in token_counts.values()),
        },
        "v9_positive_notices": len(positive_ids),
        "v9_positive_with_any_candidate": sum(row["candidate_present"] for row in positive_rows),
        "v9_nonempty_gold_evidence": len(nonempty_positive_rows),
        "v9_nonempty_gold_evidence_covered": sum(
            bool(row["evidence_covered"]) for row in nonempty_positive_rows
        ),
        "baseline_error_notices": len(error_ids),
        "baseline_errors_with_any_candidate": sum(
            bool(views[notice_id]["candidates"]) for notice_id in error_ids
        ),
        "positive_coverage": positive_rows,
        "review_packet_ids": sorted(review_ids),
        "source_ledger": source_ledger,
        "label_use": "post-view coverage measurement and review-packet selection only",
        "llm_calls": 0,
        "final_label_decisions": 0,
    }
    atomic_json(output_dir / "source_coverage.json", source_coverage)
    atomic_json(output_dir / "candidate_ledger.json", candidate_ledger)
    atomic_json(output_dir / "organizer_source_ledger.json", source_ledger)
    atomic_json(output_dir / "observability_report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
