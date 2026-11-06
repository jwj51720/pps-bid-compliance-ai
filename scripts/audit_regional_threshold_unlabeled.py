#!/usr/bin/env python3
"""Stream unlabeled organizer notices to measure threshold-branch coverage."""

from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai.facts.regional_thresholds import classify_regional_threshold
from src.pps_ai.decisions.regional_source_predicates import collect_regional_source_hits
from src.pps_ai.decisions.regional_thresholds import (
    apply_regional_threshold, guard_new_regional_positives,
)
from src.pps_ai.reference import FrozenL41Reference
from src.pps_ai.runtime.openrouter import atomic_json
from src.pps_ai.views.regional_participation import (
    build_regional_participation_candidates,
)


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
    source = (ROOT / config["regional_threshold_policy"]["unlabeled_input_path"]).resolve()
    destination = (ROOT / config["output_dir"] / "unlabeled_coverage.json").resolve()
    states: Counter[str] = Counter()
    branches: Counter[str] = Counter()
    price_bands: Counter[str] = Counter()
    local_regions: Counter[str] = Counter()
    examples: dict[str, list[str]] = {}
    possible_amount_changes: Counter[str] = Counter()
    predicate_changes: Counter[str] = Counter()
    guarded_changes: Counter[str] = Counter()
    predicate_change_examples: dict[str, list[str]] = {}
    predicate_change_reviews: list[dict[str, object]] = []
    seen: set[str] = set()
    reference_info = config["reference"]
    reference_path = (ROOT / reference_info["zip_path"]).resolve()
    reference = FrozenL41Reference(
        reference_path, reference_info["zip_sha256"],
    )
    final_logic = reference.pipeline.l40.apply_all.__globals__
    with gzip.open(source, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            notice_id = str(record.get("id") or "")
            if not notice_id or notice_id in seen:
                raise ValueError("unlabeled source has missing/duplicate notice ID")
            seen.add(notice_id)
            fact = classify_regional_threshold(record)
            state = f"{fact.contract_law}/{fact.state}"
            branch = f"{fact.contract_law}/{fact.institution_type}/{fact.service_type}/{fact.threshold_won}"
            states[state] += 1
            branches[branch] += 1
            if fact.contract_law != "지방계약법":
                continue
            price = (record.get("meta") or {}).get("입찰추정가격")
            if fact.state == "CONFIRMED" and fact.threshold_won is not None and type(price) is int:
                old_caps = {
                    "v5": final_logic["v5_gate"].amount_cap(record),
                    "v6": final_logic["v6_gate"].amount_cap(record),
                    "v7": final_logic["v7_gate"].amount_cap(record),
                }
                amount_disagreements = {
                    item for item, old_cap in old_caps.items()
                    if (price >= old_cap) != (price >= fact.threshold_won)
                }
                for item in amount_disagreements:
                    possible_amount_changes[item] += 1
                if amount_disagreements:
                    hits = collect_regional_source_hits(record, final_logic)
                    old_labels = {
                        "v5": int(price >= old_caps["v5"] and bool(hits.v5)),
                        "v6": int(
                            price < old_caps["v6"] and bool(hits.v6)
                            and not hits.small_quote_exception
                        ),
                        "v7": int(
                            price < old_caps["v7"] and bool(hits.v7)
                            and not hits.small_quote_exception
                        ),
                    }
                    new_labels = apply_regional_threshold(
                        fact, price, hits.counts, hits.small_quote_exception, old_labels,
                    ).labels
                    guarded_labels = guard_new_regional_positives(
                        apply_regional_threshold(
                            fact, price, hits.counts, hits.small_quote_exception, old_labels,
                        ),
                        old_labels,
                        build_regional_participation_candidates(record),
                    ).labels
                    for item in amount_disagreements:
                        if old_labels[item] == new_labels[item]:
                            continue
                        direction = f"{item}/{old_labels[item]}->{new_labels[item]}"
                        predicate_changes[direction] += 1
                        if old_labels[item] != guarded_labels[item]:
                            guarded_changes[direction] += 1
                        if len(predicate_change_examples.setdefault(direction, [])) < 20:
                            predicate_change_examples[direction].append(notice_id)
                        source_hits = hits.by_item[item]
                        evidence = source_hits[0] if source_hits else ""
                        source_docs = [
                            {
                                "doc_id": str(doc.get("doc_id") or ""),
                                "type": str(doc.get("type") or ""),
                            }
                            for doc in record.get("docs") or []
                            if evidence and evidence in str(doc.get("text") or "")
                        ]
                        predicate_change_reviews.append({
                            "id": notice_id,
                            "item": item,
                            "direction": direction,
                            "estimated_price": price,
                            "threshold": fact.threshold_won,
                            "institution_type": fact.institution_type,
                            "service_type": fact.service_type,
                            "source_hit_count": len(source_hits),
                            "first_source_hit": evidence[:500],
                            "source_documents": source_docs,
                            "participation_candidates": [
                                {
                                    "doc_id": value.doc_id,
                                    "type": value.document_type,
                                    "exact_text": value.exact_text,
                                    "basic_region": value.basic_region,
                                    "region_count": value.region_count,
                                }
                                for value in build_regional_participation_candidates(record)
                            ],
                        })
            if type(price) is not int:
                band = "UNKNOWN_PRICE"
            elif price < 150_000_000:
                band = "lt_150m"
            elif price < 230_000_000:
                band = "150m_to_230m"
            elif price < 330_000_000:
                band = "230m_to_330m"
            elif price < 350_000_000:
                band = "330m_to_350m"
            elif price < 500_000_000:
                band = "350m_to_500m"
            else:
                band = "ge_500m"
            price_bands[f"{fact.state}/{fact.threshold_won}/{band}"] += 1
            region = str((record.get("meta") or {}).get("지역제한여부") or "")
            local_regions[f"{fact.state}/{fact.threshold_won}/{band}/{region}"] += 1
            sample_key = f"{fact.state}/{fact.threshold_won}/{band}/{region}"
            if len(examples.setdefault(sample_key, [])) < 5:
                examples[sample_key].append(notice_id)
    report = {
        "status": "PASS",
        "phase": "unlabeled_source_coverage_not_f1",
        "source_path": str(source),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "record_count": len(seen),
        "llm_calls": 0,
        "api_calls": 0,
        "total_seconds": round(time.monotonic() - started, 3),
        "states": dict(sorted(states.items())),
        "branches": dict(sorted(branches.items())),
        "local_price_bands": dict(sorted(price_bands.items())),
        "local_region_flags_by_band": dict(sorted(local_regions.items())),
        "example_ids_by_band": dict(sorted(examples.items())),
        "amount_gate_disagreement_counts": dict(sorted(possible_amount_changes.items())),
        "source_predicate_label_change_counts": dict(sorted(predicate_changes.items())),
        "guarded_label_change_counts": dict(sorted(guarded_changes.items())),
        "source_predicate_change_examples": dict(sorted(predicate_change_examples.items())),
        "limitation": "Region metadata is a risk proxy, not a source-document participation predicate or label.",
    }
    atomic_json(destination, report)
    atomic_json(destination.with_name("unlabeled_predicate_change_review.json"),
                predicate_change_reviews)
    print(json.dumps({
        "status": report["status"],
        "record_count": report["record_count"],
        "states": report["states"],
        "local_price_bands": report["local_price_bands"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
