"""Candidate-keyed serialization for the unchanged v3 monetary semantics."""

from __future__ import annotations

import json
from typing import Any, Mapping

from .v3_monetary import build_v3_monetary_task, decide_v3_monetary


def build_v3_keyed_schema(view: Mapping[str, Any]) -> dict[str, Any]:
    source_ids = [candidate.source_id for candidate in view["candidates"]]
    observation = {
        "type": "object",
        "additionalProperties": False,
        "required": ["role", "requirement_basis", "mandatory", "amount_surface"],
        "properties": {
            "role": {
                "type": "string",
                "enum": [
                    "BID_QUALIFICATION", "EVALUATION", "EXPERIENCE_DESCRIPTION",
                    "FORM", "OTHER",
                ],
            },
            "requirement_basis": {
                "type": "string", "enum": ["AGGREGATE", "SINGLE_CONTRACT", "UNKNOWN"],
            },
            "mandatory": {"type": "string", "enum": ["NO", "UNKNOWN", "YES"]},
            "amount_surface": {
                "type": ["string", "null"], "minLength": 1, "maxLength": 80,
            },
        },
    }
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


def build_v3_keyed_task(record: Mapping[str, Any], view: Mapping[str, Any]) -> dict[str, Any]:
    task = build_v3_monetary_task(record, view)
    old = (
        "아래의 모든 candidate를 source_id별로 정확히 한 번씩\n"
        "분류한다. candidate를 빠뜨리거나 같은 source_id를 중복 출력하지 않는다."
    )
    new = (
        "observations 객체에는 아래의 모든 candidate ID를 각각 정확히 한 번 key로 사용한다.\n"
        "각 key의 value에는 그 candidate의 분류만 출력하며 source_id 필드를 다시 쓰지 않는다."
    )
    system = str(task["messages"][0]["content"])
    if old not in system:
        raise ValueError("v3 base serialization instruction changed unexpectedly")
    task["messages"][0]["content"] = system.replace(old, new)
    task["arm"] = "V3_MONETARY_KEYED_V11"
    task["schema"] = build_v3_keyed_schema(view)
    return task


def adapt_keyed_response(
    response: Mapping[str, Any], view: Mapping[str, Any],
) -> dict[str, Any] | None:
    if response.get("finish_reason") != "stop" or response.get("invalid") is True:
        return None
    try:
        parsed = json.loads(str(response.get("content", "")))
    except (TypeError, ValueError):
        return None
    expected = [candidate.source_id for candidate in view["candidates"]]
    if not isinstance(parsed, dict) or set(parsed) != {"observations"}:
        return None
    observations = parsed["observations"]
    if not isinstance(observations, dict) or set(observations) != set(expected):
        return None
    rows = []
    for source_id in expected:
        value = observations[source_id]
        if not isinstance(value, dict) or "source_id" in value:
            return None
        rows.append({"source_id": source_id, **value})
    adapted = dict(response)
    adapted["content"] = json.dumps({"observations": rows}, ensure_ascii=False)
    return adapted


def decide_v3_keyed(
    record: Mapping[str, Any],
    view: Mapping[str, Any],
    response: Mapping[str, Any],
    baseline_value: int,
    baseline_evidence: str,
) -> tuple[int, str, dict[str, Any]]:
    adapted = adapt_keyed_response(response, view)
    if adapted is None:
        return baseline_value, baseline_evidence, {
            "valid": False,
            "fallback": True,
            "decision": "BASELINE",
            "reason": "invalid_keyed_response",
            "observations": [],
        }
    return decide_v3_monetary(
        record, view, adapted, baseline_value, baseline_evidence,
    )

