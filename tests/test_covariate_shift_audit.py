from __future__ import annotations

from src.pps_ai.covariate_shift_audit import (
    ITEMS,
    poststratification_weights,
    stress_metrics,
)


def test_poststratification_weights_normalize_supported_population() -> None:
    weights, support = poststratification_weights(
        {"a": 50, "b": 50}, {"a": 80, "b": 20, "c": 1},
    )
    assert weights == {"a": 1.6, "b": 0.4}
    assert support["unsupported_population_counts"] == {"c": 1}
    assert support["mean_dev_record_weight"] == 1.0


def test_stress_metrics_reweights_fixed_predictions_without_mutation() -> None:
    labels = {
        "a": {item: int(item == "v1") for item in ITEMS},
        "b": {item: 0 for item in ITEMS},
    }
    predictions = {
        "a": {item: 0 for item in ITEMS},
        "b": {item: int(item == "v1") for item in ITEMS},
    }
    result = stress_metrics(
        labels, predictions, {"a": "rare", "b": "common"},
        {"rare": 0.2, "common": 1.8},
    )
    assert result["items"]["v1"]["raw"]["fp"] == 1.0
    assert result["items"]["v1"]["weighted"]["fp"] == 1.8
    assert result["items"]["v1"]["weighted"]["fn"] == 0.2
