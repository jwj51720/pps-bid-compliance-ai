"""V22 card-defined binary projection."""

import pytest

from src.pps_ai.decisions.v22_briefing import decide_v22_briefing, decide_v22_phase


def test_v22_requires_all_three_positive_relations() -> None:
    assert decide_v22_briefing({
        "negotiated": "Y", "briefing": "Y", "exclusion": "Y",
    }) == 1
    assert decide_v22_briefing({
        "negotiated": "Y", "briefing": "Y", "exclusion": "U",
    }) == 0
    assert decide_v22_briefing({
        "negotiated": "Y", "briefing": "N", "exclusion": "N",
    }) == 0


def test_v22_rejects_malformed_axes() -> None:
    with pytest.raises(ValueError, match="axes differ"):
        decide_v22_briefing({"briefing": "Y", "exclusion": "Y"})
    with pytest.raises(ValueError, match="invalid axis"):
        decide_v22_briefing({
            "negotiated": "Y", "briefing": "MAYBE", "exclusion": "Y",
        })


def test_v22_phase_ignores_evaluation_session_for_positive_conjunction() -> None:
    assert decide_v22_phase({
        "negotiated": "Y", "pre_submission_briefing": "Y",
        "pre_submission_bar": "Y", "proposal_evaluation_session": "Y",
    }) == 1
    assert decide_v22_phase({
        "negotiated": "Y", "pre_submission_briefing": "N",
        "pre_submission_bar": "N", "proposal_evaluation_session": "Y",
    }) == 0
