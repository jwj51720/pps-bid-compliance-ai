from __future__ import annotations

import pytest

from scripts.merge_prediction_retry_panel import merge_predictions


def test_merge_predictions_replaces_only_exact_versioned_panel() -> None:
    base = [{"id": "A", "value": 1}, {"id": "B", "value": 2}]
    retry = [{"id": "B", "value": 3}]

    assert merge_predictions(base, retry, ["B"]) == [
        {"id": "A", "value": 1},
        {"id": "B", "value": 3},
    ]


def test_merge_predictions_rejects_partial_or_extra_retry_output() -> None:
    base = [{"id": "A"}, {"id": "B"}]

    with pytest.raises(ValueError, match="exactly match"):
        merge_predictions(base, [{"id": "A"}], ["A", "B"])
    with pytest.raises(ValueError, match="absent"):
        merge_predictions(base, [{"id": "C"}], ["C"])
