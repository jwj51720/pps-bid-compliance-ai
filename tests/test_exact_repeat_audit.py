from __future__ import annotations

from collections import Counter

from src.pps_ai.exact_repeat_audit import _field_disagreements


def test_field_disagreements_are_candidate_and_field_specific() -> None:
    left = [
        {"source_id": "R1", "role": "A", "value": "x"},
        {"source_id": "R2", "role": "B", "value": "y"},
    ]
    right = [
        {"source_id": "R1", "role": "A", "value": "z"},
        {"source_id": "R2", "role": "C", "value": "y"},
    ]
    assert _field_disagreements(left, right, ("role", "value")) == Counter({
        "value": 1, "role": 1,
    })


def test_field_disagreements_reject_candidate_key_drift() -> None:
    assert _field_disagreements(
        [{"source_id": "R1"}], [{"source_id": "R2"}], (),
    ) == Counter({"candidate_key_set": 1})
