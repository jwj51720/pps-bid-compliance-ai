"""S003 source-only role probe contracts."""

from __future__ import annotations

import json

import pytest

from src.pps_ai.region_role_micro import _document_excerpt, parse_role_response


def test_excerpt_retains_exact_source_span() -> None:
    text = "앞부분 " + "가" * 400 + "[지역:r1|단위=기초] 업체 입찰참가" + "나" * 200
    start, excerpt = _document_excerpt(text, text[4:], 500)
    assert text[start:start + len(excerpt)] == excerpt
    assert "[지역:r1|단위=기초]" in excerpt
    assert len(excerpt) == 500


def test_role_response_requires_exact_quote() -> None:
    source = "경기도 소재 업체만 입찰할 수 있습니다."
    valid = {"role": "BIDDER_QUALIFICATION", "unit": "PROVINCE", "quote": "경기도 소재 업체"}
    assert parse_role_response(json.dumps(valid), source) == valid
    valid["quote"] = "경기도 업체"
    with pytest.raises(ValueError, match="exact"):
        parse_role_response(json.dumps(valid), source)


def test_role_response_rejects_non_unclear_empty_quote() -> None:
    with pytest.raises(ValueError, match="requires source quote"):
        parse_role_response(
            json.dumps({"role": "EVALUATION", "unit": "UNSPECIFIED", "quote": ""}),
            "지역업체 가점 3점",
        )
