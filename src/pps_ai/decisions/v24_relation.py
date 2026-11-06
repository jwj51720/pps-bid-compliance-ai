"""Typed v24 observation prompt and explicit relation reducer."""

from __future__ import annotations

import json
import re
from typing import Any, Mapping

from ..views.v24_relation import candidate_index, render_v24_candidates


AXIS_CONTRACT = {
    "amount": {
        "meta_field": {"BUDGET", "ESTIMATED", "NONE"},
        "document_role": {"BUDGET_TOTAL", "ESTIMATED_EX_VAT", "PARTIAL_AMOUNT", "UNKNOWN"},
        "required_roles": {"BUDGET_TOTAL", "ESTIMATED_EX_VAT"},
    },
    "contract": {
        "meta_field": {"CONTRACT_METHOD", "NONE"},
        "document_role": {"CONTRACT_METHOD", "AWARD_METHOD", "BID_METHOD", "UNKNOWN"},
        "required_roles": {"CONTRACT_METHOD"},
    },
    "region": {
        "meta_field": {"REGION_RESTRICTION", "NONE"},
        "document_role": {"BIDDER_LOCATION", "SITE_OR_DELIVERY", "POST_AWARD_OFFICE", "UNKNOWN"},
        "required_roles": {"BIDDER_LOCATION"},
    },
    "industry": {
        "meta_field": {"INDUSTRY_RESTRICTION", "NONE"},
        "document_role": {
            "BIDDER_MANDATORY_INDUSTRY", "TASK_FIELD", "PERSONNEL_QUALIFICATION",
            "PRODUCT_REGISTRATION", "UNKNOWN",
        },
        "required_roles": {"BIDDER_MANDATORY_INDUSTRY"},
    },
}

COMMON_PROPERTIES = {
    "comparable": {"type": "string", "enum": ["Y", "N", "U"]},
    "different": {"type": "string", "enum": ["Y", "N", "U"]},
    "document_value": {"type": ["string", "null"], "maxLength": 240},
    "source_id": {"type": ["string", "null"], "maxLength": 16},
}


def _axis_schema(axis: str) -> dict[str, Any]:
    contract = AXIS_CONTRACT[axis]
    return {
        "type": "object", "additionalProperties": False,
        "required": [
            "comparable", "different", "meta_field", "document_role",
            "document_value", "source_id",
        ],
        "properties": {
            **COMMON_PROPERTIES,
            "meta_field": {"type": "string", "enum": sorted(contract["meta_field"])},
            "document_role": {"type": "string", "enum": sorted(contract["document_role"])},
        },
    }


V24_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["amount", "contract", "region", "industry"],
    "properties": {axis: _axis_schema(axis) for axis in AXIS_CONTRACT},
}

SYSTEM_PROMPT = """당신은 공고 원문과 나라장터 입력값의 v24 정합성을 위해 원자 관계만 추출한다.
최종 위반 라벨을 출력하지 않는다. 각 축에서 양쪽이 같은 의미·범위·시점의 동일 필드일 때만
comparable=Y로 둔다. comparable=Y인 경우에만 값이 명백히 다르면 different=Y다.

엄격한 역할 구분:
- 금액: VAT 포함 총사업비는 BUDGET_TOTAL, 명시적 추정가격/VAT 제외액은 ESTIMATED_EX_VAT다.
  품목·연차·단가·부분금액은 PARTIAL_AMOUNT이며 전체 meta와 비교하지 않는다.
- 계약: 일반/제한/지명경쟁·수의계약만 CONTRACT_METHOD다. 협상·적격심사·최저가는
  AWARD_METHOD, 전자/직찰은 BID_METHOD다.
- 지역: 참가업체 본점·주된 영업소의 소재지 자격만 BIDDER_LOCATION이다. 현장·납품지·행사장·
  접수장소는 SITE_OR_DELIVERY, 낙찰 후 사무소 설치는 POST_AWARD_OFFICE다.
- 업종: 입찰 참가자가 마감일까지 보유해야 하는 법정 업종·면허·허가만
  BIDDER_MANDATORY_INDUSTRY다. 과업 분야, 인력자격, 제품 제조등록은 별도 역할이다.

한쪽 값이 null/미입력, 문서 후보가 없음, 의미 역할이 다름, 범위가 불명확하면 comparable=N
또는 U이고 different는 N 또는 U다. meta N과 명백한 동일 필드의 참가제한은 비교 후보지만,
문서 역할을 먼저 확정한다. source_id는 판단을 직접 입증하는 제공 후보 하나만 사용한다.
후보 헤더와 탐지어 자체는 근거가 아니다. JSON 외에는 출력하지 않는다."""


def _friendly_meta(meta: Mapping[str, Any]) -> str:
    def value(key: str) -> str:
        raw = meta.get(key)
        return "미입력" if raw is None or raw == "" else str(raw)

    return "\n".join([
        f"- 예산금액(VAT 포함 역할): {value('배정예산금액')}",
        f"- 추정가격(VAT 제외 역할): {value('입찰추정가격')}",
        f"- 계약방법: {value('계약방법')}",
        f"- 지역제한 여부: {value('지역제한여부')}",
        f"- 제한지역: {value('제한지역코드목록')}",
        f"- 업종제한 여부: {value('업종제한여부')}",
        f"- 제한업종: {value('면허업종제한목록')}",
    ])


def build_v24_task(record: Mapping[str, Any], view: Mapping[str, Any]) -> dict[str, Any]:
    sections = []
    names = {
        "amount": "금액", "contract": "계약방법",
        "region": "참가업체 지역", "industry": "필수 업종",
    }
    for axis in ("amount", "contract", "region", "industry"):
        sections.append(
            f"## {names[axis]} 후보\n"
            + render_v24_candidates(view["candidates"][axis])
        )
    user = (
        f"[공고 ID]\n{record['id']}\n\n"
        f"[나라장터 입력값 — 사람이 읽는 필드]\n{_friendly_meta(record.get('meta') or {})}\n\n"
        "[공고 원문 후보 — 모든 제공 문서를 검사한 exact span]\n"
        + "\n\n".join(sections)
    )
    return {
        "id": str(record["id"]), "arm": "V24_NATIVE",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        "schema": V24_SCHEMA,
    }


def _parse_response(response: Mapping[str, Any]) -> dict[str, Any] | None:
    if response.get("finish_reason") != "stop" or response.get("invalid") is True:
        return None
    try:
        value = json.loads(str(response.get("content", "")))
    except (TypeError, ValueError):
        return None
    if not isinstance(value, dict) or set(value) != set(AXIS_CONTRACT):
        return None
    for axis, contract in AXIS_CONTRACT.items():
        row = value.get(axis)
        if not isinstance(row, dict) or set(row) != {
            "comparable", "different", "meta_field", "document_role",
            "document_value", "source_id",
        }:
            return None
        if row["comparable"] not in {"Y", "N", "U"}:
            return None
        if row["different"] not in {"Y", "N", "U"}:
            return None
        if row["meta_field"] not in contract["meta_field"]:
            return None
        if row["document_role"] not in contract["document_role"]:
            return None
        if row["document_value"] is not None and not isinstance(row["document_value"], str):
            return None
        if row["source_id"] is not None and not isinstance(row["source_id"], str):
            return None
    return value


def decide_v24(
    record: Mapping[str, Any], view: Mapping[str, Any], response: Mapping[str, Any],
) -> tuple[int, str, dict[str, Any]]:
    parsed = _parse_response(response)
    if parsed is None:
        return 0, "", {"valid": False, "fallback": True, "axes": {}}
    sources = candidate_index(view)
    axes: dict[str, Any] = {}
    positive_source = None
    for axis, row in parsed.items():
        source = sources.get(row["source_id"]) if row["source_id"] else None
        source_axis_valid = source is not None and source.axis == axis
        role_valid = row["document_role"] in AXIS_CONTRACT[axis]["required_roles"]
        explicit = bool(
            row["comparable"] == "Y"
            and row["different"] == "Y"
            and row["meta_field"] != "NONE"
            and role_valid
            and source_axis_valid
        )
        axes[axis] = {
            **row, "role_valid": role_valid,
            "source_axis_valid": source_axis_valid,
            "explicit_contradiction": explicit,
        }
        if explicit and positive_source is None:
            positive_source = source
    if positive_source is None:
        return 0, "", {"valid": True, "fallback": False, "axes": axes}
    evidence = positive_source.text.strip()
    if len(evidence) > 500:
        evidence = evidence[:500]
    source_text = str(record["docs"][positive_source.document_order]["text"])
    if not evidence or evidence not in source_text:
        return 0, "", {
            "valid": False, "fallback": True, "axes": axes,
            "reason": "positive evidence is not an exact source substring",
        }
    return 1, evidence, {"valid": True, "fallback": False, "axes": axes}
