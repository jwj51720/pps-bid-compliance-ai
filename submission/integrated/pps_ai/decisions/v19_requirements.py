"""Typed v19 requirement observations and organizer-defined reducer."""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from ..views.v19_requirements import (
    V19RequirementCandidate,
    candidate_index,
    render_candidates,
)


ROLE_VALUES = {
    "BID_OR_PROPOSAL_QUALIFICATION",
    "POST_BID_REVIEW",
    "CONTRACT_PERFORMANCE",
    "FORM_OR_TEMPLATE",
    "INFORMATION_ONLY",
    "OTHER",
    "UNKNOWN",
}
KIND_VALUES = {
    "EXTERNAL_SUPPLY_OR_TECH_ASSURANCE",
    "EXTERNAL_STATUS_OR_AUTHENTICITY_CERTIFICATE",
    "BIDDER_SELF_PROMISE",
    "OTHER_DOCUMENT",
    "UNKNOWN",
}
TRI_VALUES = {"YES", "NO", "UNKNOWN"}


SYSTEM_PROMPT = """당신은 공공 입찰공고의 v19 판단에 필요한 requirement instance 사실만
구조화한다. 최종 위반 여부나 v19 0/1은 출력하지 않는다. observations 객체에는 user가 제공한
모든 candidate ID를 각각 정확히 한 번 key로 사용한다. 서로 다른 candidate나 서로 다른 서류의
발급자·내용·의무·시점을 합치지 않는다.

v19의 대상은 입찰자가 외부 제조사·공급사·기술지원사로부터 받아야 하는 물품공급 또는
기술지원 이행보장 서류다. 다음을 엄격히 구별한다.
- EXTERNAL_SUPPLY_OR_TECH_ASSURANCE: 외부사가 물품공급·기술지원을 이행하겠다는 보장
- EXTERNAL_STATUS_OR_AUTHENTICITY_CERTIFICATE: 제조자, 대리점, 정품, 허가·지위만 증명
- BIDDER_SELF_PROMISE: 입찰업체가 자신의 의무 준수를 약속하는 각서·확약

external_issuer_explicit는 원문에 제조사·공급사·기술지원사 등 외부 발급/보장 주체가 실제로
연결된 경우만 YES다. 서류 이름만으로 외부 발급자를 추측하지 않는다.

시점은 다음 세 사실을 따로 기록한다.
- obtain_before_bid_deadline: 입찰서/제안서 제출 마감 전 발급·보유 의무
- submit_with_bid_or_proposal: 입찰서·제안서·입찰참가서류와 함께 제출 의무
- submit_after_bid_or_contract: 적격심사, 낙찰통보, 계약체결 또는 계약이행 단계 제출

`제출 가능한 업체`, 시점 없는 언급, 다른 서류의 제출 마감, 단순 서식·목록은 의무나 시점을
추측하는 근거가 아니다. 다만 상위 제출목록의 명시적 마감이 같은 하위 서류 목록 전체에
분명하게 연결된 경우에는 그 candidate 내부 관계로 판단할 수 있다. 계약 시 제출이라도 입찰
마감 전 보유가 별도로 강제되면 두 사실을 각각 YES로 보존한다.

quoted_text는 해당 candidate 안에서 판단을 직접 뒷받침하는 변경 없는 연속 원문 substring을
1~500자로 복사한다. 설명, 생략부호, 정규화 문자를 넣지 않는다. JSON 외에는 출력하지 않는다."""


def _observation_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "requirement_role",
            "document_kind",
            "external_issuer_explicit",
            "bidder_must_obtain_or_hold",
            "bidder_must_submit",
            "obtain_before_bid_deadline",
            "submit_with_bid_or_proposal",
            "submit_after_bid_or_contract",
            "quoted_text",
        ],
        "properties": {
            "requirement_role": {"type": "string", "enum": sorted(ROLE_VALUES)},
            "document_kind": {"type": "string", "enum": sorted(KIND_VALUES)},
            "external_issuer_explicit": {"type": "string", "enum": sorted(TRI_VALUES)},
            "bidder_must_obtain_or_hold": {"type": "string", "enum": sorted(TRI_VALUES)},
            "bidder_must_submit": {"type": "string", "enum": sorted(TRI_VALUES)},
            "obtain_before_bid_deadline": {"type": "string", "enum": sorted(TRI_VALUES)},
            "submit_with_bid_or_proposal": {"type": "string", "enum": sorted(TRI_VALUES)},
            "submit_after_bid_or_contract": {"type": "string", "enum": sorted(TRI_VALUES)},
            "quoted_text": {"type": "string", "minLength": 1, "maxLength": 500},
        },
    }


def build_v19_schema(
    candidates: Sequence[V19RequirementCandidate],
) -> dict[str, Any]:
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
                "properties": {
                    source_id: _observation_schema() for source_id in source_ids
                },
            },
        },
    }


def build_v19_task(
    record: Mapping[str, Any],
    candidates: Sequence[V19RequirementCandidate],
) -> dict[str, Any]:
    user = (
        f"[공고 ID]\n{record['id']}\n\n"
        "[v19 적용 및 판정 기준 — organizer 항목표와 compact card]\n"
        "대상은 외부 제조사·공급사·기술지원사의 물품공급 또는 기술지원 확약서다. "
        "입찰서/제안서 제출 전에 발급·보유하도록 강제하거나 입찰·제안 제출과 함께 의무 "
        "제출시키면 1 조건이다. 단순 제출서류 목록, 제출 가능한 업체, 시점 없는 언급, "
        "낙찰·계약 후에만 제출, 제조자·대리점 지위 증명, 입찰자 자신의 이행약속은 0 "
        "조건이다. 최종 label은 Python이 typed observation의 명시식으로 계산하므로 모델은 "
        "원문 사실만 분류한다.\n\n"
        "[실제 공고 자료의 exact candidate — 모든 제공 문서를 순서대로 검사]\n"
        + render_candidates(candidates)
    )
    return {
        "id": str(record["id"]),
        "arm": "V19_REQUIREMENT_INSTANCES_V1",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        "schema": build_v19_schema(candidates),
    }


def parse_v19_observations(
    response: Mapping[str, Any],
    candidates: Sequence[V19RequirementCandidate],
) -> tuple[list[dict[str, Any]] | None, str | None]:
    if response.get("finish_reason") != "stop" or response.get("invalid") is True:
        return None, "invalid_transport_response"
    try:
        parsed = json.loads(str(response.get("content", "")))
    except (TypeError, ValueError):
        return None, "invalid_json"
    if not isinstance(parsed, dict) or set(parsed) != {"observations"}:
        return None, "invalid_top_level"
    observations = parsed["observations"]
    sources = candidate_index(candidates)
    if not isinstance(observations, dict) or set(observations) != set(sources):
        return None, "candidate_key_mismatch"
    required = set(_observation_schema()["required"])
    rows = []
    for source_id in sources:
        value = observations[source_id]
        if not isinstance(value, dict) or set(value) != required:
            return None, "observation_shape"
        if value["requirement_role"] not in ROLE_VALUES:
            return None, "requirement_role"
        if value["document_kind"] not in KIND_VALUES:
            return None, "document_kind"
        for key in required - {"requirement_role", "document_kind", "quoted_text"}:
            if value[key] not in TRI_VALUES:
                return None, key
        quote = value["quoted_text"]
        if (
            not isinstance(quote, str)
            or not 1 <= len(quote) <= 500
            or quote not in sources[source_id].text
        ):
            return None, "quoted_text_not_exact"
        rows.append({"source_id": source_id, **value})
    return rows, None


def reduce_v19_observations(
    candidates: Sequence[V19RequirementCandidate],
    observations: Sequence[Mapping[str, Any]],
) -> tuple[int, str, dict[str, Any]]:
    sources = candidate_index(candidates)
    if {str(row.get("source_id")) for row in observations} != set(sources):
        raise ValueError("v19 reducer requires exactly one observation per candidate")
    diagnostics = []
    positives = []
    for row in observations:
        source_id = str(row["source_id"])
        positive = (
            row["requirement_role"] == "BID_OR_PROPOSAL_QUALIFICATION"
            and row["document_kind"] == "EXTERNAL_SUPPLY_OR_TECH_ASSURANCE"
            and row["external_issuer_explicit"] == "YES"
            and (
                (
                    row["bidder_must_obtain_or_hold"] == "YES"
                    and row["obtain_before_bid_deadline"] == "YES"
                )
                or (
                    row["bidder_must_submit"] == "YES"
                    and row["submit_with_bid_or_proposal"] == "YES"
                )
            )
        )
        item = {**row, "positive_predicate": positive}
        diagnostics.append(item)
        if positive:
            positives.append((sources[source_id], str(row["quoted_text"])))
    if not positives:
        return 0, "", {
            "valid": True,
            "fallback": False,
            "decision": "NEGATIVE_PROOF",
            "observations": diagnostics,
        }
    source, quote = min(
        positives,
        key=lambda value: (value[0].document_order, value[0].start, value[0].source_id),
    )
    return 1, quote, {
        "valid": True,
        "fallback": False,
        "decision": "POSITIVE_PROOF",
        "evidence_source_id": source.source_id,
        "observations": diagnostics,
    }
