import pytest

from src.pps_ai.v5_role_quote_replay import parse_recovered_response


def _response(quote: str):
    import json

    return {"finish_reason": "stop", "invalid": False,
            "content": json.dumps({"role": "BIDDER_LOCATION", "quote": quote})}


def test_whitespace_only_quote_recovery_keeps_exact_source() -> None:
    task = {"source_texts": ["사업장 주 소재지가 서울시인 광고 대행사\n사업자등록증"]}
    result = parse_recovered_response(
        _response("사업장 주 소재지가 서울시인 광고 대행사 사업자등록증"), task,
    )
    assert result["quote"] == "사업장 주 소재지가 서울시인 광고 대행사\n사업자등록증"
    assert result["method"] == "WHITESPACE_UNIQUE"


def test_nonwhitespace_paraphrase_is_rejected() -> None:
    with pytest.raises(ValueError, match="cannot be recovered"):
        parse_recovered_response(_response("서울 거주 업체"), {"source_texts": ["경기도 업체"]})


def test_exact_quote_is_preferred_over_earlier_whitespace_match() -> None:
    task = {"source_texts": ["서울특별\n시 업체", "서울특별시 업체"]}
    result = parse_recovered_response(_response("서울특별시 업체"), task)
    assert result["quote"] == "서울특별시 업체"
    assert result["source_fragment_index"] == 1
    assert result["method"] == "BYTE_EXACT"
