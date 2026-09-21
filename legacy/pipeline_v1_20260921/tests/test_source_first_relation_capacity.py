from __future__ import annotations

import json

from scripts.audit_source_first_relation_capacity import build_audit
from src.schema import FACT_INVENTORY_CATEGORIES


def _prediction(record_id: str, count: int) -> dict:
    raw = {
        category: ["source" for _ in range(count)]
        for category in FACT_INVENTORY_CATEGORIES
    }
    return {
        "id": record_id,
        "staged_run": {
            "inventory": {
                "by_category": {
                    category: [["D0", "source"] for _ in range(count)]
                    for category in FACT_INVENTORY_CATEGORIES
                },
                "raw_responses": [json.dumps(raw, ensure_ascii=False)],
            }
        },
        "judgment": {"v1": 1},
    }


def test_relation_capacity_audit_excludes_labels_and_final_judgments() -> None:
    records = [
        {
            "id": "A",
            "meta": {"적용계약법": "지방계약법", "계약방법": "수의계약", "낙찰방법": "협상에의한계약", "공동도급구성방식": "공동이행"},
            "docs": [],
        },
        {
            "id": "B",
            "meta": {"적용계약법": "국가계약법", "계약방법": "일반경쟁", "낙찰방법": "적격심사", "공동도급구성방식": "미기재"},
            "docs": [],
        },
    ]
    audit = build_audit(records, {"A": _prediction("A", 3), "B": _prediction("B", 1)})

    assert audit["label_inputs_read"] is False
    assert audit["final_judgments_read"] is False
    assert audit["category_cap_rate"]["일정_설명회"] == 0.5
    assert audit["relation_requirements"]["v23"]["eligible_records"] == 1
    assert audit["relation_requirements"]["v23"]["any_category_at_cap"] == 1
    assert audit["relation_requirements"]["v8"]["eligible_records"] == 1
