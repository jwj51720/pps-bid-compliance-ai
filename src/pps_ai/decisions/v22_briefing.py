"""Card-defined binary projection for native v22 observations."""

from __future__ import annotations

from typing import Mapping


AXES = ("negotiated", "briefing", "exclusion")
PHASE_AXES = (
    "negotiated", "pre_submission_briefing", "pre_submission_bar",
    "proposal_evaluation_session",
)


def decide_v22_briefing(axes: Mapping[str, str]) -> int:
    if set(axes) != set(AXES):
        raise ValueError("v22 observation axes differ")
    if any(axes[key] not in {"Y", "N", "U"} for key in AXES):
        raise ValueError("v22 observation has invalid axis")
    return int(all(axes[key] == "Y" for key in AXES))


def decide_v22_phase(axes: Mapping[str, str]) -> int:
    if set(axes) != set(PHASE_AXES):
        raise ValueError("v22 phase observation axes differ")
    if any(axes[key] not in {"Y", "N", "U"} for key in PHASE_AXES):
        raise ValueError("v22 phase observation has invalid axis")
    return int(all(axes[key] == "Y" for key in (
        "negotiated", "pre_submission_briefing", "pre_submission_bar",
    )))
