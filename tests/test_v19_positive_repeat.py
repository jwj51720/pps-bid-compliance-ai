from __future__ import annotations

from src.pps_ai.v19_positive_repeat import (
    adapt_single_json_fence,
    positive_f1,
    repeat_gate,
)


def _rows(tp_kept: int, fp_kept: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(6):
        rows.append({
            "truth": 1,
            "repeat_value": 1 if index < tp_kept else 0,
            "semantic_valid": True,
        })
    for index in range(4):
        rows.append({
            "truth": 0,
            "repeat_value": 1 if index < fp_kept else 0,
            "semantic_valid": True,
        })
    return rows


def test_positive_f1_uses_positive_class_confusion_counts() -> None:
    assert positive_f1(6, 4, 0) == 0.75
    assert positive_f1(6, 3, 0) == 0.8
    assert positive_f1(5, 2, 1) == 10 / 13


def test_repeat_gate_requires_actual_f1_improvement() -> None:
    failed = repeat_gate(_rows(5, 3), baseline_f1=0.75)
    passed = repeat_gate(_rows(6, 3), baseline_f1=0.75)
    assert failed["status"] == "FAIL"
    assert failed["checks"]["consensus_f1_strictly_improves"] is False
    assert passed["status"] == "PASS"
    assert passed["consensus"] == {"tp": 6, "fp": 3, "fn": 0, "f1": 0.8}


def test_repeat_gate_fails_when_any_response_is_semantically_invalid() -> None:
    rows = _rows(6, 3)
    rows[0]["semantic_valid"] = False
    report = repeat_gate(rows, baseline_f1=0.75)
    assert report["status"] == "FAIL"
    assert report["checks"]["all_semantic_valid"] is False


def test_single_json_fence_adapter_preserves_inner_payload_exactly() -> None:
    inner = '{\n  "observations": {"R01": {"quoted_text": "원문"}}\n}'
    response = {"content": f"```json\n{inner}\n```", "finish_reason": "stop"}
    adapted, audit = adapt_single_json_fence(response)
    assert adapted["content"] == inner
    assert audit == {
        "recovered": True,
        "reason": "single_outer_json_fence",
        "inner_object_exact": True,
    }
    assert response["content"].startswith("```json")


def test_single_json_fence_adapter_rejects_surrounding_text() -> None:
    response = {"content": "설명\n```json\n{}\n```"}
    adapted, audit = adapt_single_json_fence(response)
    assert adapted == response
    assert audit == {"recovered": False, "reason": "no_single_outer_fence"}
