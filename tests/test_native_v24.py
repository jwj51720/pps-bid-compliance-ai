from __future__ import annotations

import json

from src.pps_ai.decisions.v24_relation import decide_v24
from src.pps_ai.views.v24_relation import build_v24_relation_view


def _record(texts: list[str]) -> dict[str, object]:
    return {
        "id": "N1",
        "meta": {
            "배정예산금액": 110000000,
            "입찰추정가격": 100000000,
            "계약방법": "일반경쟁",
            "지역제한여부": "N",
            "제한지역코드목록": None,
            "업종제한여부": "N",
            "면허업종제한목록": None,
        },
        "docs": [
            {"doc_id": f"D{index}", "type": "공고문" if index == 0 else "규격서", "text": text}
            for index, text in enumerate(texts)
        ],
    }


def _response(value: dict[str, object]) -> dict[str, object]:
    return {
        "finish_reason": "stop", "invalid": False,
        "content": json.dumps(value, ensure_ascii=False),
    }


def _neutral() -> dict[str, dict[str, object]]:
    return {
        "amount": {
            "comparable": "N", "different": "N", "meta_field": "NONE",
            "document_role": "UNKNOWN", "document_value": None, "source_id": None,
        },
        "contract": {
            "comparable": "N", "different": "N", "meta_field": "NONE",
            "document_role": "UNKNOWN", "document_value": None, "source_id": None,
        },
        "region": {
            "comparable": "N", "different": "N", "meta_field": "NONE",
            "document_role": "UNKNOWN", "document_value": None, "source_id": None,
        },
        "industry": {
            "comparable": "N", "different": "N", "meta_field": "NONE",
            "document_role": "UNKNOWN", "document_value": None, "source_id": None,
        },
    }


def test_v24_view_inspects_every_document_and_keeps_exact_spans() -> None:
    record = _record([
        "계약방법은 제한경쟁입니다.",
        "납품지는 서울이며 사업예산은 110,000,000원입니다.",
    ])
    view = build_v24_relation_view(record)
    assert len(view["document_coverage"]) == 2
    assert all(row["inspected"] for row in view["document_coverage"])
    for candidates in view["candidates"].values():
        for candidate in candidates:
            document = record["docs"][candidate.document_order]
            assert document["text"][candidate.start:candidate.end] == candidate.text


def test_v24_reducer_rejects_award_method_as_contract_method() -> None:
    record = _record(["계약방법은 협상에 의한 계약입니다."])
    view = build_v24_relation_view(record)
    value = _neutral()
    source_id = view["candidates"]["contract"][0].source_id
    value["contract"] = {
        "comparable": "Y", "different": "Y", "meta_field": "CONTRACT_METHOD",
        "document_role": "AWARD_METHOD", "document_value": "협상에 의한 계약",
        "source_id": source_id,
    }
    verdict, evidence, diagnostic = decide_v24(record, view, _response(value))
    assert verdict == 0
    assert evidence == ""
    assert not diagnostic["axes"]["contract"]["role_valid"]


def test_v24_reducer_accepts_explicit_contract_method_conflict() -> None:
    record = _record(["계약방법은 제한경쟁입니다."])
    view = build_v24_relation_view(record)
    value = _neutral()
    source_id = view["candidates"]["contract"][0].source_id
    value["contract"] = {
        "comparable": "Y", "different": "Y", "meta_field": "CONTRACT_METHOD",
        "document_role": "CONTRACT_METHOD", "document_value": "제한경쟁",
        "source_id": source_id,
    }
    verdict, evidence, diagnostic = decide_v24(record, view, _response(value))
    assert verdict == 1
    assert evidence in record["docs"][0]["text"]
    assert diagnostic["axes"]["contract"]["explicit_contradiction"]


def test_v24_reducer_requires_axis_matching_source() -> None:
    record = _record(["계약방법은 제한경쟁이고 사업예산은 110,000,000원입니다."])
    view = build_v24_relation_view(record)
    value = _neutral()
    amount_source = view["candidates"]["amount"][0].source_id
    value["contract"] = {
        "comparable": "Y", "different": "Y", "meta_field": "CONTRACT_METHOD",
        "document_role": "CONTRACT_METHOD", "document_value": "제한경쟁",
        "source_id": amount_source,
    }
    verdict, _, diagnostic = decide_v24(record, view, _response(value))
    assert verdict == 0
    assert not diagnostic["axes"]["contract"]["source_axis_valid"]
