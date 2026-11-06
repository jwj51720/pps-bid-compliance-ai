from src.pps_ai.python_policy_population import wilson_interval


def test_wilson_interval_bounds_and_sparse_positive() -> None:
    low, high = wilson_interval(0, 200)
    assert low == 0.0
    assert 0 < high < 0.02
    low, high = wilson_interval(7, 200)
    assert low < 7 / 200 < high
