from __future__ import annotations

from scripts.audit_navigation_label_alignment import (
    audit,
    navigation_contains_gold,
)
from src.schema import ITEMS


def _judgment() -> dict:
    return {
        item: {"위반여부": 0, "근거문구": ""}
        for item in ITEMS
    }


def test_navigation_contains_gold_resolves_whitespace_but_not_keywords() -> None:
    assert navigation_contains_gold(
        "서울시에 본사를 둔 업체",
        ["참가자는 서울시에  본사를 둔 업체로 제한한다"],
    )
    assert not navigation_contains_gold("서울시 제한", ["서울시 업체"])


def test_audit_separates_navigation_hit_from_final_judgment() -> None:
    model = _judgment()
    final = _judgment()
    predictions = [
        {
            "id": "A",
            "judgment": final,
            "decision_provenance": {"model_judgment": model},
            "staged_run": {
                "inventory": {"by_category": {"facts": [["D0", "실적 3억원 이상 제한"]]}}
            },
        }
    ]
    label = {"id": "A"}
    for index, item in enumerate(ITEMS, 1):
        label[item] = "1" if item == "v2" else "0"
        label[f"e{index}"] = "실적 3억원 이상" if item == "v2" else ""

    result = audit(predictions, [label], "per_pass_or")
    v2 = next(row for row in result["per_item"] if row["item"] == "v2")

    assert v2["navigation_hit"] == 1
    assert v2["final_fn_navigation_hit"] == 1
    assert result["totals"]["navigation_recall_on_nonblank_gold"] == 1.0
