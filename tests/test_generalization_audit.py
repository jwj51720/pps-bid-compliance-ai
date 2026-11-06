"""Generalization shift metric tests."""

from __future__ import annotations

from src.pps_ai.generalization_audit import compare_cohorts, price_band


def test_price_band_uses_organizer_threshold_boundaries() -> None:
    assert price_band(None) == "<MISSING>"
    assert price_band(99_999_999) == "lt_100m"
    assert price_band(100_000_000) == "100m_to_lt_150m"
    assert price_band(230_000_000) == "230m_to_lt_330m"
    assert price_band(350_000_000) == "350m_to_lt_500m"
    assert price_band(500_000_000) == "ge_500m"


def test_compare_cohorts_flags_large_binary_shift() -> None:
    def cohort(records: int, active: int) -> dict[str, object]:
        return {
            "records": records,
            "categorical_counts": {"x": {"A": records}},
            "continuous_values": {"x": [1.0] * records},
            "binary_counts": {"route": active},
        }

    result = compare_cohorts(
        cohort(10, 8), cohort(100, 20),
        rate_difference_gate=0.1, risk_ratio_low=0.67, risk_ratio_high=1.5,
    )
    route = result["binary"]["route"]
    assert route["risk_ratio"] == 4.0
    assert route["large_shift"] is True
    assert result["categorical"]["x"]["total_variation"] == 0.0
