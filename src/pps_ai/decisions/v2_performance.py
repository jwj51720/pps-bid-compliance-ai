"""V2-only projection from Gemma observations and organizer price metadata."""

from __future__ import annotations

from typing import Any, Mapping


GENERAL_GOODS_SERVICES_THRESHOLD = 230_000_000
ENTERPRISE_GOODS_SERVICES_THRESHOLD = 710_000_000
AXES = (
    "performance_participation", "procurement_role",
    "explicit_allowance", "enterprise_rule_applies",
)
ROLES = {"manufacture", "purchase_supply", "service", "works", "other", "U"}


def decide_v2_performance(
    axes: Mapping[str, str], metadata: Mapping[str, Any], *, valid_quote: bool,
) -> int:
    """Apply only the v32 conjunction; never mine source text for a label."""
    if set(axes) != set(AXES):
        raise ValueError("v2 observation axes differ")
    if axes["performance_participation"] not in {"Y", "N", "U"}:
        raise ValueError("invalid performance_participation")
    if axes["procurement_role"] not in ROLES:
        raise ValueError("invalid procurement_role")
    if axes["explicit_allowance"] not in {"Y", "N", "U"}:
        raise ValueError("invalid explicit_allowance")
    if axes["enterprise_rule_applies"] not in {"Y", "N", "U"}:
        raise ValueError("invalid enterprise_rule_applies")
    price = metadata.get("입찰추정가격")
    if price is not None and (isinstance(price, bool) or not isinstance(price, int)
                              or price < 0):
        raise ValueError("invalid organizer estimated price")
    if metadata.get("적용계약법") not in {"국가계약법", "지방계약법"}:
        return 0
    if (
        axes["performance_participation"] != "Y"
        or axes["procurement_role"] not in {
            "manufacture", "purchase_supply", "service",
        }
        or axes["explicit_allowance"] != "N"
        or not valid_quote
        or price is None
    ):
        return 0
    enterprise = axes["enterprise_rule_applies"]
    if enterprise == "Y":
        threshold = ENTERPRISE_GOODS_SERVICES_THRESHOLD
    elif enterprise == "N":
        threshold = GENERAL_GOODS_SERVICES_THRESHOLD
    elif price < GENERAL_GOODS_SERVICES_THRESHOLD:
        # The lower threshold suffices regardless of the uncertain higher rule.
        threshold = GENERAL_GOODS_SERVICES_THRESHOLD
    else:
        return 0
    return int(price < threshold)
