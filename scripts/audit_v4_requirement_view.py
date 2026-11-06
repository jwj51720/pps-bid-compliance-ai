#!/usr/bin/env python3
"""Audit native C007B v4 source observability without model calls."""

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
from src.pps_ai.decisions.v4_requirements import build_v4_scope_task, build_v4_task
from src.pps_ai.decisions.v4_allowance_axes import build_v4_axis_task
from src.pps_ai.runtime.openrouter import atomic_json
from src.pps_ai.runtime.tokenizer import GemmaTokenCounter
from src.pps_ai.views.v4_requirements import (
    V4RequirementCandidate,
    build_v4_requirement_view,
    render_v4_candidates,
)
from src.pps_ai.views.v4_requirement_scope import (
    build_v4_requirement_scope_view,
    render_v4_scoped_candidates,
)


def _read_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["id"]: row for row in csv.DictReader(handle)}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _p95(values: list[int]) -> int:
    ordered = sorted(values)
    return ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)] if ordered else 0


def _candidate(candidate: V4RequirementCandidate) -> dict[str, Any]:
    return {
        "source_id": candidate.source_id,
        "doc_id": candidate.doc_id,
        "document_type": candidate.document_type,
        "document_order": candidate.document_order,
        "start": candidate.start,
        "end": candidate.end,
        "document_sha256": candidate.document_sha256,
        "trigger_surfaces": list(candidate.trigger_surfaces),
        "text": candidate.text,
        "heading_trail": [
            {"start": line.start, "end": line.end, "text": line.text}
            for line in candidate.heading_trail
        ],
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
        "--output", default="outputs/clean-exp-c007b-v4-requirement-view-audit-v1",
    )
    parser.add_argument("--scope", choices=("base", "heading-trail"), default="base")
    parser.add_argument("--allowance-axes", action="store_true")
    parser.add_argument("--review-id", action="append", default=[])
    args = parser.parse_args()

    input_path = (ROOT / args.input).resolve()
    labels_path = (ROOT / args.labels).resolve()
    baseline_path = (ROOT / args.baseline).resolve()
    item_table_path = (ROOT / args.item_table).resolve()
    card_path = (ROOT / args.card).resolve()
    output_dir = (ROOT / args.output).resolve()
    tokenizer_dir = Path(args.tokenizer_dir).expanduser().resolve()

    records = load_notice_records(input_path)
    # Build every label-blind view before reading labels or predictions.
    view_builder = (
        build_v4_requirement_scope_view if args.scope == "heading-trail"
        else build_v4_requirement_view
    )
    if args.allowance_axes and args.scope != "heading-trail":
        parser.error("allowance axes require heading-trail scope")
    task_builder = (
        build_v4_axis_task if args.allowance_axes else
        build_v4_scope_task if args.scope == "heading-trail" else build_v4_task
    )
    render_candidates = (
        render_v4_scoped_candidates if args.scope == "heading-trail"
        else render_v4_candidates
    )
    views = {record.notice_id: view_builder(record.raw) for record in records}
    labels = _read_rows(labels_path)
    baseline = _read_rows(baseline_path)
    expected_ids = {record.notice_id for record in records}
    if set(labels) != expected_ids or set(baseline) != expected_ids:
        raise ValueError("input/label/baseline ID coverage differs")

    counter = GemmaTokenCounter(tokenizer_dir)
    candidate_only_tokens: dict[str, int] = {}
    task_tokens: dict[str, int] = {}
    tasks: dict[str, dict[str, Any]] = {}
    task_candidates: dict[str, tuple[V4RequirementCandidate, ...]] = {}
    notice_task_ids: dict[str, list[str]] = {}
    coverage_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    for record in records:
        view = views[record.notice_id]
        if len(view["document_coverage"]) != len(record.documents):
            raise ValueError(f"{record.notice_id}: document coverage differs")
        if any(not row["inspected"] for row in view["document_coverage"]):
            raise ValueError(f"{record.notice_id}: uninspected document")
        for candidate in view["candidates"]:
            document = record.documents[candidate.document_order]
            if (
                document.doc_id != candidate.doc_id
                or document.sha256 != candidate.document_sha256
                or document.text[candidate.start:candidate.end] != candidate.text
            ):
                raise ValueError(f"{record.notice_id}: candidate provenance differs")
            for heading in candidate.heading_trail:
                if (
                    not 0 <= heading.start < heading.end <= candidate.start
                    or document.text[heading.start:heading.end] != heading.text
                ):
                    raise ValueError(f"{record.notice_id}: heading provenance differs")
        rendered = render_candidates(view["candidates"])
        candidate_only_tokens[record.notice_id] = counter.count([
            {"role": "system", "content": "v4 source observability audit"},
            {"role": "user", "content": rendered or "[NO CANDIDATE]"},
        ])
        notice_task_ids[record.notice_id] = []
        current: list[V4RequirementCandidate] = []
        packs: list[tuple[V4RequirementCandidate, ...]] = []
        for candidate in view["candidates"]:
            trial = tuple([*current, candidate])
            task = task_builder(record.raw, trial)
            if counter.count(task["messages"]) <= 14_848:
                current.append(candidate)
                continue
            if not current:
                raise ValueError(
                    f"{record.notice_id}/{candidate.source_id}: one candidate exceeds budget"
                )
            packs.append(tuple(current))
            current = [candidate]
            single = task_builder(record.raw, tuple(current))
            if counter.count(single["messages"]) > 14_848:
                raise ValueError(
                    f"{record.notice_id}/{candidate.source_id}: one candidate exceeds budget"
                )
        if current:
            packs.append(tuple(current))
        for part, pack in enumerate(packs, 1):
            task_id = f"{record.notice_id}__p{part:02d}"
            task = task_builder(record.raw, pack)
            tasks[task_id] = task
            task_candidates[task_id] = pack
            task_tokens[task_id] = counter.count(task["messages"])
            notice_task_ids[record.notice_id].append(task_id)
        coverage_rows.append({
            "id": record.notice_id,
            "documents": view["document_coverage"],
            "candidate_count": len(view["candidates"]),
            "candidate_only_tokens": candidate_only_tokens[record.notice_id],
            "task_ids": notice_task_ids[record.notice_id],
            "overflow_passes": max(0, len(packs) - 1),
        })
        candidate_rows.append({
            "id": record.notice_id,
            "candidates": [_candidate(value) for value in view["candidates"]],
        })

    positive_ids = {notice_id for notice_id, row in labels.items() if row["v4"] == "1"}
    error_ids = {
        notice_id for notice_id in expected_ids
        if labels[notice_id]["v4"] != baseline[notice_id]["v4"]
    }
    review_ids = positive_ids | error_ids
    record_by_id = {record.notice_id: record for record in records}
    positive_coverage = []
    for notice_id in sorted(positive_ids):
        evidence = labels[notice_id]["e4"]
        candidates = views[notice_id]["candidates"]
        containing = [candidate.source_id for candidate in candidates if evidence and evidence in candidate.text]
        positive_coverage.append({
            "id": notice_id,
            "gold_evidence_nonempty": bool(evidence),
            "candidate_present": bool(candidates),
            "candidate_count": len(candidates),
            "evidence_containing_candidate_ids": containing,
            "evidence_covered": bool(containing) if evidence else None,
        })

    for notice_id in sorted(review_ids):
        record = record_by_id[notice_id]
        atomic_json(output_dir / "review_packets" / f"{notice_id}.json", {
            "id": notice_id,
            "baseline_v4": int(baseline[notice_id]["v4"]),
            "gold_v4": int(labels[notice_id]["v4"]),
            "gold_e4": labels[notice_id]["e4"],
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
                "candidates": [_candidate(value) for value in views[notice_id]["candidates"]],
            },
        })

    item_table = json.loads(item_table_path.read_text(encoding="utf-8"))
    cards = json.loads(card_path.read_text(encoding="utf-8"))
    candidate_records = [record for record in records if notice_task_ids[record.notice_id]]
    rendered_samples = []
    semantic_rows = []
    if candidate_records:
        character_counts = {
            record.notice_id: sum(len(document.text) for document in record.documents)
            for record in candidate_records
        }
        attachment_id = next(
            (
                record.notice_id for record in candidate_records
                if len(record.documents) > 1
            ),
            min(character_counts, key=character_counts.get),
        )
        largest_task_id = max(task_tokens, key=task_tokens.get)
        samples = [
            ("short", min(character_counts, key=character_counts.get)),
            ("attachment", attachment_id),
            ("largest", largest_task_id.split("__p", 1)[0]),
        ]
        samples.extend(("manual_review", notice_id) for notice_id in args.review_id)
        overflow_notice = next(
            (row["id"] for row in coverage_rows if row["overflow_passes"]), None,
        )
        if overflow_notice:
            samples.append(("overflow", overflow_notice))
        seen = set()
        for role, notice_id in samples:
            if (role, notice_id) in seen:
                continue
            seen.add((role, notice_id))
            coverage = next(row for row in coverage_rows if row["id"] == notice_id)
            for task_id in notice_task_ids[notice_id]:
                task = tasks[task_id]
                path = output_dir / "rendered_inputs" / f"{role}_{task_id}.json"
                atomic_json(path, {
                    "id": notice_id,
                    "task_id": task_id,
                    "role": role,
                    "tokens": task_tokens[task_id],
                    "messages": task["messages"],
                    "schema": task["schema"],
                    "candidate_source_ids": [
                        candidate.source_id for candidate in task_candidates[task_id]
                    ],
                    "coverage": coverage,
                })
                rendered_samples.append({
                    "role": role,
                    "id": notice_id,
                    "task_id": task_id,
                    "path": str(path),
                })
                system = str(task["messages"][0]["content"])
                user = str(task["messages"][1]["content"])
                checks = {
                    "qualification_role": "실제 입찰 참가자격" in user,
                    "issuer_or_specific_relation": "특정 발주기관군" in user and "특정 사업명·대상·방식" in user,
                    "allowance_exception": (
                        "같은 제한축의 실질적 허용" in user if args.allowance_axes
                        else "민간·해외·동등·일반 유사실적 허용" in user
                    ),
                    "necessity_exception": "구체적 필요" in user,
                    "evaluation_zero": "평가·가점" in user,
                    "form_zero": "증빙서식" in user,
                    "no_final_label": (
                        "최종 v4 또는 위반 0/1은 출력하지 않는다" in system
                        if args.allowance_axes else
                        "최종 v4나 위반 0/1은 출력하지 않는다" in system
                    ),
                    "all_candidate_ids": all(
                        f"[{candidate.source_id} |" in user
                        for candidate in task_candidates[task_id]
                    ),
                }
                if args.scope == "heading-trail":
                    checks["heading_trail"] = (
                        "직전 제목형" in system and "원문 줄" in system
                        and "[직전 제목형 원문 줄 — 소속 관계는 확정하지 않음]" in user
                    )
                if args.allowance_axes:
                    checks["two_allowance_axes"] = (
                        "i 발주기관 허용" in system
                        and "a 사업내용 허용" in system
                        and "발주기관군과 사업내용은 독립된 축" in system
                    )
                semantic_rows.append({
                    "task_id": task_id,
                    "checks": checks,
                    "status": "PASS" if all(checks.values()) else "FAIL",
                })
    atomic_json(output_dir / "semantic_contract.json", {
        "active_item": "v4",
        "rendered_tasks": semantic_rows,
        "status": "PASS" if semantic_rows and all(
            row["status"] == "PASS" for row in semantic_rows
        ) else "FAIL",
    })
    all_documents = [row for notice in coverage_rows for row in notice["documents"]]
    nonempty = [row for row in positive_coverage if row["gold_evidence_nonempty"]]
    semantic_pass = bool(semantic_rows) and all(
        row["status"] == "PASS" for row in semantic_rows
    )
    report = {
        "status": "PASS" if semantic_pass else "FAIL",
        "phase": "label_blind_source_observability_only",
        "records": len(records),
        "documents_inspected": len(all_documents),
        "documents_uninspected": sum(not row["inspected"] for row in all_documents),
        "candidate_notices": sum(bool(row["candidate_count"]) for row in coverage_rows),
        "candidate_count": sum(row["candidate_count"] for row in coverage_rows),
        "scope_mode": args.scope,
        "allowance_axes": args.allowance_axes,
        "candidate_with_heading_trail": sum(
            bool(candidate.heading_trail)
            for view in views.values() for candidate in view["candidates"]
        ),
        "heading_line_count": sum(
            len(candidate.heading_trail)
            for view in views.values() for candidate in view["candidates"]
        ),
        "heading_provenance_errors": 0,
        "candidate_only_tokens": {
            "sum": sum(candidate_only_tokens.values()),
            "min": min(candidate_only_tokens.values()),
            "p95": _p95(list(candidate_only_tokens.values())),
            "max": max(candidate_only_tokens.values()),
        },
        "admitted_tasks": {
            "logical_calls": len(tasks),
            "overflow_passes": sum(row["overflow_passes"] for row in coverage_rows),
            "tokens_sum": sum(task_tokens.values()),
            "tokens_min": min(task_tokens.values(), default=0),
            "tokens_p95": _p95(list(task_tokens.values())),
            "tokens_max": max(task_tokens.values(), default=0),
            "over_14848": sum(value > 14_848 for value in task_tokens.values()),
            "task_hashes": {
                task_id: counter.task_sha256(task) for task_id, task in tasks.items()
            },
        },
        "v4_positive_notices": len(positive_ids),
        "v4_positive_with_any_candidate": sum(row["candidate_present"] for row in positive_coverage),
        "v4_nonempty_gold_evidence": len(nonempty),
        "v4_nonempty_gold_evidence_covered": sum(bool(row["evidence_covered"]) for row in nonempty),
        "baseline_error_notices": len(error_ids),
        "baseline_errors_with_any_candidate": sum(bool(views[notice_id]["candidates"]) for notice_id in error_ids),
        "positive_coverage": positive_coverage,
        "review_packet_ids": sorted(review_ids),
        "rendered_samples": rendered_samples,
        "semantic_contract": "PASS" if semantic_pass else "FAIL",
        "source_ledger": {
            "item_table": {
                "path": str(item_table_path),
                "sha256": _sha256(item_table_path),
                "v4": item_table["항목"]["v4"],
            },
            "decision_card": {
                "path": str(card_path),
                "sha256": _sha256(card_path),
                "v4": cards["cards"]["v4"],
            },
        },
        "label_use": "post-view coverage measurement and review selection only",
        "llm_calls": 0,
        "final_label_decisions": 0,
    }
    atomic_json(output_dir / "source_coverage.json", coverage_rows)
    atomic_json(output_dir / "candidate_ledger.json", candidate_rows)
    atomic_json(output_dir / "observability_report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if semantic_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
