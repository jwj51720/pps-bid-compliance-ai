#!/usr/bin/env python3
"""Audit and replay the 2026-09-22 organizer v5-v7 threshold correction."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai.evaluate import evaluate_rows
from src.pps_ai.decisions.regional_thresholds import (
    apply_regional_threshold, guard_new_regional_positives,
)
from src.pps_ai.decisions.regional_source_predicates import collect_regional_source_hits
from src.pps_ai.evidence import clean_final_rows
from src.pps_ai.export import write_submission_csv
from src.pps_ai.facts.regional_thresholds import classify_regional_threshold
from src.pps_ai.ingest import load_notice_records
from src.pps_ai.reference import FrozenL41Reference
from src.pps_ai.runtime.openrouter import atomic_json
from src.pps_ai.views.regional_participation import (
    build_regional_participation_candidates,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_rows(path: Path) -> dict[str, dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        expected = ["id"] + [f"v{i}" for i in range(1, 25)] + [
            f"e{i}" for i in range(1, 25)
        ]
        if reader.fieldnames != expected:
            raise ValueError(f"{path}: expected 49 ordered submission columns")
        rows: dict[str, dict[str, Any]] = {}
        for row in reader:
            notice_id = row["id"]
            if not notice_id or notice_id in rows:
                raise ValueError(f"{path}: missing or duplicate notice ID")
            rows[notice_id] = dict(row)
        return rows


def _evidence(hit: str) -> str:
    value = hit.strip()
    while value.startswith(("=", "+", "@")):
        value = value[1:].lstrip()
    return value[:500]


def _item_counts(
    truth: Mapping[str, Mapping[str, Any]], rows: Mapping[str, Mapping[str, Any]], item: str,
) -> dict[str, float | int]:
    tp = fp = fn = tn = 0
    for notice_id, row in rows.items():
        actual = int(truth[notice_id][item])
        predicted = int(row[item])
        tp += int(actual == 1 and predicted == 1)
        fp += int(actual == 0 and predicted == 1)
        fn += int(actual == 1 and predicted == 0)
        tn += int(actual == 0 and predicted == 0)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": precision, "recall": recall, "f1": f1}


def main() -> int:
    started = time.monotonic()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="experiments/manifests/clean_exp_s002_regional_threshold_audit_v1.json",
    )
    args = parser.parse_args()
    config_path = (ROOT / args.config).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    data = config["data"]
    output_dir = (ROOT / config["output_dir"]).resolve()
    input_path = (ROOT / data["input_path"]).resolve()
    labels_path = (ROOT / data["labels_path"]).resolve()
    baseline_path = (ROOT / config["regional_threshold_policy"]["base_submission_path"]).resolve()
    fast_path = (ROOT / config["evaluation"]["fast_panel_path"]).resolve()
    holdout_path = (ROOT / config["evaluation"]["holdout_panel_path"]).resolve()
    reference_path = (ROOT / config["reference"]["zip_path"]).resolve()

    records = load_notice_records(input_path)
    raw_records = {record.notice_id: dict(record.raw) for record in records}
    baseline = _read_rows(baseline_path)
    truth = _read_rows(labels_path)
    expected_ids = set(raw_records)
    if set(baseline) != expected_ids or set(truth) != expected_ids:
        raise ValueError("input, baseline, and label ID coverage differs")

    reference = FrozenL41Reference(reference_path, config["reference"]["zip_sha256"])
    pipeline = reference.pipeline
    final_logic = pipeline.l40.apply_all.__globals__
    required_gates = {"strict_region_hits", "v5_gate", "v6_gate", "v7_gate"}
    if not required_gates <= set(final_logic):
        raise ValueError("hash-pinned reference does not expose the expected regional gates")
    facts = {
        notice_id: classify_regional_threshold(record)
        for notice_id, record in raw_records.items()
    }
    participation_views = {
        notice_id: build_regional_participation_candidates(record)
        for notice_id, record in raw_records.items()
    }
    candidate = {notice_id: dict(row) for notice_id, row in baseline.items()}
    details = []
    changes = []
    for notice_id, record in raw_records.items():
        fact = facts[notice_id]
        estimate = (record.get("meta") or {}).get("입찰추정가격")
        hits = collect_regional_source_hits(record, final_logic)
        for candidate_view in participation_views[notice_id]:
            source_document = record["docs"][candidate_view.document_order]
            if (
                str(source_document["doc_id"]) != candidate_view.doc_id
                or source_document["text"][candidate_view.start:candidate_view.end]
                != candidate_view.exact_text
            ):
                raise ValueError(f"{notice_id}: regional source span provenance differs")
        row = candidate[notice_id]
        before = {item: int(row[item]) for item in ("v5", "v6", "v7")}
        raw_verdict = apply_regional_threshold(
            fact, estimate, hits.counts, hits.small_quote_exception, before,
        )
        verdict = guard_new_regional_positives(
            raw_verdict, before, participation_views[notice_id],
        )
        if verdict.applied:
            for item, value in verdict.labels.items():
                row[item] = value
                row["e" + item[1:]] = _evidence(hits.by_item[item][0]) if value else ""
        after = {item: int(row[item]) for item in ("v5", "v6", "v7")}
        changed = [item for item in before if before[item] != after[item]]
        if changed:
            changes.append({"id": notice_id, "items": changed, "before": before, "after": after})
        details.append({
            "id": notice_id,
            "estimated_price": estimate,
            "fact": fact.to_dict(),
            "source_predicates": {
                "v5_hit_count": len(hits.v5),
                "v6_hit_count": len(hits.v6),
                "v7_hit_count": len(hits.v7),
                "small_quote_exception": hits.small_quote_exception,
            },
            "threshold_applied": verdict.applied,
            "threshold_reason": verdict.reason,
            "raw_threshold_labels": dict(raw_verdict.labels),
            "participation_candidate_count": len(participation_views[notice_id]),
            "participation_candidates": [
                {
                    "doc_id": value.doc_id,
                    "type": value.document_type,
                    "start": value.start,
                    "end": value.end,
                    "exact_text": value.exact_text,
                    "basic_region": value.basic_region,
                    "region_count": value.region_count,
                }
                for value in participation_views[notice_id]
            ],
            "before": before,
            "after": after,
            "changed_items": changed,
        })

    ordered_rows = [candidate[record.notice_id] for record in records]
    for row in ordered_rows:
        row["id"] = str(row["id"])
        for index in range(1, 25):
            row[f"v{index}"] = int(row[f"v{index}"])
    cleaned_rows, evidence_report = clean_final_rows(
        list(raw_records.values()), candidate,
    )
    if any(
        int(cleaned[f"v{index}"]) != int(uncleaned[f"v{index}"])
        for cleaned, uncleaned in zip(cleaned_rows, ordered_rows)
        for index in range(1, 25)
    ):
        raise ValueError("evidence validation changed a verdict")
    ordered_rows = cleaned_rows
    submission_path = output_dir / "submission.counterfactual.csv"
    write_submission_csv(submission_path, ordered_rows)
    metrics = evaluate_rows(ordered_rows, labels_path, {
        "fast20": fast_path,
        "holdout20": holdout_path,
    })

    state_counts = Counter(fact.state for fact in facts.values())
    threshold_counts = Counter(
        str(fact.threshold_won) if fact.threshold_won is not None else fact.state
        for fact in facts.values()
    )
    institution_counts = Counter(fact.institution_type for fact in facts.values())
    service_counts = Counter(fact.service_type for fact in facts.values())
    local_ids = {
        notice_id for notice_id, record in raw_records.items()
        if (record.get("meta") or {}).get("적용계약법") == "지방계약법"
    }
    local_unknown = [
        notice_id for notice_id in sorted(local_ids)
        if facts[notice_id].state != "CONFIRMED"
    ]
    positive_source_coverage = {}
    for item in ("v5", "v6", "v7"):
        positive_ids = [
            notice_id for notice_id, row in truth.items()
            if int(row[item]) == 1
        ]
        evidence_key = "e" + item[1:]
        positive_source_coverage[item] = {
            "positive_count": len(positive_ids),
            "positive_with_candidate": sum(
                bool(participation_views[notice_id]) for notice_id in positive_ids
            ),
            "positive_with_gold_evidence_in_candidate": sum(
                bool(truth[notice_id][evidence_key])
                and any(
                    str(truth[notice_id][evidence_key]) in value.exact_text
                    for value in participation_views[notice_id]
                )
                for notice_id in positive_ids
            ),
            "positive_without_candidate_ids": [
                notice_id for notice_id in positive_ids
                if not participation_views[notice_id]
            ],
        }
    report = {
        "status": "PASS",
        "phase": "zero_call_source_coverage_and_threshold_only_counterfactual",
        "experiment_id": config["experiment_id"],
        "records": len(records),
        "local_contract_records": len(local_ids),
        "state_counts": dict(sorted(state_counts.items())),
        "threshold_counts": dict(sorted(threshold_counts.items())),
        "institution_counts": dict(sorted(institution_counts.items())),
        "service_counts": dict(sorted(service_counts.items())),
        "local_unknown_count": len(local_unknown),
        "local_unknown_ids": local_unknown,
        "threshold_applied_count": sum(row["threshold_applied"] for row in details),
        "changed_notice_count": len(changes),
        "changed_cell_count": sum(len(row["items"]) for row in changes),
        "changes": changes,
        "participation_candidate_notices": sum(
            bool(view) for view in participation_views.values()
        ),
        "positive_source_coverage": positive_source_coverage,
        "v5_before": _item_counts(truth, baseline, "v5"),
        "v5_after": _item_counts(truth, candidate, "v5"),
        "v6_before": _item_counts(truth, baseline, "v6"),
        "v6_after": _item_counts(truth, candidate, "v6"),
        "v7_before": _item_counts(truth, baseline, "v7"),
        "v7_after": _item_counts(truth, candidate, "v7"),
        "metrics": metrics,
        "evidence": evidence_report,
        "llm_calls": 0,
        "api_calls": 0,
        "total_seconds": round(time.monotonic() - started, 3),
        "source_predicate_policy": "frozen reference predicates, amount filter removed only",
        "unknown_policy": "preserve base cells; never infer an institution threshold",
        "source_ledger": {
            "organizer_notice": "docs/organizer_notice_20260922_local_region_thresholds.md",
            "manifest_path": str(config_path),
            "manifest_sha256": _sha256(config_path),
            "organizer_notice_sha256": _sha256(
                ROOT / "docs/organizer_notice_20260922_local_region_thresholds.md"
            ),
            "input_path": str(input_path),
            "input_sha256": _sha256(input_path),
            "baseline_path": str(baseline_path),
            "baseline_sha256": _sha256(baseline_path),
            "reference_path": str(reference_path),
            "reference_sha256": _sha256(reference_path),
        },
    }
    atomic_json(output_dir / "fact_ledger.json", details)
    atomic_json(output_dir / "audit_report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
