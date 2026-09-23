"""Tests for Python owner stage attribution math."""

from src.pps_ai.owner_stage_attribution import binary_metrics, stage_attribution


def test_binary_metrics_positive_f1() -> None:
    result = binary_metrics({"a": 1, "b": 1, "c": 0}, {"a": 1, "b": 0, "c": 1})
    assert result["tp"] == 1
    assert result["fp"] == 1
    assert result["fn"] == 1
    assert result["f1"] == 0.5


def test_stage_attribution_reports_f1_half_precision_threshold() -> None:
    truth = {"a": 1, "b": 1, "c": 0, "d": 0}
    initial = {"a": 1, "b": 0, "c": 0, "d": 0}
    final = {"a": 1, "b": 1, "c": 1, "d": 0}
    result = stage_attribution(initial, final, truth)
    assert result["initial"]["f1"] == 2 / 3
    assert result["expansion_precision"] == 0.5
    assert result["f1_improvement_precision_threshold"] == 1 / 3
    assert result["final"]["f1"] > result["initial"]["f1"]


def test_transition_integrity_components_include_removal() -> None:
    truth = {"a": 0, "b": 1}
    result = stage_attribution({"a": 1, "b": 0}, {"a": 0, "b": 1}, truth)
    assert result["transitions"]["zero_to_one_true"] == 1
    assert result["transitions"]["one_to_zero_corrected_false_positive"] == 1
    assert result["final"]["f1"] == 1.0
