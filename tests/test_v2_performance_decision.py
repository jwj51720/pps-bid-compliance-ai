"""V2 projection uses source-observed roles and organizer price only."""

import pytest

from src.pps_ai.decisions.v2_performance import decide_v2_performance


BASE_AXES = {
    "performance_participation": "Y",
    "procurement_role": "purchase_supply",
    "explicit_allowance": "N",
    "enterprise_rule_applies": "N",
}
BASE_METADATA = {"적용계약법": "국가계약법", "입찰추정가격": 153_636_364}


def test_purchase_supply_is_not_categorically_zero() -> None:
    assert decide_v2_performance(BASE_AXES, BASE_METADATA, valid_quote=True) == 1


@pytest.mark.parametrize("changed", [
    {"performance_participation": "N"},
    {"procurement_role": "works"},
    {"explicit_allowance": "Y"},
    {"explicit_allowance": "U"},
])
def test_required_observations_gate_positive(changed: dict[str, str]) -> None:
    axes = BASE_AXES | changed
    assert decide_v2_performance(axes, BASE_METADATA, valid_quote=True) == 0


def test_threshold_and_uncertain_enterprise_rule() -> None:
    assert decide_v2_performance(
        BASE_AXES, BASE_METADATA | {"입찰추정가격": 230_000_000},
        valid_quote=True,
    ) == 0
    unknown = BASE_AXES | {"enterprise_rule_applies": "U"}
    assert decide_v2_performance(unknown, BASE_METADATA, valid_quote=True) == 1
    assert decide_v2_performance(
        unknown, BASE_METADATA | {"입찰추정가격": 300_000_000},
        valid_quote=True,
    ) == 0
    enterprise = BASE_AXES | {"enterprise_rule_applies": "Y"}
    assert decide_v2_performance(
        enterprise, BASE_METADATA | {"입찰추정가격": 300_000_000},
        valid_quote=True,
    ) == 1


def test_evidence_and_law_are_required() -> None:
    assert decide_v2_performance(BASE_AXES, BASE_METADATA, valid_quote=False) == 0
    assert decide_v2_performance(
        BASE_AXES, BASE_METADATA | {"적용계약법": "불명"}, valid_quote=True,
    ) == 0


def test_unknown_or_extra_axis_is_rejected() -> None:
    with pytest.raises(ValueError):
        decide_v2_performance(BASE_AXES | {"extra": "Y"}, BASE_METADATA,
                              valid_quote=True)
