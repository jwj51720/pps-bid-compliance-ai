"""Native v1 diagnostic never silently turns uncertainty into a decision."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.pps_ai.domain.models import NoticeDocument, NoticeRecord
from src.pps_ai.native_v1_diagnostic import (
    load_native_v1_config, parse_v1_axis_response, parse_v1_response,
)
from src.pps_ai.views.v1_qualification import build_v1_qualification_view_v2


ROOT = Path(__file__).resolve().parents[1]


def _view():
    document = NoticeDocument.from_raw("n1", 0, {
        "doc_id": "N", "type": "공고문",
        "text": "입찰 참가자격: 대학만 참가 가능함.",
    })
    record = NoticeRecord("n1", (document,), {}, {}, {}, {})
    return build_v1_qualification_view_v2(record)


def _response(content: str) -> dict[str, object]:
    return {"content": content, "finish_reason": "stop", "invalid": False}


def test_v1_positive_requires_exact_source_quote() -> None:
    view = _view()
    valid = parse_v1_response(
        _response('{"state":"Y","quote":"대학만 참가 가능함"}'), view,
    )
    assert valid["state"] == "Y"
    assert valid["valid"] is True
    assert valid["source_ids"]
    missing = parse_v1_response(
        _response('{"state":"Y","quote":"대학교로 제한함"}'), view,
    )
    assert missing == {
        "state": "U", "quote": None, "valid": False,
        "reason": "quote_not_in_source",
    }


def test_v1_malformed_and_unknown_are_not_zero() -> None:
    view = _view()
    malformed = parse_v1_response(_response("not json"), view)
    assert malformed["state"] == "U"
    assert malformed["valid"] is False
    unknown = parse_v1_response(_response('{"state":"U","quote":null}'), view)
    assert unknown["state"] == "U"
    assert unknown["valid"] is True


def test_native_v1_manifest_has_no_reference_dependency() -> None:
    candidate = ROOT / "experiments/manifests/clean_exp_n001_v1_fast_diagnostic_v1.json"
    config = load_native_v1_config(candidate, ROOT)
    assert "reference" not in config.raw
    assert config.raw["run"]["mode"] == "fast20_observation"
    with pytest.raises(ValueError, match="audit-only"):
        load_native_v1_config(
            ROOT / "experiments/manifests/clean_native_v1_source_audit_v2.json", ROOT,
        )


def test_explicit_state_manifest_selects_v3_without_reference() -> None:
    candidate = ROOT / "experiments/manifests/clean_exp_n002_v1_explicit_state_fast_v1.json"
    config = load_native_v1_config(candidate, ROOT)
    assert config.raw["prompt"]["task"] == "native-v1-explicit-state-observation-v3"
    assert "reference" not in config.raw


def test_bidder_relation_manifest_selects_v5_without_reference() -> None:
    candidate = ROOT / "experiments/manifests/clean_exp_n004_v1_bidder_relation_fast_v1.json"
    config = load_native_v1_config(candidate, ROOT)
    assert config.raw["prompt"]["task"] == "native-v1-bidder-relation-observation-v5"
    assert "reference" not in config.raw


def test_axis_reducer_excludes_other_item_restrictions() -> None:
    view = _view()
    excluded = parse_v1_axis_response(
        _response('{"target":"N","allowed":"U","quote":null}'), view,
    )
    assert excluded["state"] == "N"
    violation = parse_v1_axis_response(
        _response(
            '{"target":"Y","allowed":"N",'
            '"quote":"대학만 참가 가능함"}'
        ),
        view,
    )
    assert violation["state"] == "Y"
    assert violation["source_ids"]
