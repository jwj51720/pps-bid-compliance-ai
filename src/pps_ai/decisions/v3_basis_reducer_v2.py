"""Source-concordant v3 reducer accepting single or aggregate monetary requirements."""

from __future__ import annotations

from typing import Any, Mapping

from .v3_keyed_serialization import adapt_keyed_response
from .v3_monetary import decide_v3_monetary_with_bases


def decide_v3_basis_v2(
    record: Mapping[str, Any],
    view: Mapping[str, Any],
    response: Mapping[str, Any],
    baseline_value: int,
    baseline_evidence: str,
) -> tuple[int, str, dict[str, Any]]:
    adapted = adapt_keyed_response(response, view)
    if adapted is None:
        return baseline_value, baseline_evidence, {
            "valid": False,
            "fallback": True,
            "decision": "BASELINE",
            "reason": "invalid_keyed_response",
            "observations": [],
        }
    return decide_v3_monetary_with_bases(
        record,
        view,
        adapted,
        baseline_value,
        baseline_evidence,
        accepted_bases={"SINGLE_CONTRACT", "AGGREGATE"},
    )

