from src.pps_ai.python_owner_audit import compare_binary_rates


def test_compare_binary_rates_reports_shift_and_ratio() -> None:
    result = compare_binary_rates({"a": 10, "b": 0}, {"a": 20, "b": 5}, 100, 100)
    assert result["a"]["rate_difference_dev_minus_population"] == -0.1
    assert result["a"]["risk_ratio_dev_over_population"] == 0.5
    assert result["b"]["dev_rate"] == 0.0
    assert result["b"]["population_rate"] == 0.05
