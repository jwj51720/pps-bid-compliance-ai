"""Conservative, source-traced applicability exclusions.

This module does not detect a violation and never searches notice text.  It
only identifies an item that the organizer-provided metadata or exact product
CSV makes *impossible* under that item's published decision card.  Everything
else remains active for Gemma.  The registry is intentionally small: an
unproven convenience filter is worse than leaving an item in the prompt.
"""

from __future__ import annotations

import re
from typing import Any

from src.data import competition_product_fact


_DECIMAL = re.compile(r"^\d+$")
_NON_NEGOTIATED_AWARD_METHODS = {
    "적격심사제",
    "소액수의견적",
    "규격가격동시입찰",
    "2단계경쟁입찰",
}

# This is audit metadata, not prompt text.  Each entry must name the exact
# decision-card condition that makes the resulting 0 logically safe.
GATE_PROVENANCE: dict[str, dict[str, str]] = {
    "exact_noncompetition": {
        "items": "v10,v11,v13",
        "source": "decision_cards_v6 v10/v11/v13 0 조건 + competition_products_v1 exact-code index",
        "condition": "metadata has product codes and none matches the organizer competition-product index",
    },
    "below_100m": {
        "items": "v15,v16",
        "source": "decision_cards_v6 v15/v16 1 조건",
        "condition": "입찰추정가격 is an exact integer below 100,000,000 KRW",
    },
    "at_least_100m": {
        "items": "v17,v18",
        "source": "decision_cards_v6 v17/v18 1 조건",
        "condition": "입찰추정가격 is an exact integer at or above 100,000,000 KRW",
    },
    "explicit_non_negotiated": {
        "items": "v22",
        "source": "decision_cards_v6 v22 1 조건",
        "condition": "낙찰방법 is one of the organizer's explicit non-negotiated values",
    },
    "national_or_explicit_non_negotiated": {
        "items": "v23",
        "source": "decision_cards_v6 v23 1/0 조건",
        "condition": "적용계약법 is 국가계약법, or 지방계약법 with explicit non-negotiated 낙찰방법",
    },
}


def _exact_estimated_price(record: dict[str, Any]) -> int | None:
    """Parse only an unambiguous organizer numeric value; never coerce prose."""
    value = record["meta"].get("입찰추정가격")
    text = str(value).strip() if value is not None else ""
    return int(text) if _DECIMAL.fullmatch(text) else None


def safe_inactive_items(
    record: dict[str, Any], products: dict[str, dict[str, str]],
) -> dict[str, str]:
    """Return only items whose card prerequisite is explicitly impossible.

    A returned mapping is ``item -> registry reason``.  No missing/unknown
    metadata value can deactivate an item.  In particular, this deliberately
    excludes local-small-contract and competition-to-general shortcuts: their
    dev coverage audit found counterexamples, so they are not source-safe.
    """
    inactive: dict[str, str] = {}
    product_status = competition_product_fact(record, products)["status"]
    if product_status == "not_matched":
        inactive.update({item: "exact_noncompetition" for item in ("v10", "v11", "v13")})

    price = _exact_estimated_price(record)
    if price is not None:
        if price < 100_000_000:
            inactive.update({item: "below_100m" for item in ("v15", "v16")})
        else:
            inactive.update({item: "at_least_100m" for item in ("v17", "v18")})

    meta = record["meta"]
    award_method = str(meta.get("낙찰방법") or "").strip()
    explicitly_non_negotiated = award_method in _NON_NEGOTIATED_AWARD_METHODS
    if explicitly_non_negotiated:
        inactive["v22"] = "explicit_non_negotiated"

    contract_law = str(meta.get("적용계약법") or "").strip()
    if contract_law == "국가계약법" or (
        contract_law == "지방계약법" and explicitly_non_negotiated
    ):
        inactive["v23"] = "national_or_explicit_non_negotiated"
    return inactive
