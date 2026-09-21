"""Typed v4 requirement-instance observations and conservative reducer."""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from ..views.v4_requirements import V4RequirementCandidate, render_v4_candidates


ROLE_VALUES = {"Q", "E", "F", "C", "O", "U"}
MANDATORY_VALUES = {"Y", "N", "U"}
RESTRICTION_VALUES = {"I", "S", "G", "N", "U"}
ALLOWANCE_VALUES = {"B", "E", "N", "U"}
NECESSITY_VALUES = {"C", "N", "U"}


SYSTEM_PROMPT = """당신은 공공 입찰공고의 v4 판단에 필요한 실적 요구 사실만 후보별로
구조화한다. 최종 v4나 위반 0/1은 출력하지 않는다. observations 객체에는 user가 제공한 모든
candidate ID를 각각 정확히 한 번 key로 사용한다. 서로 다른 candidate의 역할·제한·허용·필요성을
합치지 않는다.

각 value는 r,m,x,a,n,q 여섯 field다.
- r 역할: Q=입찰 참가자격, E=평가·가점, F=서식·증빙양식, C=계약 후 이행조건,
  O=그 밖의 정보, U=불명
- m 의무성: Y=그 실적 없이는 참가 불가, N=참가 박탈조건 아님, U=불명
- x 제한 종류: I=특정 발주기관군 실적만 인정, S=특정 사업명·대상·방식으로 매우 좁게 한정,
  G=계약 목적과 직접 관련된 일반 동종·유사 실적, N=제한 없음, U=불명
- a 같은 요구의 허용: B=민간·해외 등 넓은 발주처/실적도 허용, E=동등·유사 실적을 실질 허용,
  N=그런 허용이 명시되지 않음, U=불명
- n 같은 요구의 좁은 범위 필요성: C=특수 기술·공법·성능·안전 등 구체적 필요가 원문에 명시,
  N=구체적 필요가 명시되지 않음, U=불명
- q: Q/Y이면서 x가 I 또는 S이고 a=N,n=N인 후보만 판단을 직접 입증하는 1~500자 변경 없는
  연속 원문을 복사한다. 나머지는 null이다.

공공기관이라는 단어가 발주처·제출처·서식 예시에 있다는 이유만으로 I로 분류하지 않는다.
평가표와 실적증명서 양식을 참가자격으로 바꾸지 않는다. 문서 전체의 사업 목적만 보고 구체적
필요성을 추측하지 말고, 같은 candidate에 필요 사유가 명시될 때만 n=C다. 일반적인 관련·유사
실적을 특정실적으로 과장하지 않는다. JSON 외에는 출력하지 않는다."""


def _observation_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["r", "m", "x", "a", "n", "q"],
        "properties": {
            "r": {"type": "string", "enum": sorted(ROLE_VALUES)},
            "m": {"type": "string", "enum": sorted(MANDATORY_VALUES)},
            "x": {"type": "string", "enum": sorted(RESTRICTION_VALUES)},
            "a": {"type": "string", "enum": sorted(ALLOWANCE_VALUES)},
            "n": {"type": "string", "enum": sorted(NECESSITY_VALUES)},
            "q": {"type": ["string", "null"], "minLength": 1, "maxLength": 500},
        },
    }


def build_v4_schema(candidates: Sequence[V4RequirementCandidate]) -> dict[str, Any]:
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


def build_v4_task(
    record: Mapping[str, Any], candidates: Sequence[V4RequirementCandidate],
) -> dict[str, Any]:
    user = (
        f"[공고 ID]\n{record['id']}\n\n"
        "[v4 organizer 판단 계약]\n"
        "과거 실적을 실제 입찰 참가자격으로 강제하면서 특정 발주기관군 실적만 인정하거나 "
        "계약 목적상 필요 이상으로 특정 사업명·대상·방식의 실적만 인정하고, 같은 요구에 "
        "민간·해외·동등·일반 유사실적 허용이나 구체적 필요가 명시되지 않은 관계를 찾는다. "
        "평가·가점, 증빙서식, 계약 후 조건, 일반 동종실적은 해당하지 않는다. 금액 범위는 "
        "이번 관계 관측에서 판단하지 않는다. 모델은 후보별 source 사실만 분류하고 최종식은 "
        "Python이 계산한다.\n\n"
        "[모든 제공 문서를 순서대로 검사한 exact candidate]\n"
        + render_v4_candidates(candidates)
    )
    return {
        "id": str(record["id"]),
        "arm": "V4_REQUIREMENT_INSTANCES_V1",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        "schema": build_v4_schema(candidates),
    }


def parse_v4_observations(
    response: Mapping[str, Any], candidates: Sequence[V4RequirementCandidate],
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
    sources = {candidate.source_id: candidate for candidate in candidates}
    if not isinstance(observations, dict) or set(observations) != set(sources):
        return None, "candidate_key_mismatch"
    required = {"r", "m", "x", "a", "n", "q"}
    rows: list[dict[str, Any]] = []
    for source_id, source in sources.items():
        value = observations[source_id]
        if not isinstance(value, dict) or set(value) != required:
            return None, "observation_shape"
        if value["r"] not in ROLE_VALUES:
            return None, "role"
        if value["m"] not in MANDATORY_VALUES:
            return None, "mandatory"
        if value["x"] not in RESTRICTION_VALUES:
            return None, "restriction"
        if value["a"] not in ALLOWANCE_VALUES:
            return None, "allowance"
        if value["n"] not in NECESSITY_VALUES:
            return None, "necessity"
        potential_positive = (
            value["r"] == "Q"
            and value["m"] == "Y"
            and value["x"] in {"I", "S"}
            and value["a"] == "N"
            and value["n"] == "N"
        )
        quote = value["q"]
        if potential_positive:
            if (
                not isinstance(quote, str)
                or not 1 <= len(quote) <= 500
                or quote not in source.text
            ):
                return None, "positive_quote_not_exact"
        elif quote is not None:
            return None, "negative_quote_must_be_null"
        rows.append({"source_id": source_id, **value})
    return rows, None


def _negative_excluded(row: Mapping[str, Any]) -> bool:
    if row["r"] in {"E", "F", "C", "O"}:
        return True
    if row["r"] != "Q":
        return False
    if row["m"] == "N" or row["x"] in {"G", "N"}:
        return True
    if row["x"] in {"I", "S"} and (row["a"] in {"B", "E"} or row["n"] == "C"):
        return True
    return False


def decide_v4(
    response: Mapping[str, Any], candidates: Sequence[V4RequirementCandidate],
    baseline_value: int, baseline_evidence: str,
) -> tuple[int, str, dict[str, Any]]:
    rows, reason = parse_v4_observations(response, candidates)
    if rows is None:
        return baseline_value, baseline_evidence, {
            "valid": False,
            "fallback": True,
            "decision": "BASELINE",
            "reason": reason,
            "observations": [],
        }
    return reduce_v4_observations(rows, candidates, baseline_value, baseline_evidence)


def reduce_v4_observations(
    rows: Sequence[Mapping[str, Any]], candidates: Sequence[V4RequirementCandidate],
    baseline_value: int, baseline_evidence: str,
) -> tuple[int, str, dict[str, Any]]:
    """Reduce already validated observations, including multiple admitted packs."""

    expected = {candidate.source_id for candidate in candidates}
    actual = [str(row.get("source_id")) for row in rows]
    if len(actual) != len(expected) or set(actual) != expected:
        return baseline_value, baseline_evidence, {
            "valid": False,
            "fallback": True,
            "decision": "BASELINE",
            "reason": "merged_candidate_key_mismatch",
            "observations": list(rows),
        }
    positives = [
        row for row in rows
        if (
            row["r"] == "Q"
            and row["m"] == "Y"
            and row["x"] in {"I", "S"}
            and row["a"] == "N"
            and row["n"] == "N"
        )
    ]
    if positives:
        order = {candidate.source_id: index for index, candidate in enumerate(candidates)}
        selected = min(positives, key=lambda row: order[str(row["source_id"])])
        return 1, str(selected["q"]), {
            "valid": True,
            "fallback": False,
            "decision": "POSITIVE_PROOF",
            "evidence_source_id": selected["source_id"],
            "observations": rows,
        }
    if rows and all(_negative_excluded(row) for row in rows):
        return 0, "", {
            "valid": True,
            "fallback": False,
            "decision": "NEGATIVE_PROOF",
            "observations": rows,
        }
    return baseline_value, baseline_evidence, {
        "valid": True,
        "fallback": True,
        "decision": "BASELINE",
        "reason": "unresolved_observation",
        "observations": rows,
    }
