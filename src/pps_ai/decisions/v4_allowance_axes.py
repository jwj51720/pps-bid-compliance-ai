"""V4-only issuer/work allowance observations with source-checked evidence."""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from .v19_quote_resolution_v2 import resolve_exact_quote
from .v4_requirements import (
    MANDATORY_VALUES,
    NECESSITY_VALUES,
    RESTRICTION_VALUES,
    ROLE_VALUES,
    build_v4_scope_task,
)
from ..views.v4_requirements import V4RequirementCandidate


ISSUER_ALLOWANCE_VALUES = {"B", "N", "U"}
WORK_ALLOWANCE_VALUES = {"E", "N", "U"}


AXIS_SYSTEM_PROMPT = """당신은 공공 입찰공고의 v4 판단에 필요한 실적 요구를 후보별로 구조화한다.
최종 v4 또는 위반 0/1은 출력하지 않는다. observations의 key는 제공된 모든 candidate ID와
정확히 같아야 하며, 서로 다른 후보의 조건을 합치지 않는다.

각 후보에 r,m,x,i,a,n,q 일곱 field를 기록한다.
- r 역할: Q=입찰 참가자격, E=평가·가점, F=서식·증빙양식, C=계약 후 이행,
  O=기타, U=불명
- m 의무성: Y=해당 실적 없이는 참가 불가, N=참가 박탈조건 아님, U=불명
- x 제한축: I=특정 발주기관군 실적만 인정, S=특정 사업명·대상·방식의 실적으로
  매우 좁게 한정, G=일반 동종·유사 실적, N=제한 없음, U=불명
- i 발주기관 허용: B=같은 실적 요구에서 민간·해외 등 해당 기관군 밖의 발주실적도
  실질적으로 허용, N=기관군 제한을 넓히는 허용이 명시되지 않음, U=불명
- a 사업내용 허용: E=같은 실적 요구에서 동등·유사한 사업내용도 실질적으로 허용,
  N=사업내용을 넓히는 허용이 명시되지 않음, U=불명
- n 좁은 실적 요구의 필요성: C=특수 기술·공법·성능·안전 등 구체적 필요가 같은
  요구에 명시, N=명시되지 않음, U=불명
- q: Q/Y/n=N이면서 (x=I이고 i=N) 또는 (x=S이고 a=N)인 후보에서만
  제한을 직접 입증하는 연속된 원문 1~500자를 복사한다. 나머지는 null이다.

발주기관군과 사업내용은 독립된 축이다. 유사한 사업내용을 허용한다는 말만으로
제한된 발주기관군 밖의 실적도 허용된다고 추정하지 않는다. 반대로 민간 실적을
허용한다는 말만으로 특정 사업내용 제한까지 해제됐다고 추정하지 않는다.
평가표·제출서류·실적증명서 양식을 참가자격으로 바꾸지 않는다. 직전 제목형
원문 줄은 위치 단서이며 자동 확정된 상위 절이 아니다. q는 제목 이력이 아닌
실적 후보 원문에서만 복사한다. JSON 외에는 출력하지 않는다."""


def build_v4_axis_task(
    record: Mapping[str, Any], candidates: Sequence[V4RequirementCandidate],
) -> dict[str, Any]:
    task = build_v4_scope_task(record, candidates)
    task["arm"] = "V4_REQUIREMENT_ALLOWANCE_AXES_V1"
    task["messages"][0]["content"] = AXIS_SYSTEM_PROMPT
    task["messages"][1]["content"] = task["messages"][1]["content"].replace(
        "민간·해외·동등·일반 유사실적 허용이나 구체적 필요",
        "같은 제한축의 실질적 허용이나 구체적 필요",
        1,
    )
    properties = task["schema"]["properties"]["observations"]["properties"]
    for value in properties.values():
        value["required"] = ["r", "m", "x", "i", "a", "n", "q"]
        value["properties"]["i"] = {
            "type": "string", "enum": sorted(ISSUER_ALLOWANCE_VALUES),
        }
        value["properties"]["a"] = {
            "type": "string", "enum": sorted(WORK_ALLOWANCE_VALUES),
        }
    return task


def _positive(row: Mapping[str, Any]) -> bool:
    return (
        row["r"] == "Q"
        and row["m"] == "Y"
        and row["n"] == "N"
        and (
            (row["x"] == "I" and row["i"] == "N")
            or (row["x"] == "S" and row["a"] == "N")
        )
    )


def parse_v4_axis_observations(
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
    required = {"r", "m", "x", "i", "a", "n", "q"}
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
        if value["i"] not in ISSUER_ALLOWANCE_VALUES:
            return None, "issuer_allowance"
        if value["a"] not in WORK_ALLOWANCE_VALUES:
            return None, "work_allowance"
        if value["n"] not in NECESSITY_VALUES:
            return None, "necessity"
        quote = value["q"]
        if _positive(value):
            if not isinstance(quote, str) or not 1 <= len(quote) <= 500:
                return None, "positive_quote_shape"
            quote, _ = resolve_exact_quote(source.text, quote)
            if quote is None:
                return None, "positive_quote_not_exact"
        elif quote is not None:
            if not isinstance(quote, str) or not 1 <= len(quote) <= 500:
                return None, "negative_quote_shape"
            quote = None
        rows.append({"source_id": source_id, **value, "q": quote})
    return rows, None


def _negative_excluded(row: Mapping[str, Any]) -> bool:
    if row["r"] in {"E", "F", "C", "O"}:
        return True
    if row["r"] != "Q":
        return False
    if row["m"] == "N" or row["x"] in {"G", "N"}:
        return True
    if row["x"] == "I" and (row["i"] == "B" or row["n"] == "C"):
        return True
    if row["x"] == "S" and (row["a"] == "E" or row["n"] == "C"):
        return True
    return False


def reduce_v4_axis_observations(
    rows: Sequence[Mapping[str, Any]], candidates: Sequence[V4RequirementCandidate],
    baseline_value: int, baseline_evidence: str,
) -> tuple[int, str, dict[str, Any]]:
    expected = {candidate.source_id for candidate in candidates}
    actual = [str(row.get("source_id")) for row in rows]
    if len(actual) != len(expected) or set(actual) != expected:
        return baseline_value, baseline_evidence, {
            "valid": False, "fallback": True, "decision": "BASELINE",
            "reason": "merged_candidate_key_mismatch", "observations": list(rows),
        }
    positives = [row for row in rows if _positive(row)]
    if positives:
        order = {candidate.source_id: index for index, candidate in enumerate(candidates)}
        selected = min(positives, key=lambda row: order[str(row["source_id"])])
        return 1, str(selected["q"]), {
            "valid": True, "fallback": False, "decision": "POSITIVE_PROOF",
            "evidence_source_id": selected["source_id"], "observations": rows,
        }
    if rows and all(_negative_excluded(row) for row in rows):
        return 0, "", {
            "valid": True, "fallback": False, "decision": "NEGATIVE_PROOF",
            "observations": rows,
        }
    return baseline_value, baseline_evidence, {
        "valid": True, "fallback": True, "decision": "BASELINE",
        "reason": "unresolved_observation", "observations": rows,
    }
