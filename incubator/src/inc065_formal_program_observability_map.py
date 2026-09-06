#!/usr/bin/env python3
"""All-item observability map for legal-program discovery; no predictions."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common
from inc048_source_fragment_ontology_audit import fragments


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "incubator/runs/inc065_formal_program_observability_map"

# These are necessary inputs derived from the item-table task shape, not
# learned cues or prediction gates.  An empty tuple means the condition is
# source-side only (for example a binding specification).
PROGRAMS: dict[str, dict[str, Any]] = {
    "v1": {"family": "eligibility_performance", "metadata": ("적용계약법",), "source_fact": "participant eligibility restriction and restricted entity"},
    "v2": {"family": "eligibility_performance", "metadata": ("적용계약법", "입찰추정가격", "계약방법"), "source_fact": "bidder performance restriction"},
    "v3": {"family": "eligibility_performance", "metadata": ("입찰추정가격",), "source_fact": "bidder performance amount or scale"},
    "v4": {"family": "eligibility_performance", "metadata": ("적용계약법", "입찰추정가격", "계약방법"), "source_fact": "specific-institution or specific-performance eligibility restriction"},
    "v5": {"family": "regional_restriction", "metadata": ("적용계약법", "입찰추정가격", "지역제한여부", "제한지역코드목록"), "source_fact": "region restriction and statutory regime"},
    "v6": {"family": "regional_restriction", "metadata": ("적용계약법", "입찰추정가격", "계약방법", "지역제한여부", "제한지역코드목록"), "source_fact": "municipality-level restriction"},
    "v7": {"family": "regional_restriction", "metadata": ("적용계약법", "입찰추정가격", "계약방법", "지역제한여부", "제한지역코드목록"), "source_fact": "adjacent-region restriction and exception fact"},
    "v8": {"family": "regional_restriction", "metadata": ("적용계약법", "계약방법", "지역제한여부"), "source_fact": "coexisting performance and regional eligibility restrictions"},
    "v9": {"family": "specification_economic_restriction", "metadata": (), "source_fact": "binding model/specification and equivalence treatment"},
    "v10": {"family": "product_applicability", "metadata": ("세부품명번호목록", "입찰추정가격"), "source_fact": "direct-production restriction or its absence"},
    "v11": {"family": "product_applicability", "metadata": ("세부품명번호목록", "입찰추정가격"), "source_fact": "small-business restriction or its absence"},
    "v12": {"family": "product_applicability", "metadata": ("세부품명번호목록",), "source_fact": "direct-production eligibility restriction"},
    "v13": {"family": "product_applicability", "metadata": ("세부품명번호목록", "입찰추정가격"), "source_fact": "small-enterprise restriction"},
    "v14": {"family": "product_applicability", "metadata": ("세부품명번호목록", "입찰추정가격"), "source_fact": "small-business restriction and exception"},
    "v15": {"family": "product_applicability", "metadata": ("세부품명번호목록", "입찰추정가격"), "source_fact": "small-enterprise restriction and exception"},
    "v16": {"family": "product_applicability", "metadata": ("세부품명번호목록", "입찰추정가격"), "source_fact": "required restriction absence and exception"},
    "v17": {"family": "product_applicability", "metadata": ("세부품명번호목록", "입찰추정가격"), "source_fact": "small-business restriction and exception"},
    "v18": {"family": "product_applicability", "metadata": ("세부품명번호목록", "입찰추정가격"), "source_fact": "required restriction absence and exception"},
    "v19": {"family": "timing_procedure", "metadata": ("적용계약법", "계약방법"), "source_fact": "supply-confirmation submission timing"},
    "v20": {"family": "timing_procedure", "metadata": ("정보화사업여부", "입찰추정가격"), "source_fact": "software participant eligibility and project scope"},
    "v21": {"family": "timing_procedure", "metadata": ("공동도급구성방식",), "source_fact": "joint-contract member share"},
    "v22": {"family": "timing_procedure", "metadata": ("낙찰방법",), "source_fact": "site-briefing attendance as eligibility"},
    "v23": {"family": "timing_procedure", "metadata": ("적용계약법", "낙찰방법", "공고게시일자", "개찰예정일자"), "source_fact": "proposal/site-briefing schedule"},
    "v24": {"family": "cross_source_consistency", "metadata": ("배정예산금액", "계약방법", "제한지역코드목록", "면허업종제한목록"), "source_fact": "corresponding notice declaration"},
}


def present(value: Any) -> bool:
    return value not in (None, "", "미입력")


def main() -> None:
    data = ROOT / "data/raw/open"
    records = list(common.read_jsonl_gz(data / "dev.jsonl.gz"))
    labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}
    predictions = {row["id"]: row for row in csv.DictReader((ROOT / "incubator/runs/inc041_v2_v3_v21_rule_composition_audit/dev_composed_predictions.csv").open(encoding="utf-8"))}
    record_by_id = {record["id"]: record for record in records}
    rows = []
    for item in common.ITEMS:
        program = PROGRAMS[item]
        evidence_key = f"e{item[1:]}"
        positives = [record["id"] for record in records if labels[record["id"]][item] == "1"]
        source_lines = {record["id"]: [line["text"] for line in fragments(record) if line["kind"] == "line" and line["selectable"]] for record in records}
        evidence_nonempty = [record_id for record_id in positives if labels[record_id][evidence_key]]
        line_contained = [record_id for record_id in evidence_nonempty if any(labels[record_id][evidence_key] in line for line in source_lines[record_id])]
        metadata_complete = [record["id"] for record in records if all(present(record["meta"].get(key)) for key in program["metadata"])]
        tp = fp = fn = 0
        for record in records:
            gold = int(labels[record["id"]][item])
            predicted = int(predictions[record["id"]][item])
            tp += gold and predicted
            fp += (not gold) and predicted
            fn += gold and (not predicted)
        rows.append({
            "item": item,
            **program,
            "positive_count": len(positives),
            "metadata_complete_notices": len(metadata_complete),
            "metadata_complete_rate": len(metadata_complete) / len(records),
            "positive_with_nonempty_organizer_evidence": len(evidence_nonempty),
            "positive_evidence_source_line_contained": len(line_contained),
            "source_line_coverage_of_nonempty_evidence": len(line_contained) / len(evidence_nonempty) if evidence_nonempty else None,
            "inc041": {"tp": tp, "fp": fp, "fn": fn, "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0},
            "necessary_observability": {
                "metadata_all_notices": len(metadata_complete) == len(records),
                "all_positive_evidence_line_contained": bool(evidence_nonempty) and len(line_contained) == len(positives),
                "eligible_for_program_construction": len(metadata_complete) == len(records) and bool(evidence_nonempty) and len(line_contained) == len(positives),
            },
        })
    by_family: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_family.setdefault(row["family"], []).append(row)
    report = {
        "experiment_id": "inc065_formal_program_observability_map",
        "method": "all-item offline necessary-input audit; no model call, prediction, threshold, or rule",
        "source_sha256": {"dev": common.sha256_file(data / "dev.jsonl.gz"), "labels": common.sha256_file(data / "dev_labels.csv"), "inc041": common.sha256_file(ROOT / "incubator/runs/inc041_v2_v3_v21_rule_composition_audit/dev_composed_predictions.csv")},
        "items": rows,
        "families": {family: {"items": [row["item"] for row in members], "program_construction_eligible": [row["item"] for row in members if row["necessary_observability"]["eligible_for_program_construction"]]} for family, members in by_family.items()},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    common.write_json(OUT / "report.json", report)
    print(json.dumps(report["families"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
