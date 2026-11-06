from __future__ import annotations

import json

import pytest

from src.pps_ai.decisions.v19_requirements import (
    build_v19_schema,
    build_v19_task,
    parse_v19_observations,
    reduce_v19_observations,
)
from src.pps_ai.views.v19_requirements import build_v19_requirement_view


def _record(texts: list[str]) -> dict[str, object]:
    return {
        "id": "N1",
        "meta": {},
        "docs": [
            {
                "doc_id": f"D{index}",
                "type": "공고문" if index == 0 else "제안요청서",
                "text": text,
            }
            for index, text in enumerate(texts)
        ],
    }


def _row(quote: str, **changes: str) -> dict[str, str]:
    value = {
        "requirement_role": "OTHER",
        "document_kind": "OTHER_DOCUMENT",
        "external_issuer_explicit": "NO",
        "bidder_must_obtain_or_hold": "NO",
        "bidder_must_submit": "NO",
        "obtain_before_bid_deadline": "NO",
        "submit_with_bid_or_proposal": "NO",
        "submit_after_bid_or_contract": "NO",
        "quoted_text": quote,
    }
    value.update(changes)
    return value


def _response(observations: dict[str, object]) -> dict[str, object]:
    return {
        "finish_reason": "stop",
        "invalid": False,
        "content": json.dumps({"observations": observations}, ensure_ascii=False),
    }


def test_view_inspects_every_document_and_keeps_exact_offsets() -> None:
    record = _record([
        "제조사의 물품공급 확약서를 입찰 전에 보유한다.",
        "일반 안내만 있는 첨부입니다.",
        "계약상대자는 안전보건 이행확약서를 제출한다.",
    ])
    view = build_v19_requirement_view(record)
    assert len(view["document_coverage"]) == 3
    assert all(row["inspected"] for row in view["document_coverage"])
    assert len(view["candidates"]) == 2
    for candidate in view["candidates"]:
        document = record["docs"][candidate.document_order]
        assert document["text"][candidate.start:candidate.end] == candidate.text


def test_schema_uses_exact_candidate_keys_and_task_has_truth_boundaries() -> None:
    record = _record([
        "제조사의 물품공급 확약서를 입찰 전에 보유한다.",
        "직접이행 확약서는 계약 시 제출한다.",
    ])
    view = build_v19_requirement_view(record)
    schema = build_v19_schema(view["candidates"])
    observations = schema["properties"]["observations"]
    assert observations["required"] == ["R01", "R02"]
    assert observations["additionalProperties"] is False
    task = build_v19_task(record, view["candidates"])
    system = task["messages"][0]["content"]
    user = task["messages"][1]["content"]
    assert "최종 위반 여부나 v19 0/1은 출력하지 않는다" in system
    assert "제출 가능한 업체" in user
    assert "낙찰·계약 후에만 제출" in user
    assert "입찰자 자신의 이행약속" in user


def test_parser_rejects_missing_key_and_non_exact_quote() -> None:
    record = _record([
        "제조사의 물품공급 확약서를 입찰 전에 보유한다.",
        "직접이행 확약서는 계약 시 제출한다.",
    ])
    candidates = build_v19_requirement_view(record)["candidates"]
    first = _row(candidates[0].text)
    rows, reason = parse_v19_observations(_response({"R01": first}), candidates)
    assert rows is None
    assert reason == "candidate_key_mismatch"

    observations = {
        "R01": first,
        "R02": _row("원문에 없는 요약"),
    }
    rows, reason = parse_v19_observations(_response(observations), candidates)
    assert rows is None
    assert reason == "quoted_text_not_exact"


@pytest.mark.parametrize(
    ("text", "changes"),
    [
        (
            "제조사의 물품공급 확약서를 입찰서 제출 마감 전까지 보유하여야 한다.",
            {
                "requirement_role": "BID_OR_PROPOSAL_QUALIFICATION",
                "document_kind": "EXTERNAL_SUPPLY_OR_TECH_ASSURANCE",
                "external_issuer_explicit": "YES",
                "bidder_must_obtain_or_hold": "YES",
                "obtain_before_bid_deadline": "YES",
            },
        ),
        (
            "제조회사 공급 증명원 및 A/S 확약서를 제안서와 함께 제출하여야 한다.",
            {
                "requirement_role": "BID_OR_PROPOSAL_QUALIFICATION",
                "document_kind": "EXTERNAL_SUPPLY_OR_TECH_ASSURANCE",
                "external_issuer_explicit": "YES",
                "bidder_must_submit": "YES",
                "submit_with_bid_or_proposal": "YES",
            },
        ),
    ],
)
def test_reducer_accepts_only_explicit_prebid_external_assurance(
    text: str, changes: dict[str, str],
) -> None:
    record = _record([text])
    candidates = build_v19_requirement_view(record)["candidates"]
    response = _response({"R01": _row(text, **changes)})
    rows, reason = parse_v19_observations(response, candidates)
    assert reason is None
    assert rows is not None
    value, evidence, diagnostic = reduce_v19_observations(candidates, rows)
    assert value == 1
    assert evidence == text
    assert diagnostic["decision"] == "POSITIVE_PROOF"


@pytest.mark.parametrize(
    ("text", "changes"),
    [
        (
            "제조사의 물품공급 확약서를 적격심사 시 제출하여야 한다.",
            {
                "requirement_role": "POST_BID_REVIEW",
                "document_kind": "EXTERNAL_SUPPLY_OR_TECH_ASSURANCE",
                "external_issuer_explicit": "YES",
                "bidder_must_submit": "YES",
                "submit_after_bid_or_contract": "YES",
            },
        ),
        (
            "정품공급 확약서 제출이 가능한 업체여야 한다.",
            {
                "requirement_role": "BID_OR_PROPOSAL_QUALIFICATION",
                "document_kind": "EXTERNAL_SUPPLY_OR_TECH_ASSURANCE",
                "external_issuer_explicit": "UNKNOWN",
            },
        ),
        (
            "계약상대자는 직접이행의무 준수 확약서를 계약 시 제출한다.",
            {
                "requirement_role": "CONTRACT_PERFORMANCE",
                "document_kind": "BIDDER_SELF_PROMISE",
                "bidder_must_submit": "YES",
                "submit_after_bid_or_contract": "YES",
            },
        ),
        (
            "원제조자가 발행한 제조자증명서를 입찰 전에 제출한다.",
            {
                "requirement_role": "BID_OR_PROPOSAL_QUALIFICATION",
                "document_kind": "EXTERNAL_STATUS_OR_AUTHENTICITY_CERTIFICATE",
                "external_issuer_explicit": "YES",
                "bidder_must_submit": "YES",
                "submit_with_bid_or_proposal": "YES",
            },
        ),
    ],
)
def test_reducer_rejects_material_zero_conditions(
    text: str, changes: dict[str, str],
) -> None:
    record = _record([text])
    candidates = build_v19_requirement_view(record)["candidates"]
    rows, reason = parse_v19_observations(
        _response({"R01": _row(text, **changes)}), candidates,
    )
    assert reason is None
    assert rows is not None
    value, evidence, diagnostic = reduce_v19_observations(candidates, rows)
    assert value == 0
    assert evidence == ""
    assert diagnostic["decision"] == "NEGATIVE_PROOF"


def test_reducer_does_not_join_fields_across_candidates() -> None:
    record = _record([
        "제조사의 물품공급 확약서가 있다.",
        "다른 제출서류는 입찰서와 함께 반드시 제출한다.",
    ])
    # The second document lacks an assurance anchor, so add a self-promise anchor.
    record["docs"][1]["text"] = "다른 이행확약서는 입찰서와 함께 반드시 제출한다."
    candidates = build_v19_requirement_view(record)["candidates"]
    observations = {
        "R01": _row(
            candidates[0].text,
            requirement_role="BID_OR_PROPOSAL_QUALIFICATION",
            document_kind="EXTERNAL_SUPPLY_OR_TECH_ASSURANCE",
            external_issuer_explicit="YES",
        ),
        "R02": _row(
            candidates[1].text,
            requirement_role="BID_OR_PROPOSAL_QUALIFICATION",
            document_kind="BIDDER_SELF_PROMISE",
            bidder_must_submit="YES",
            submit_with_bid_or_proposal="YES",
        ),
    }
    rows, reason = parse_v19_observations(_response(observations), candidates)
    assert reason is None
    assert rows is not None
    assert reduce_v19_observations(candidates, rows)[0] == 0
