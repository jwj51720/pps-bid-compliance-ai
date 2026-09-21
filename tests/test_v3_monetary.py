from __future__ import annotations

import json

from src.pps_ai.decisions.v3_monetary import decide_v3_monetary, parse_amount_won
from src.pps_ai.views.v3_monetary import build_v3_monetary_view


def _record(texts: list[str], estimate: int = 100_000_000) -> dict[str, object]:
    return {
        "id": "N1",
        "meta": {"입찰추정가격": estimate},
        "docs": [
            {"doc_id": f"D{index}", "type": "공고문" if index == 0 else "제안요청서", "text": text}
            for index, text in enumerate(texts)
        ],
    }


def _response(view: dict[str, object], **changes: object) -> dict[str, object]:
    observations = []
    for candidate in view["candidates"]:
        row = {
            "source_id": candidate.source_id,
            "role": "OTHER",
            "requirement_basis": "UNKNOWN",
            "mandatory": "UNKNOWN",
            "amount_surface": None,
        }
        row.update(changes)
        observations.append(row)
    return {
        "finish_reason": "stop",
        "invalid": False,
        "content": json.dumps({"observations": observations}, ensure_ascii=False),
    }


def test_amount_parser_normalizes_supported_units() -> None:
    assert parse_amount_won("455,000,000원") == 455_000_000
    assert parse_amount_won("3억 원") == 300_000_000
    assert parse_amount_won("1.5억원") == 150_000_000
    assert parse_amount_won("5천만원") == 50_000_000
    assert parse_amount_won("2500만원") == 25_000_000
    assert parse_amount_won("83,454천원") == 83_454_000
    assert parse_amount_won("1억원 또는 2억원") is None


def test_view_inspects_all_documents_and_keeps_exact_spans() -> None:
    record = _record([
        "참가자격으로 단일 용역 수행실적 2억원 이상인 업체여야 한다.",
        "실적증명서 서식: 계약금액 50,000,000원.",
        "금액 문구가 없는 문서입니다.",
    ])
    view = build_v3_monetary_view(record)
    assert len(view["document_coverage"]) == 3
    assert all(row["inspected"] for row in view["document_coverage"])
    assert len(view["candidates"]) == 2
    for candidate in view["candidates"]:
        document = record["docs"][candidate.document_order]
        assert document["text"][candidate.start:candidate.end] == candidate.text


def test_positive_uses_exact_surface_and_strict_greater_than() -> None:
    record = _record(["입찰참가자는 단일 계약 수행실적 2억원 이상이어야 합니다."])
    view = build_v3_monetary_view(record)
    response = _response(
        view,
        role="BID_QUALIFICATION",
        requirement_basis="SINGLE_CONTRACT",
        mandatory="YES",
        amount_surface="2억원",
    )
    value, evidence, diagnostic = decide_v3_monetary(record, view, response, 0, "")
    assert value == 1
    assert evidence in record["docs"][0]["text"]
    assert diagnostic["decision"] == "POSITIVE_PROOF"

    equal_record = _record(
        ["입찰참가자는 단일 계약 수행실적 1억원 이상이어야 합니다."],
        estimate=100_000_000,
    )
    equal_view = build_v3_monetary_view(equal_record)
    equal_response = _response(
        equal_view,
        role="BID_QUALIFICATION",
        requirement_basis="SINGLE_CONTRACT",
        mandatory="YES",
        amount_surface="1억원",
    )
    value, evidence, diagnostic = decide_v3_monetary(
        equal_record, equal_view, equal_response, 1, "old",
    )
    assert value == 0
    assert evidence == ""
    assert diagnostic["decision"] == "NEGATIVE_PROOF"


def test_evaluation_or_unverified_amount_falls_back() -> None:
    record = _record(["제안서 평가의 수행실적 2억원 이상은 5점이다."])
    view = build_v3_monetary_view(record)
    evaluation = _response(
        view,
        role="EVALUATION",
        requirement_basis="SINGLE_CONTRACT",
        mandatory="NO",
        amount_surface="2억원",
    )
    value, evidence, diagnostic = decide_v3_monetary(record, view, evaluation, 1, "base")
    assert (value, evidence) == (1, "base")
    assert diagnostic["fallback"]

    hallucinated = _response(
        view,
        role="BID_QUALIFICATION",
        requirement_basis="SINGLE_CONTRACT",
        mandatory="YES",
        amount_surface="3억원",
    )
    value, evidence, diagnostic = decide_v3_monetary(record, view, hallucinated, 0, "")
    assert (value, evidence) == (0, "")
    assert diagnostic["reason"] == "qualification_amount_not_verified"


def test_duplicate_or_missing_candidate_is_invalid() -> None:
    record = _record([
        "참가자격 수행실적 2억원 이상.",
        "평가용 수행실적 3억원 이상이면 5점.",
    ])
    view = build_v3_monetary_view(record)
    response = _response(view)
    parsed = json.loads(response["content"])
    parsed["observations"][1]["source_id"] = parsed["observations"][0]["source_id"]
    response["content"] = json.dumps(parsed)
    value, evidence, diagnostic = decide_v3_monetary(record, view, response, 1, "base")
    assert (value, evidence) == (1, "base")
    assert diagnostic["reason"] == "invalid_response"

