from __future__ import annotations

import json

from src.pps_ai.decisions.v24_multi_observation import decide_v24_multi
from src.pps_ai.views.v24_multi_observation import build_v24_multi_observation_view


def _record(texts: list[str]) -> dict[str, object]:
    return {
        "id": "N1",
        "meta": {
            "배정예산금액": 110000000,
            "입찰추정가격": 100000000,
            "계약방법": "일반경쟁",
            "지역제한여부": "Y",
            "제한지역코드목록": "경기도",
            "업종제한여부": "Y",
            "면허업종제한목록": "[학술연구용역(1169)]",
        },
        "docs": [
            {
                "doc_id": f"D{index}",
                "type": "공고문" if index == 0 else "규격서",
                "text": text,
            }
            for index, text in enumerate(texts)
        ],
    }


def _response(**overrides: object) -> dict[str, object]:
    value = {"amount": [], "contract": [], "region": [], "industry": []}
    value.update(overrides)
    return {
        "finish_reason": "stop",
        "invalid": False,
        "content": json.dumps(value, ensure_ascii=False),
    }


def test_table_aware_view_keeps_header_and_following_value() -> None:
    record = _record(["기초금액\n\n추정가격\n\n부가가치세\n\n110,000,000\n\n100,000,000\n\n10,000,000"])
    view = build_v24_multi_observation_view(record)
    texts = [candidate.text for candidate in view["candidates"]["amount"]]
    assert any("추정가격" in text and "110,000,000" in text for text in texts)
    for candidate in view["candidates"]["amount"]:
        assert record["docs"][candidate.document_order]["text"][candidate.start:candidate.end] == candidate.text


def test_view_inspects_each_document_and_distinguishes_missing_from_omitted() -> None:
    record = _record([
        "계약방법은 일반경쟁입니다.",
        "본점 소재지는 경기도로 제한합니다.",
    ])
    view = build_v24_multi_observation_view(record, max_axis_characters=1000)
    assert len(view["document_coverage"]) == 2
    assert all(row["inspected"] for row in view["document_coverage"])
    states = {
        row["state"] for rows in view["axis_coverage"].values() for row in rows
    }
    assert "NOT_FOUND" in states
    assert "FOUND_SELECTED" in states


def test_reducer_keeps_multiple_contract_statements_and_detects_one_conflict() -> None:
    record = _record(["입찰방법은 일반경쟁입니다.\n\n계약방법은 제한경쟁입니다."])
    view = build_v24_multi_observation_view(record)
    source = view["candidates"]["contract"][0].source_id
    response = _response(contract=[
        {"source_id": source, "role": "COMPETITION_METHOD", "competition_method": "GENERAL"},
        {"source_id": source, "role": "COMPETITION_METHOD", "competition_method": "LIMITED"},
    ])
    value, evidence, diagnostic = decide_v24_multi(record, view, response)
    assert value == 1
    assert evidence in record["docs"][0]["text"]
    assert diagnostic["mismatches"][0]["axis"] == "contract"


def test_reducer_ignores_award_method_for_contract_comparison() -> None:
    record = _record(["계약방법은 협상에 의한 계약입니다."])
    view = build_v24_multi_observation_view(record)
    source = view["candidates"]["contract"][0].source_id
    response = _response(contract=[{
        "source_id": source,
        "role": "AWARD_OR_NEGOTIATION_METHOD",
        "competition_method": "OTHER",
    }])
    value, evidence, diagnostic = decide_v24_multi(record, view, response)
    assert value == 0
    assert evidence == ""
    assert not diagnostic["mismatches"]


def test_reducer_compares_region_as_complete_set() -> None:
    record = _record(["본점 소재지는 경기도 또는 제주도로 제한합니다."])
    view = build_v24_multi_observation_view(record)
    source = view["candidates"]["region"][0].source_id
    response = _response(region=[{
        "source_id": source,
        "role": "BIDDER_LOCATION",
        "regions": ["경기도", "제주도"],
    }])
    value, _, diagnostic = decide_v24_multi(record, view, response)
    assert value == 1
    assert diagnostic["mismatches"][0]["actual"] == ["경기도", "제주특별자치도"]


def test_reducer_normalizes_organizer_region_placeholder() -> None:
    record = _record(["본점 소재지를 경기도로 제한합니다."])
    record["meta"]["제한지역코드목록"] = "[등록지역:r1|단위=기초|광역=경기도]"
    view = build_v24_multi_observation_view(record)
    source = view["candidates"]["region"][0].source_id
    response = _response(region=[{
        "source_id": source,
        "role": "BIDDER_LOCATION",
        "regions": ["경기도"],
    }])
    value, _, diagnostic = decide_v24_multi(record, view, response)
    assert value == 0
    assert not diagnostic["mismatches"]


def test_reducer_compares_industry_code_union() -> None:
    record = _record(["업종코드 1169 또는 업종코드 9901로 등록한 업체여야 합니다."])
    view = build_v24_multi_observation_view(record)
    source = view["candidates"]["industry"][0].source_id
    response = _response(industry=[{
        "source_id": source,
        "role": "BIDDER_MANDATORY_INDUSTRY",
        "industry_codes": ["1169", "9901"],
        "industry_names": [],
    }])
    value, _, diagnostic = decide_v24_multi(record, view, response)
    assert value == 1
    assert diagnostic["mismatches"][0]["axis"] == "industry"


def test_reducer_rejects_cross_axis_or_hallucinated_source_value() -> None:
    record = _record(["계약방법은 일반경쟁이고 본점 소재지는 경기도입니다."])
    view = build_v24_multi_observation_view(record)
    contract_source = view["candidates"]["contract"][0].source_id
    response = _response(region=[{
        "source_id": contract_source,
        "role": "BIDDER_LOCATION",
        "regions": ["제주도"],
    }])
    value, _, diagnostic = decide_v24_multi(record, view, response)
    assert value == 0
    assert not diagnostic["observations"]["region"][0]["source_valid"]


def test_invalid_enum_is_a_fallback_not_a_positive() -> None:
    record = _record(["계약방법은 제한경쟁입니다."])
    view = build_v24_multi_observation_view(record)
    source = view["candidates"]["contract"][0].source_id
    response = _response(contract=[{
        "source_id": source,
        "role": "COMPETITION_METHOD",
        "competition_method": "NOT_AN_ENUM",
    }])
    value, evidence, diagnostic = decide_v24_multi(record, view, response)
    assert value == 0
    assert evidence == ""
    assert diagnostic["fallback"]
