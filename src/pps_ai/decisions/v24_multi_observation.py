"""Typed multi-observation extraction and mechanical v24 relation reduction."""

from __future__ import annotations

import json
import re
from typing import Any, Mapping

from ..views.v24_multi_observation import candidate_index, render_candidates


MAX_OBSERVATIONS = 8
ROLE_VALUES = {
    "amount": {"BUDGET_TOTAL", "ESTIMATED_EX_VAT", "PARTIAL_OR_UNIT_AMOUNT", "OTHER"},
    "contract": {
        "COMPETITION_METHOD", "AWARD_OR_NEGOTIATION_METHOD", "SUBMISSION_METHOD", "OTHER",
    },
    "region": {"BIDDER_LOCATION", "SITE_OR_DELIVERY", "POST_AWARD_OFFICE", "OTHER"},
    "industry": {
        "BIDDER_MANDATORY_INDUSTRY", "TASK_FIELD", "PERSONNEL_QUALIFICATION",
        "PRODUCT_REGISTRATION", "OTHER",
    },
}
CONTRACT_VALUES = {"GENERAL", "LIMITED", "NOMINATED", "DIRECT", "OTHER", "UNKNOWN"}
REGION_ALIASES = {
    "서울": "서울특별시", "서울시": "서울특별시",
    "부산": "부산광역시", "부산시": "부산광역시",
    "대구": "대구광역시", "대구시": "대구광역시",
    "인천": "인천광역시", "인천시": "인천광역시",
    "광주": "광주광역시", "광주시": "광주광역시",
    "대전": "대전광역시", "대전시": "대전광역시",
    "울산": "울산광역시", "울산시": "울산광역시",
    "세종": "세종특별자치시", "세종시": "세종특별자치시",
    "강원도": "강원특별자치도", "전라북도": "전북특별자치도",
    "전북": "전북특별자치도", "제주": "제주특별자치도",
    "제주도": "제주특별자치도",
}


def _array_schema(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "array",
        "maxItems": MAX_OBSERVATIONS,
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": required,
            "properties": properties,
        },
    }


SOURCE_ID = {"type": "string", "minLength": 2, "maxLength": 16}
SHORT_STRING = {"type": "string", "minLength": 1, "maxLength": 120}
STRING_LIST = {"type": "array", "maxItems": 10, "items": SHORT_STRING}

V24_MULTI_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["amount", "contract", "region", "industry"],
    "properties": {
        "amount": _array_schema({
            "source_id": SOURCE_ID,
            "role": {"type": "string", "enum": [
                "BUDGET_TOTAL", "ESTIMATED_EX_VAT", "PARTIAL_OR_UNIT_AMOUNT", "OTHER",
            ]},
            "value_won": {"type": ["string", "null"], "maxLength": 40},
        }, ["source_id", "role", "value_won"]),
        "contract": _array_schema({
            "source_id": SOURCE_ID,
            "role": {"type": "string", "enum": [
                "COMPETITION_METHOD", "AWARD_OR_NEGOTIATION_METHOD", "SUBMISSION_METHOD", "OTHER",
            ]},
            "competition_method": {"type": "string", "enum": [
                "GENERAL", "LIMITED", "NOMINATED", "DIRECT", "OTHER", "UNKNOWN",
            ]},
        }, ["source_id", "role", "competition_method"]),
        "region": _array_schema({
            "source_id": SOURCE_ID,
            "role": {"type": "string", "enum": [
                "BIDDER_LOCATION", "SITE_OR_DELIVERY", "POST_AWARD_OFFICE", "OTHER",
            ]},
            "regions": STRING_LIST,
        }, ["source_id", "role", "regions"]),
        "industry": _array_schema({
            "source_id": SOURCE_ID,
            "role": {"type": "string", "enum": [
                "BIDDER_MANDATORY_INDUSTRY", "TASK_FIELD", "PERSONNEL_QUALIFICATION",
                "PRODUCT_REGISTRATION", "OTHER",
            ]},
            "industry_codes": STRING_LIST,
            "industry_names": STRING_LIST,
        }, ["source_id", "role", "industry_codes", "industry_names"]),
    },
}


SYSTEM_PROMPT = """당신은 공고 원문과 나라장터 입력값의 v24 정합성 점검을 위해 원자 사실만 구조화한다.
최종 위반 여부, different, 일치/불일치 결론은 출력하지 않는다. 제공 후보 중 공고 자체가 선언한
서로 다른 공식 값을 빠짐없이 배열로 출력한다. 같은 축에 공식 문구가 둘 이상이면 하나를 고르지
말고 각각 별도 observation으로 보존한다. 일반 안내·법령 인용·서식 예시는 생략한다.

역할 규칙:
- amount: VAT 포함 총사업비/기초금액은 BUDGET_TOTAL, 명시적 추정가격/VAT 제외액은
  ESTIMATED_EX_VAT다. 실적금액·보증금·단가·품목·연차 금액은 PARTIAL_OR_UNIT_AMOUNT다.
- contract: 일반/제한/지명경쟁·수의계약만 COMPETITION_METHOD다. 협상·적격심사·최저가 등
  낙찰자 선정 방식은 AWARD_OR_NEGOTIATION_METHOD, 전자/직찰은 SUBMISSION_METHOD다.
- region: 참가자의 본점·주된 영업소 소재지 자격만 BIDDER_LOCATION이다. 현장·납품지·행사장과
  낙찰 후 사무소는 별도 역할이다. 허용 지역이 여러 개면 regions 배열에 모두 넣는다.
- industry: 입찰 참가자가 마감일까지 보유해야 할 법정 업종·면허만
  BIDDER_MANDATORY_INDUSTRY다. 과업 분야, 인력 자격, 제품 등록은 별도 역할이다. 공고에 적힌
  업종코드와 업종명을 각각 배열에 보존한다.

value_won은 원 단위 숫자만 공백·쉼표 없이 출력한다. 지역명·업종명은 원문 표기를 보존한다.
source_id는 그 원자값과 역할을 직접 입증하는 후보여야 한다. 후보가 없거나 공식 값을 확정할 수
없으면 해당 배열을 비운다. JSON 외에는 출력하지 않는다."""


def _friendly_meta(meta: Mapping[str, Any]) -> str:
    def value(key: str) -> str:
        raw = meta.get(key)
        return "미입력" if raw is None or raw == "" else str(raw)

    return "\n".join([
        f"- 예산금액(VAT 포함): {value('배정예산금액')}",
        f"- 추정가격(VAT 제외): {value('입찰추정가격')}",
        f"- 계약방법: {value('계약방법')}",
        f"- 지역제한 여부: {value('지역제한여부')}",
        f"- 제한지역: {value('제한지역코드목록')}",
        f"- 업종제한 여부: {value('업종제한여부')}",
        f"- 제한업종: {value('면허업종제한목록')}",
    ])


def build_v24_multi_task(record: Mapping[str, Any], view: Mapping[str, Any]) -> dict[str, Any]:
    names = {
        "amount": "금액", "contract": "경쟁·계약 방식",
        "region": "참가업체 지역", "industry": "필수 업종·면허",
    }
    sections = [
        f"## {names[axis]} 후보\n{render_candidates(view['candidates'][axis])}"
        for axis in ("amount", "contract", "region", "industry")
    ]
    user = (
        f"[공고 ID]\n{record['id']}\n\n"
        f"[나라장터 입력값 — 사람이 읽는 필드]\n{_friendly_meta(record.get('meta') or {})}\n\n"
        "[공고 원문 후보 — 모든 제공 문서를 순회한 exact span]\n"
        + "\n\n".join(sections)
    )
    return {
        "id": str(record["id"]),
        "arm": "V24_MULTI_OBSERVATION_V2",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        "schema": V24_MULTI_SCHEMA,
    }


def _parse_response(response: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]] | None:
    if response.get("finish_reason") != "stop" or response.get("invalid") is True:
        return None
    try:
        parsed = json.loads(str(response.get("content", "")))
    except (TypeError, ValueError):
        return None
    if not isinstance(parsed, dict) or set(parsed) != {"amount", "contract", "region", "industry"}:
        return None
    required = {
        "amount": {"source_id", "role", "value_won"},
        "contract": {"source_id", "role", "competition_method"},
        "region": {"source_id", "role", "regions"},
        "industry": {"source_id", "role", "industry_codes", "industry_names"},
    }
    for axis, rows in parsed.items():
        if not isinstance(rows, list) or len(rows) > MAX_OBSERVATIONS:
            return None
        for row in rows:
            if not isinstance(row, dict) or set(row) != required[axis]:
                return None
            if not isinstance(row["source_id"], str):
                return None
            if row["role"] not in ROLE_VALUES[axis]:
                return None
            if axis == "amount" and row["value_won"] is not None and not isinstance(row["value_won"], str):
                return None
            if axis == "contract" and row["competition_method"] not in CONTRACT_VALUES:
                return None
            if axis == "region" and not _string_list(row["regions"]):
                return None
            if axis == "industry" and (
                not _string_list(row["industry_codes"]) or not _string_list(row["industry_names"])
            ):
                return None
    return parsed


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and len(value) <= 10 and all(
        isinstance(item, str) and item for item in value
    )


def _digits(value: Any) -> str | None:
    if value is None:
        return None
    digits = re.sub(r"\D", "", str(value))
    return digits or None


def _normal_text(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]", "", value).casefold()


def _source_contains(source_text: str, value: str) -> bool:
    normalized = _normal_text(value)
    return bool(normalized) and normalized in _normal_text(source_text)


def _amount_in_source(source_text: str, value: str) -> bool:
    target = _digits(value)
    if target is None:
        return False
    return any(_digits(token) == target for token in re.findall(r"\d[\d, ]*", source_text))


def _contract_method(value: Any) -> str | None:
    text = _normal_text(str(value or ""))
    if "일반경쟁" in text:
        return "GENERAL"
    if "제한경쟁" in text:
        return "LIMITED"
    if "지명경쟁" in text:
        return "NOMINATED"
    if "수의" in text:
        return "DIRECT"
    return None


def _region_set(value: Any) -> set[str]:
    if value is None or value == "":
        return set()
    if not isinstance(value, list):
        tagged = re.findall(r"광역=([가-힣]+)", str(value))
        if tagged:
            return {_canonical_region(item) for item in tagged}
    values = value if isinstance(value, list) else re.split(r"[,;/|]", str(value))
    return {_canonical_region(str(item)) for item in values if _canonical_region(str(item))}


def _canonical_region(value: str) -> str:
    match = re.search(r"광역=([가-힣]+)", value)
    text = match.group(1) if match else value
    normalized = _normal_text(text)
    return _normal_text(REGION_ALIASES.get(normalized, normalized))


def _industry_codes(value: Any) -> set[str]:
    if value is None:
        return set()
    return set(re.findall(r"(?<!\d)(\d{4})(?!\d)", str(value)))


def _evidence(source: Any) -> str:
    text = source.text.strip()
    if len(text) <= 500:
        return text
    positions = [text.casefold().find(term.casefold()) for term in source.terms]
    positions = [position for position in positions if position >= 0]
    center = min(positions) if positions else 0
    start = max(0, center - 180)
    return text[start:start + 500]


def decide_v24_multi(
    record: Mapping[str, Any], view: Mapping[str, Any], response: Mapping[str, Any],
) -> tuple[int, str, dict[str, Any]]:
    parsed = _parse_response(response)
    if parsed is None:
        return 0, "", {"valid": False, "fallback": True, "observations": {}, "mismatches": []}
    sources = candidate_index(view)
    accepted: dict[str, list[dict[str, Any]]] = {axis: [] for axis in parsed}
    for axis, rows in parsed.items():
        for row in rows:
            source = sources.get(row["source_id"])
            valid = source is not None and source.axis == axis
            if valid and axis == "amount" and row["value_won"] is not None:
                valid = _amount_in_source(source.text, row["value_won"])
            elif valid and axis == "region":
                valid = all(_source_contains(source.text, value) for value in row["regions"])
            elif valid and axis == "industry":
                valid = all(
                    _source_contains(source.text, value)
                    for value in row["industry_codes"] + row["industry_names"]
                )
            accepted[axis].append({**row, "source_valid": valid, "source": source})

    meta = record.get("meta") or {}
    mismatches: list[dict[str, Any]] = []

    amount_meta = {
        "BUDGET_TOTAL": _digits(meta.get("배정예산금액")),
        "ESTIMATED_EX_VAT": _digits(meta.get("입찰추정가격")),
    }
    for row in accepted["amount"]:
        expected = amount_meta.get(row["role"])
        actual = _digits(row["value_won"])
        if row["source_valid"] and expected is not None and actual is not None and actual != expected:
            mismatches.append({"axis": "amount", "source": row["source"], "expected": expected, "actual": actual})

    expected_contract = _contract_method(meta.get("계약방법"))
    for row in accepted["contract"]:
        if (
            row["source_valid"] and row["role"] == "COMPETITION_METHOD"
            and expected_contract is not None
            and row["competition_method"] not in {"UNKNOWN", "OTHER", expected_contract}
        ):
            mismatches.append({
                "axis": "contract", "source": row["source"],
                "expected": expected_contract, "actual": row["competition_method"],
            })

    expected_regions = _region_set(meta.get("제한지역코드목록"))
    region_limited = str(meta.get("지역제한여부") or "").upper() == "Y"
    region_rows = [
        row for row in accepted["region"]
        if row["source_valid"] and row["role"] == "BIDDER_LOCATION" and row["regions"]
    ]
    actual_regions = {_canonical_region(value) for row in region_rows for value in row["regions"]}
    if actual_regions and ((not region_limited) or (expected_regions and actual_regions != expected_regions)):
        mismatches.append({
            "axis": "region", "source": region_rows[0]["source"],
            "expected": sorted(expected_regions), "actual": sorted(actual_regions),
        })

    expected_codes = _industry_codes(meta.get("면허업종제한목록"))
    industry_limited = str(meta.get("업종제한여부") or "").upper() == "Y"
    industry_rows = [
        row for row in accepted["industry"]
        if row["source_valid"] and row["role"] == "BIDDER_MANDATORY_INDUSTRY"
        and row["industry_codes"]
    ]
    actual_codes = {code for row in industry_rows for code in row["industry_codes"]}
    if actual_codes and ((not industry_limited) or (expected_codes and actual_codes != expected_codes)):
        mismatches.append({
            "axis": "industry", "source": industry_rows[0]["source"],
            "expected": sorted(expected_codes), "actual": sorted(actual_codes),
        })

    diagnostic_observations = {
        axis: [{key: value for key, value in row.items() if key != "source"} for row in rows]
        for axis, rows in accepted.items()
    }
    if not mismatches:
        return 0, "", {
            "valid": True, "fallback": False,
            "observations": diagnostic_observations, "mismatches": [],
        }
    source = mismatches[0]["source"]
    evidence = _evidence(source)
    original = str(record["docs"][source.document_order]["text"])
    if not evidence or evidence not in original:
        return 0, "", {
            "valid": False, "fallback": True,
            "observations": diagnostic_observations,
            "mismatches": [{key: value for key, value in item.items() if key != "source"} for item in mismatches],
            "reason": "positive evidence is not an exact source substring",
        }
    return 1, evidence, {
        "valid": True, "fallback": False,
        "observations": diagnostic_observations,
        "mismatches": [{key: value for key, value in item.items() if key != "source"} for item in mismatches],
    }
