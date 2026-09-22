"""Native v22 parser and manifest invariants."""

from pathlib import Path

import pytest

from src.pps_ai.domain.models import NoticeDocument, NoticeRecord
from src.pps_ai.native_v22_diagnostic import (
    load_native_v22_config, parse_v22_phase_response, parse_v22_response,
)
from src.pps_ai.views.v22_briefing import build_v22_briefing_view


ROOT = Path(__file__).resolve().parents[1]


def _view():
    document = NoticeDocument.from_raw("n1", 0, {
        "doc_id": "D0", "type": "공고문",
        "text": "사업설명회에 불참한 업체는 제안서를 제출할 수 없습니다.",
    })
    return build_v22_briefing_view(NoticeRecord("n1", (document,), {}, {}, {}, {}))


def _response(content: str) -> dict[str, object]:
    return {"content": content, "finish_reason": "stop", "invalid": False}


def test_v22_positive_requires_all_axes_and_exact_quote() -> None:
    view = _view()
    valid = parse_v22_response(_response(
        '{"negotiated":"Y","briefing":"Y","exclusion":"Y",'
        '"quote":"불참한 업체는 제안서를 제출할 수 없습니다"}'
    ), view)
    assert valid["state"] == "Y"
    assert valid["valid"] is True
    nonnegotiated = parse_v22_response(_response(
        '{"negotiated":"N","briefing":"Y","exclusion":"Y",'
        '"quote":"불참한 업체는 제안서를 제출할 수 없습니다"}'
    ), view)
    assert nonnegotiated["state"] == "N"
    bad_quote = parse_v22_response(_response(
        '{"negotiated":"Y","briefing":"Y","exclusion":"Y",'
        '"quote":"불참자는 참여 불가"}'
    ), view)
    assert bad_quote["state"] == "U"
    assert bad_quote["reason"] == "quote_not_in_source"


def test_v22_unknown_is_not_silently_zero() -> None:
    result = parse_v22_response(_response(
        '{"negotiated":"Y","briefing":"U","exclusion":"U","quote":null}'
    ), _view())
    assert result["state"] == "U"
    assert result["valid"] is True


def test_native_v22_manifest_has_no_reference_dependency() -> None:
    candidate = ROOT / "experiments/manifests/clean_exp_n005_v22_briefing_fast_v1.json"
    config = load_native_v22_config(candidate, ROOT)
    assert "reference" not in config.raw
    assert config.cohort == "fast20"
    with pytest.raises(ValueError, match="audit-only"):
        load_native_v22_config(
            ROOT / "experiments/manifests/clean_native_v22_source_audit_v1.json", ROOT,
        )


def test_native_v22_holdout_selects_binary_owner() -> None:
    candidate = ROOT / "experiments/manifests/clean_exp_n005h_v22_briefing_holdout_v1.json"
    config = load_native_v22_config(candidate, ROOT)
    assert config.cohort == "holdout20"
    assert config.raw["decision"]["otherwise"] == 0


def test_native_v22_dev200_has_no_panel_or_reference() -> None:
    candidate = ROOT / "experiments/manifests/clean_exp_n005d_v22_briefing_dev200_v1.json"
    config = load_native_v22_config(candidate, ROOT)
    assert config.cohort == "dev200"
    assert config.panel_path is None
    assert "reference" not in config.raw


def test_v22_phase_parser_separates_evaluation_from_pre_submission_bar() -> None:
    view = _view()
    result = parse_v22_phase_response(_response(
        '{"negotiated":"Y","pre_submission_briefing":"N",'
        '"pre_submission_bar":"N","proposal_evaluation_session":"Y",'
        '"quote":null}'
    ), view)
    assert result["state"] == "N"
    assert result["valid"] is True
    assert result["axes"]["proposal_evaluation_session"] == "Y"


def test_native_v22_phase_manifest_selects_v2_without_reference() -> None:
    candidate = ROOT / "experiments/manifests/clean_exp_n006_v22_phase_fast_v1.json"
    config = load_native_v22_config(candidate, ROOT)
    assert config.raw["prompt"]["task"] == "native-v22-phase-relation-observation-v2"
    assert config.raw["decision"]["owner"] == "v22-phase-binary-conjunction-v2"
    assert "reference" not in config.raw
