#!/usr/bin/env python3
"""Audit whether EXP171's broad fact navigation can preserve source relations.

This is deliberately label-blind: it reads only source-first prediction
artifacts and organizer notice metadata, never dev_labels or V/E judgments.
It does not propose or execute a new prompt.  Its role is to decide whether a
relation-specific source-only candidate has enough representability evidence
to justify its own feasibility work.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data import load_records
from src.schema import FACT_INVENTORY_CATEGORIES


RELATION_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "v3": {
        "relation": "single performance amount ↔ same-object/same-unit reference amount",
        "categories": ("참가자격_실적_지역", "금액_메타대조"),
        "minimum_source_endpoints": 2,
    },
    "v8": {
        "relation": "same qualification clause: performance restriction ↔ regional restriction",
        "categories": ("참가자격_실적_지역",),
        "minimum_source_endpoints": 2,
    },
    "v9": {
        "relation": "maker/model requirement ↔ equivalent/compatible or special-need qualifier",
        "categories": ("규격_모델_기술요구",),
        "minimum_source_endpoints": 2,
    },
    "v19": {
        "relation": "undertaking/document ↔ pre-bid/pre-proposal timing and purpose",
        "categories": ("제출서류_확약서",),
        "minimum_source_endpoints": 2,
    },
    "v21": {
        "relation": "each-member minimum share ↔ joint-contract method/member role",
        "categories": ("계약방식_공동계약",),
        "minimum_source_endpoints": 2,
    },
    "v22": {
        "relation": "briefing attendance ↔ explicit proposal/bid eligibility consequence",
        "categories": ("일정_설명회",),
        "minimum_source_endpoints": 2,
    },
    "v23": {
        "relation": "notice date ↔ briefing/proposal deadline role",
        "categories": ("일정_설명회",),
        "minimum_source_endpoints": 2,
    },
    "v24": {
        "relation": "notice's explicit field value ↔ same semantic metadata field",
        "categories": ("금액_메타대조",),
        "minimum_source_endpoints": 1,
    },
}


def _read_predictions(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        row = json.loads(line)
        record_id = row.get("id")
        if not isinstance(record_id, str):
            raise ValueError(f"prediction line {line_number} has no string id")
        if record_id in rows:
            raise ValueError(f"duplicate prediction id: {record_id}")
        rows[record_id] = row
    return rows


def _inventory_counts(row: dict[str, Any]) -> list[dict[str, int]]:
    """Return one category-count mapping per valid stage-1 source pack.

    ``by_category`` is an across-pack aggregate and can correctly have more
    than three excerpts.  Cap pressure must instead be measured from each raw
    response, where the JSON schema imposes the three-excerpt limit.
    """
    inventory = row.get("staged_run", {}).get("inventory", {}).get("by_category", {})
    if set(inventory) != set(FACT_INVENTORY_CATEGORIES):
        raise ValueError("prediction does not contain EXP171 v1 fact-inventory categories")
    raw_responses = row.get("staged_run", {}).get("inventory", {}).get("raw_responses", [])
    if not isinstance(raw_responses, list) or not raw_responses:
        raise ValueError("prediction has no stage-1 raw responses")
    counts_by_pack: list[dict[str, int]] = []
    for raw_response in raw_responses:
        try:
            parsed = json.loads(raw_response)
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(parsed, dict) or set(parsed) != set(FACT_INVENTORY_CATEGORIES):
            continue
        counts: dict[str, int] = {}
        for category in FACT_INVENTORY_CATEGORIES:
            values = parsed[category]
            if not isinstance(values, list) or len(values) > 3:
                break
            counts[category] = len(values)
        if len(counts) == len(FACT_INVENTORY_CATEGORIES):
            counts_by_pack.append(counts)
    if not counts_by_pack:
        raise ValueError("prediction has no valid stage-1 source-pack inventory")
    return counts_by_pack


def _eligible_items(record: dict[str, Any]) -> set[str]:
    """Return metadata-only audit slices, never label or prediction routes."""
    meta = record.get("meta", {})
    law = str(meta.get("적용계약법", ""))
    contract = str(meta.get("계약방법", ""))
    award = str(meta.get("낙찰방법", ""))
    joint = str(meta.get("공동도급구성방식", ""))
    eligible = {"v3", "v9", "v19", "v24"}
    if law == "지방계약법" and (contract == "수의계약" or award == "소액수의견적"):
        eligible.add("v8")
    if joint and joint not in {"미기재", "미입력", "없음", "None"}:
        eligible.add("v21")
    if award == "협상에의한계약":
        eligible.add("v22")
    if law == "지방계약법" and award == "협상에의한계약":
        eligible.add("v23")
    return eligible


def build_audit(records: list[dict[str, Any]], predictions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Summarize cap pressure without reading labels or final decisions."""
    record_ids = {record["id"] for record in records}
    missing = sorted(record_ids - set(predictions))
    extra = sorted(set(predictions) - record_ids)
    if missing or extra:
        raise ValueError(f"prediction/record ids differ; missing={missing[:3]}, extra={extra[:3]}")

    category_counts: dict[str, Counter[int]] = {
        category: Counter() for category in FACT_INVENTORY_CATEGORIES
    }
    relation_rows: dict[str, dict[str, int]] = {
        item: {"eligible_records": 0, "any_category_at_cap": 0, "all_required_categories_at_cap": 0}
        for item in RELATION_REQUIREMENTS
    }
    missing_stage = 0
    stage_context_count = 0
    for record in records:
        row = predictions[record["id"]]
        try:
            counts_by_pack = _inventory_counts(row)
        except ValueError:
            missing_stage += 1
            continue
        stage_context_count += len(counts_by_pack)
        for counts in counts_by_pack:
            for category, count in counts.items():
                category_counts[category][count] += 1
        for item in _eligible_items(record):
            requirement = RELATION_REQUIREMENTS[item]
            categories = requirement["categories"]
            relation_rows[item]["eligible_records"] += 1
            at_cap = [
                any(counts[category] == 3 for counts in counts_by_pack)
                for category in categories
            ]
            if any(at_cap):
                relation_rows[item]["any_category_at_cap"] += 1
            if all(at_cap):
                relation_rows[item]["all_required_categories_at_cap"] += 1

    def rate(numerator: int, denominator: int) -> float:
        return round(numerator / denominator, 4) if denominator else 0.0

    return {
        "audit_kind": "label_blind_source_first_relation_capacity_v1",
        "label_inputs_read": False,
        "final_judgments_read": False,
        "record_count": len(records),
        "records_missing_valid_stage_inventory": missing_stage,
        "valid_stage_context_count": stage_context_count,
        "inventory_cap_per_category": 3,
        "category_excerpt_count_distribution": {
            category: {
                str(count): category_counts[category][count]
                for count in range(4)
            }
            for category in FACT_INVENTORY_CATEGORIES
        },
        "category_cap_rate": {
            category: rate(category_counts[category][3], sum(category_counts[category].values()))
            for category in FACT_INVENTORY_CATEGORIES
        },
        "relation_requirements": {
            item: {
                **requirement,
                **relation_rows[item],
                "any_category_at_cap_rate": rate(
                    relation_rows[item]["any_category_at_cap"],
                    relation_rows[item]["eligible_records"],
                ),
                "all_required_categories_at_cap_rate": rate(
                    relation_rows[item]["all_required_categories_at_cap"],
                    relation_rows[item]["eligible_records"],
                ),
            }
            for item, requirement in RELATION_REQUIREMENTS.items()
        },
        "interpretation": (
            "A cap hit proves only that the three-slot category has no room for an additional "
            "source excerpt. It does not establish a missing fact, a violation, or a quality gain."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = load_records(args.records)
    audit = build_audit(records, _read_predictions(args.predictions))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
