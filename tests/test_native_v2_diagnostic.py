"""V2 response parsing keeps malformed output and non-source quotes negative."""

from __future__ import annotations

import json

from src.pps_ai.domain.models import NoticeDocument, NoticeRecord
from src.pps_ai.native_v2_diagnostic import parse_v2_response
from src.pps_ai.views.v2_performance import build_v2_performance_view_v2


def _view():
    document = NoticeDocument.from_raw("n1", 0, {
        "doc_id": "D0", "type": "공고문",
        "text": "입찰 참가자격: 최근 3년간 물품 공급 실적 3천만원 이상인 자.",
    })
    record = NoticeRecord("n1", (document,), {}, {}, {}, {})
    return build_v2_performance_view_v2(record)


def _response(**changed):
    value = {
        "performance_participation": "Y",
        "procurement_role": "purchase_supply",
        "explicit_allowance": "N",
        "enterprise_rule_applies": "N",
        "quote": "최근 3년간 물품 공급 실적 3천만원 이상인 자",
    } | changed
    return {"finish_reason": "stop", "invalid": False,
            "content": json.dumps(value, ensure_ascii=False)}


def test_v2_parser_accepts_exact_source_quote() -> None:
    result = parse_v2_response(_response(), _view())
    assert result["valid"] is True
    assert result["axes"]["procurement_role"] == "purchase_supply"
    assert result["source_ids"] == ["P001"]


def test_v2_parser_rejects_paraphrase_and_malformed_axis() -> None:
    assert parse_v2_response(_response(quote="비슷한 물품 실적"), _view())[
        "reason"
    ] == "quote_not_in_source"
    assert parse_v2_response(_response(procurement_role=["purchase_supply"]), _view())[
        "reason"
    ] == "invalid_axis"


def test_v2_parser_rejects_length_and_nonparticipation_quote() -> None:
    assert parse_v2_response({**_response(), "finish_reason": "length"}, _view())[
        "valid"
    ] is False
    assert parse_v2_response(
        _response(performance_participation="N"), _view(),
    )["reason"] == "quote_for_nonpositive_axis"
