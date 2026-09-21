"""Compact serialization for unchanged v19 requirement observations."""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from .v19_requirements import build_v19_task
from ..views.v19_requirements import V19RequirementCandidate


ROLE_CODES = {
    0: "BID_OR_PROPOSAL_QUALIFICATION",
    1: "POST_BID_REVIEW",
    2: "CONTRACT_PERFORMANCE",
    3: "FORM_OR_TEMPLATE",
    4: "INFORMATION_ONLY",
    5: "OTHER",
    6: "UNKNOWN",
}
KIND_CODES = {
    0: "EXTERNAL_SUPPLY_OR_TECH_ASSURANCE",
    1: "EXTERNAL_STATUS_OR_AUTHENTICITY_CERTIFICATE",
    2: "BIDDER_SELF_PROMISE",
    3: "OTHER_DOCUMENT",
    4: "UNKNOWN",
}
TRI_CODES = {0: "NO", 1: "YES", 2: "UNKNOWN"}


SERIALIZATION_INSTRUCTION = """

[응답 직렬화 코드 — 의미는 위 지시와 동일]
각 candidate key의 value는 정확히 r,k,x,h,s,b,w,a,q 아홉 key를 출력한다.
r: 0=입찰·제안자격, 1=입찰후심사, 2=계약이행, 3=서식, 4=안내, 5=기타, 6=불명.
k: 0=외부물품공급·기술지원이행보장, 1=외부지위·정품증명, 2=입찰자자기확약,
3=기타서류, 4=불명.
x,h,s,b,w,a는 모두 0=NO, 1=YES, 2=UNKNOWN이다. 순서대로 외부발급자명시,
입찰자발급·보유의무, 입찰자제출의무, 입찰마감전발급·보유, 입찰·제안동시제출,
입찰후·계약단계제출을 뜻한다. q는 기존 quoted_text와 동일한 원문 문자열이다.
이 코드는 출력 모양만 줄이며 사실의 의미나 판단 기준을 바꾸지 않는다."""


def build_v19_compact_schema(
    candidates: Sequence[V19RequirementCandidate],
) -> dict[str, Any]:
    observation = {
        "type": "object",
        "additionalProperties": False,
        "required": ["r", "k", "x", "h", "s", "b", "w", "a", "q"],
        "properties": {
            "r": {"type": "integer", "enum": sorted(ROLE_CODES)},
            "k": {"type": "integer", "enum": sorted(KIND_CODES)},
            **{
                key: {"type": "integer", "enum": sorted(TRI_CODES)}
                for key in ("x", "h", "s", "b", "w", "a")
            },
            "q": {"type": "string", "minLength": 1, "maxLength": 500},
        },
    }
    source_ids = [candidate.source_id for candidate in candidates]
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["observations"],
        "properties": {
            "observations": {
                "type": "object",
                "additionalProperties": False,
                "required": source_ids,
                "properties": {source_id: observation for source_id in source_ids},
            },
        },
    }


def build_v19_compact_task(
    record: Mapping[str, Any],
    candidates: Sequence[V19RequirementCandidate],
) -> dict[str, Any]:
    task = build_v19_task(record, candidates)
    task["arm"] = "V19_REQUIREMENT_COMPACT_V1"
    task["messages"][0]["content"] += SERIALIZATION_INSTRUCTION
    task["schema"] = build_v19_compact_schema(candidates)
    return task


def adapt_compact_response(
    response: Mapping[str, Any],
    candidates: Sequence[V19RequirementCandidate],
) -> dict[str, Any] | None:
    if response.get("finish_reason") != "stop" or response.get("invalid") is True:
        return None
    try:
        parsed = json.loads(str(response.get("content", "")))
    except (TypeError, ValueError):
        return None
    source_ids = [candidate.source_id for candidate in candidates]
    if not isinstance(parsed, dict) or set(parsed) != {"observations"}:
        return None
    observations = parsed["observations"]
    if not isinstance(observations, dict) or set(observations) != set(source_ids):
        return None
    required = {"r", "k", "x", "h", "s", "b", "w", "a", "q"}
    verbose = {}
    for source_id in source_ids:
        value = observations[source_id]
        if not isinstance(value, dict) or set(value) != required:
            return None
        if value["r"] not in ROLE_CODES or value["k"] not in KIND_CODES:
            return None
        if any(value[key] not in TRI_CODES for key in ("x", "h", "s", "b", "w", "a")):
            return None
        if not isinstance(value["q"], str) or not 1 <= len(value["q"]) <= 500:
            return None
        verbose[source_id] = {
            "requirement_role": ROLE_CODES[value["r"]],
            "document_kind": KIND_CODES[value["k"]],
            "external_issuer_explicit": TRI_CODES[value["x"]],
            "bidder_must_obtain_or_hold": TRI_CODES[value["h"]],
            "bidder_must_submit": TRI_CODES[value["s"]],
            "obtain_before_bid_deadline": TRI_CODES[value["b"]],
            "submit_with_bid_or_proposal": TRI_CODES[value["w"]],
            "submit_after_bid_or_contract": TRI_CODES[value["a"]],
            "quoted_text": value["q"],
        }
    adapted = dict(response)
    adapted["content"] = json.dumps({"observations": verbose}, ensure_ascii=False)
    return adapted
