"""Narrow distinct-observation serialization for the unchanged v24 v2.1 reducer."""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from .v24_code_provenance_v21 import decide_v24_code_provenance_v21
from .v24_multi_observation import (
    CONTRACT_VALUES,
    ROLE_VALUES,
    SYSTEM_PROMPT,
    build_v24_multi_task,
)


MAX_DISTINCT_OBSERVATIONS = 4
SERIALIZATION_INSTRUCTION = """

직렬화 규칙:
- 동일 source_id, role, canonical value 조합을 절대 반복하지 않는다.
- 같은 값을 반복하는 문구는 observation 하나만 출력한다.
- value_won은 JSON 문자열이 아니라 0 이상의 JSON 정수 또는 null이다.
- industry_codes에는 정확히 4자리 업종코드만 넣고 세부품명번호는 넣지 않는다.
- 제공된 해당 축 source_id enum 외의 문자열은 출력하지 않는다."""


def _source_id_schema(ids: Sequence[str]) -> dict[str, Any]:
    return {"type": "string", "enum": list(ids) or ["__NO_SOURCE__"]}


def _array(items: dict[str, Any], *, source_count: int) -> dict[str, Any]:
    return {
        "type": "array",
        "maxItems": MAX_DISTINCT_OBSERVATIONS if source_count else 0,
        "items": items,
    }


def _object(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }


def build_v24_serialization_schema(view: Mapping[str, Any]) -> dict[str, Any]:
    source_ids = {
        axis: [candidate.source_id for candidate in view["candidates"][axis]]
        for axis in ("amount", "contract", "region", "industry")
    }
    short = {"type": "string", "minLength": 1, "maxLength": 120}
    string_list = {"type": "array", "maxItems": 10, "items": short}
    code_list = {
        "type": "array",
        "maxItems": 10,
        "items": {"type": "string", "pattern": "^[0-9]{4}$"},
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["amount", "contract", "region", "industry"],
        "properties": {
            "amount": _array(_object({
                "source_id": _source_id_schema(source_ids["amount"]),
                "role": {"type": "string", "enum": [
                    "BUDGET_TOTAL", "ESTIMATED_EX_VAT", "PARTIAL_OR_UNIT_AMOUNT", "OTHER",
                ]},
                "value_won": {"type": ["integer", "null"], "minimum": 0},
            }, ["source_id", "role", "value_won"]), source_count=len(source_ids["amount"])),
            "contract": _array(_object({
                "source_id": _source_id_schema(source_ids["contract"]),
                "role": {"type": "string", "enum": [
                    "COMPETITION_METHOD", "AWARD_OR_NEGOTIATION_METHOD", "SUBMISSION_METHOD", "OTHER",
                ]},
                "competition_method": {"type": "string", "enum": [
                    "GENERAL", "LIMITED", "NOMINATED", "DIRECT", "OTHER", "UNKNOWN",
                ]},
            }, ["source_id", "role", "competition_method"]), source_count=len(source_ids["contract"])),
            "region": _array(_object({
                "source_id": _source_id_schema(source_ids["region"]),
                "role": {"type": "string", "enum": [
                    "BIDDER_LOCATION", "SITE_OR_DELIVERY", "POST_AWARD_OFFICE", "OTHER",
                ]},
                "regions": string_list,
            }, ["source_id", "role", "regions"]), source_count=len(source_ids["region"])),
            "industry": _array(_object({
                "source_id": _source_id_schema(source_ids["industry"]),
                "role": {"type": "string", "enum": [
                    "BIDDER_MANDATORY_INDUSTRY", "TASK_FIELD", "PERSONNEL_QUALIFICATION",
                    "PRODUCT_REGISTRATION", "OTHER",
                ]},
                "industry_codes": code_list,
                "industry_names": string_list,
            }, ["source_id", "role", "industry_codes", "industry_names"]), source_count=len(source_ids["industry"])),
        },
    }


def build_v24_serialization_task(
    record: Mapping[str, Any], view: Mapping[str, Any],
) -> dict[str, Any]:
    task = build_v24_multi_task(record, view)
    task["arm"] = "V24_DISTINCT_SERIALIZATION_V22"
    task["messages"][0]["content"] = SYSTEM_PROMPT + SERIALIZATION_INSTRUCTION
    task["schema"] = build_v24_serialization_schema(view)
    return task


def _parse_v22(response: Mapping[str, Any], view: Mapping[str, Any]) -> dict[str, Any] | None:
    if response.get("finish_reason") != "stop" or response.get("invalid") is True:
        return None
    try:
        parsed = json.loads(str(response.get("content", "")))
    except (TypeError, ValueError):
        return None
    if not isinstance(parsed, dict) or set(parsed) != {"amount", "contract", "region", "industry"}:
        return None
    allowed_ids = {
        axis: {candidate.source_id for candidate in view["candidates"][axis]}
        for axis in parsed
    }
    required = {
        "amount": {"source_id", "role", "value_won"},
        "contract": {"source_id", "role", "competition_method"},
        "region": {"source_id", "role", "regions"},
        "industry": {"source_id", "role", "industry_codes", "industry_names"},
    }
    seen: set[tuple[str, str]] = set()
    for axis, rows in parsed.items():
        if not isinstance(rows, list) or len(rows) > MAX_DISTINCT_OBSERVATIONS:
            return None
        for row in rows:
            if not isinstance(row, dict) or set(row) != required[axis]:
                return None
            if row["source_id"] not in allowed_ids[axis]:
                return None
            if row["role"] not in ROLE_VALUES[axis]:
                return None
            if axis == "amount" and row["value_won"] is not None and (
                type(row["value_won"]) is not int or row["value_won"] < 0
            ):
                return None
            if axis == "contract" and row["competition_method"] not in CONTRACT_VALUES:
                return None
            if axis == "region" and not _valid_string_list(row["regions"]):
                return None
            if axis == "industry" and (
                not isinstance(row["industry_codes"], list)
                or len(row["industry_codes"]) > 10
                or not _valid_string_list(row["industry_names"])
            ):
                return None
            if axis == "industry" and any(
                not isinstance(code, str) or len(code) != 4 or not code.isdigit()
                for code in row["industry_codes"]
            ):
                return None
            identity = (axis, json.dumps(row, ensure_ascii=False, sort_keys=True))
            if identity in seen:
                return None
            seen.add(identity)
    return parsed


def _valid_string_list(value: Any) -> bool:
    return isinstance(value, list) and len(value) <= 10 and all(
        isinstance(item, str) and 0 < len(item) <= 120 for item in value
    )


def adapt_v22_response(
    response: Mapping[str, Any], view: Mapping[str, Any],
) -> dict[str, Any] | None:
    parsed = _parse_v22(response, view)
    if parsed is None:
        return None
    for row in parsed["amount"]:
        if row["value_won"] is not None:
            row["value_won"] = str(row["value_won"])
    adapted = dict(response)
    adapted["content"] = json.dumps(parsed, ensure_ascii=False)
    return adapted


def decide_v24_serialization_v22(
    record: Mapping[str, Any],
    view: Mapping[str, Any],
    response: Mapping[str, Any],
) -> tuple[int, str, dict[str, Any]]:
    adapted = adapt_v22_response(response, view)
    if adapted is None:
        return 0, "", {
            "valid": False,
            "fallback": True,
            "observations": {},
            "mismatches": [],
            "serialization_valid": False,
        }
    value, evidence, diagnostic = decide_v24_code_provenance_v21(record, view, adapted)
    diagnostic["serialization_valid"] = True
    return value, evidence, diagnostic
