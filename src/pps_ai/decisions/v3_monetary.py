"""Typed v3 monetary observations and deterministic amount comparison."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import json
import re
from typing import Any, Mapping

from ..views.v3_monetary import candidate_index, render_candidates


ROLE_VALUES = {
    "BID_QUALIFICATION", "EVALUATION", "FORM", "EXPERIENCE_DESCRIPTION", "OTHER",
}
BASIS_VALUES = {"SINGLE_CONTRACT", "AGGREGATE", "UNKNOWN"}
MANDATORY_VALUES = {"YES", "NO", "UNKNOWN"}


SYSTEM_PROMPT = """당신은 v3 실적금액 관계를 위한 원자 사실만 구조화한다. 최종 위반 여부와
금액 비교 결과는 출력하지 않는다. 아래의 모든 candidate를 source_id별로 정확히 한 번씩
분류한다. candidate를 빠뜨리거나 같은 source_id를 중복 출력하지 않는다.

role 규칙:
- BID_QUALIFICATION: 입찰에 참가하기 위해 반드시 충족해야 하는 과거 완료실적 요건
- EVALUATION: 제안서 점수, 적격심사, 특별신인도 등 참가 후 평가용 실적
- FORM: 실적증명서 서식, 제출목록 또는 작성 예시일 뿐 그 자체로 참가 기준이 아닌 내용
- EXPERIENCE_DESCRIPTION: 업체가 자신의 실적을 소개하도록 한 내용
- OTHER: 그 밖의 내용

requirement_basis는 단일 계약/단일 건 금액이면 SINGLE_CONTRACT, 여러 건의 합계·누적이면
AGGREGATE, 확정할 수 없으면 UNKNOWN이다. mandatory는 해당 과거실적 금액이 참가 자체의
필수조건인지 표시한다. amount_surface는 candidate에 실제로 적힌 요구금액 표현 하나를 글자
그대로 복사한다(예: "5억원", "455,000,000원"). 평가구간, 사업비, 배점, 보증금이 아니라
과거실적 요구금액이어야 한다. 해당하지 않거나 확정할 수 없으면 null이다. 정수 원 단위로
환산하거나 계산하지 않는다. JSON 외에는 출력하지 않는다."""


def build_v3_monetary_schema(view: Mapping[str, Any]) -> dict[str, Any]:
    source_ids = [candidate.source_id for candidate in view["candidates"]]
    count = len(source_ids)
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["observations"],
        "properties": {
            "observations": {
                "type": "array",
                "minItems": count,
                "maxItems": count,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "source_id", "role", "requirement_basis", "mandatory",
                        "amount_surface",
                    ],
                    "properties": {
                        "source_id": {"type": "string", "enum": source_ids},
                        "role": {"type": "string", "enum": sorted(ROLE_VALUES)},
                        "requirement_basis": {
                            "type": "string", "enum": sorted(BASIS_VALUES),
                        },
                        "mandatory": {"type": "string", "enum": sorted(MANDATORY_VALUES)},
                        "amount_surface": {
                            "type": ["string", "null"], "minLength": 1, "maxLength": 80,
                        },
                    },
                },
            },
        },
    }


def build_v3_monetary_task(record: Mapping[str, Any], view: Mapping[str, Any]) -> dict[str, Any]:
    estimate = (record.get("meta") or {}).get("입찰추정가격")
    friendly_estimate = "미입력" if estimate is None or estimate == "" else str(estimate)
    user = (
        f"[공고 ID]\n{record['id']}\n\n"
        f"[나라장터 입력값 — 사람이 읽는 필드]\n- 입찰추정가격(VAT 제외): {friendly_estimate}원\n\n"
        "[v3 판정 기준]\n실제 입찰 참가자격으로 단일 과거실적 금액을 요구하는지를 찾는다. "
        "누적실적·평가점수·특별신인도·서식·경력소개는 참가자격 단일실적이 아니다. "
        "후속 검증기는 검증된 요구금액이 위 입찰추정가격을 초과할 때만 1로 계산하고, "
        "같거나 작으면 0으로 계산한다. 모델은 이 비교나 최종 라벨을 출력하지 않는다.\n\n"
        "[공고 원문 후보 — 모든 제공 문서를 순회한 exact span]\n"
        + render_candidates(view["candidates"])
    )
    return {
        "id": str(record["id"]),
        "arm": "V3_MONETARY_V1",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        "schema": build_v3_monetary_schema(view),
    }


def parse_amount_won(surface: str) -> int | None:
    """Parse one Korean monetary surface without inferring absent multipliers."""
    compact = re.sub(r"[\s,]", "", surface)
    patterns = (
        (r"(?<![\d.])(\d+(?:\.\d+)?)억원?(?!\d)", Decimal(100_000_000)),
        (r"(?<![\d.])(\d+(?:\.\d+)?)천만원(?!\d)", Decimal(10_000_000)),
        (r"(?<![\d.])(\d+(?:\.\d+)?)만원(?!\d)", Decimal(10_000)),
        (r"(?<![\d.])(\d+(?:\.\d+)?)천원(?!\d)", Decimal(1_000)),
        (r"(?<![\d.])(\d+)원(?!\d)", Decimal(1)),
    )
    matches: list[int] = []
    for pattern, multiplier in patterns:
        for match in re.finditer(pattern, compact):
            try:
                value = Decimal(match.group(1)) * multiplier
            except InvalidOperation:
                return None
            if value != value.to_integral_value() or value <= 0:
                return None
            matches.append(int(value))
        if matches:
            break
    return matches[0] if len(matches) == 1 else None


def _parse_response(
    response: Mapping[str, Any], expected_ids: set[str],
) -> list[dict[str, Any]] | None:
    if response.get("finish_reason") != "stop" or response.get("invalid") is True:
        return None
    try:
        parsed = json.loads(str(response.get("content", "")))
    except (TypeError, ValueError):
        return None
    if not isinstance(parsed, dict) or set(parsed) != {"observations"}:
        return None
    rows = parsed["observations"]
    if not isinstance(rows, list) or len(rows) != len(expected_ids):
        return None
    required = {"source_id", "role", "requirement_basis", "mandatory", "amount_surface"}
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != required:
            return None
        source_id = row["source_id"]
        if not isinstance(source_id, str) or source_id not in expected_ids or source_id in seen:
            return None
        seen.add(source_id)
        if row["role"] not in ROLE_VALUES:
            return None
        if row["requirement_basis"] not in BASIS_VALUES:
            return None
        if row["mandatory"] not in MANDATORY_VALUES:
            return None
        if row["amount_surface"] is not None and not isinstance(row["amount_surface"], str):
            return None
    return rows if seen == expected_ids else None


def _evidence(text: str, surface: str) -> str:
    position = text.find(surface)
    start = max(0, position - 210) if position >= 0 else 0
    return text[start:start + 500].strip()


def decide_v3_monetary(
    record: Mapping[str, Any],
    view: Mapping[str, Any],
    response: Mapping[str, Any],
    baseline_value: int,
    baseline_evidence: str,
) -> tuple[int, str, dict[str, Any]]:
    return decide_v3_monetary_with_bases(
        record, view, response, baseline_value, baseline_evidence,
        accepted_bases={"SINGLE_CONTRACT"},
    )


def decide_v3_monetary_with_bases(
    record: Mapping[str, Any],
    view: Mapping[str, Any],
    response: Mapping[str, Any],
    baseline_value: int,
    baseline_evidence: str,
    *,
    accepted_bases: set[str],
) -> tuple[int, str, dict[str, Any]]:
    if not accepted_bases or not accepted_bases <= {"SINGLE_CONTRACT", "AGGREGATE"}:
        raise ValueError("accepted v3 requirement bases are invalid")
    sources = candidate_index(view)
    rows = _parse_response(response, set(sources))
    diagnostic: dict[str, Any] = {
        "valid": rows is not None,
        "fallback": False,
        "decision": "BASELINE",
        "observations": [],
    }
    if rows is None:
        diagnostic["fallback"] = True
        diagnostic["reason"] = "invalid_response"
        return baseline_value, baseline_evidence, diagnostic
    estimate = (record.get("meta") or {}).get("입찰추정가격")
    if not isinstance(estimate, (int, float)) or estimate <= 0:
        diagnostic["fallback"] = True
        diagnostic["reason"] = "missing_estimated_price"
        return baseline_value, baseline_evidence, diagnostic

    qualification_rows = []
    for row in rows:
        source = sources[row["source_id"]]
        surface = row["amount_surface"]
        source_valid = isinstance(surface, str) and surface in source.text
        amount_won = parse_amount_won(surface) if source_valid else None
        accepted = (
            row["role"] == "BID_QUALIFICATION"
            and row["requirement_basis"] in accepted_bases
            and row["mandatory"] == "YES"
        )
        observed = {
            **row,
            "source_valid": source_valid,
            "amount_won": amount_won,
            "accepted_qualification": accepted,
        }
        diagnostic["observations"].append(observed)
        if accepted:
            qualification_rows.append((observed, source))

    if not qualification_rows:
        diagnostic["fallback"] = True
        diagnostic["reason"] = "no_verified_qualification_observation"
        return baseline_value, baseline_evidence, diagnostic
    if any(row["amount_won"] is None for row, _ in qualification_rows):
        diagnostic["fallback"] = True
        diagnostic["reason"] = "qualification_amount_not_verified"
        return baseline_value, baseline_evidence, diagnostic

    violating = [
        (row, source) for row, source in qualification_rows
        if int(row["amount_won"]) > int(estimate)
    ]
    if violating:
        row, source = max(violating, key=lambda pair: int(pair[0]["amount_won"]))
        diagnostic["decision"] = "POSITIVE_PROOF"
        diagnostic["estimated_price"] = int(estimate)
        return 1, _evidence(source.text, str(row["amount_surface"])), diagnostic

    diagnostic["decision"] = "NEGATIVE_PROOF"
    diagnostic["estimated_price"] = int(estimate)
    return 0, "", diagnostic
