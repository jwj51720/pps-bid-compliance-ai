from __future__ import annotations

import json

from src.pps_ai.decisions.v4_allowance_axes import (
    build_v4_axis_task,
    parse_v4_axis_observations,
    reduce_v4_axis_observations,
)
from src.pps_ai.views.v4_requirement_scope import build_v4_requirement_scope_view


def _record(text: str) -> dict[str, object]:
    return {"id": "N1", "docs": [{"doc_id": "D0", "type": "공고문", "text": text}]}


def _value(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "r": "Q", "m": "Y", "x": "I", "i": "N", "a": "E", "n": "N", "q": None,
    }
    value.update(changes)
    return value


def _response(source_id: str, value: dict[str, object]) -> dict[str, object]:
    return {
        "finish_reason": "stop", "invalid": False,
        "content": json.dumps({"observations": {source_id: value}}, ensure_ascii=False),
    }


def test_schema_and_prompt_separate_issuer_from_work_allowance() -> None:
    record = _record("2. 입찰참가자격\n공공기관 발주 유사사업 실적이 있어야 한다.")
    candidates = build_v4_requirement_scope_view(record)["candidates"]
    task = build_v4_axis_task(record, candidates)
    properties = task["schema"]["properties"]["observations"]["properties"]["R001"]
    assert properties["required"] == ["r", "m", "x", "i", "a", "n", "q"]
    assert properties["properties"]["i"]["enum"] == ["B", "N", "U"]
    assert properties["properties"]["a"]["enum"] == ["E", "N", "U"]
    assert "발주기관군과 사업내용은 독립된 축" in task["messages"][0]["content"]
    assert "같은 제한축의 실질적 허용" in task["messages"][1]["content"]


def test_equivalent_work_does_not_cancel_issuer_restriction() -> None:
    record = _record("공공기관 발주 유사사업 실적이 있어야 한다.")
    candidates = build_v4_requirement_scope_view(record)["candidates"]
    source = candidates[0]
    response = _response(
        source.source_id,
        _value(q="공공기관 발주 유사사업 실적이 있어야 한다"),
    )
    rows, reason = parse_v4_axis_observations(response, candidates)
    assert reason is None and rows is not None
    value, evidence, diagnostic = reduce_v4_axis_observations(rows, candidates, 0, "")
    assert value == 1
    assert evidence == "공공기관 발주 유사사업 실적이 있어야 한다"
    assert diagnostic["decision"] == "POSITIVE_PROOF"


def test_broad_issuer_allowance_excludes_issuer_restriction() -> None:
    record = _record("공공기관 발주 실적 또는 민간 발주 실적 허용")
    candidates = build_v4_requirement_scope_view(record)["candidates"]
    rows, reason = parse_v4_axis_observations(
        _response(candidates[0].source_id, _value(i="B", a="N")), candidates,
    )
    assert reason is None and rows is not None
    value, _, diagnostic = reduce_v4_axis_observations(rows, candidates, 1, "old")
    assert value == 0 and diagnostic["decision"] == "NEGATIVE_PROOF"


def test_work_restriction_uses_work_allowance_not_issuer_allowance() -> None:
    record = _record("특정 사업 실적 제한")
    candidates = build_v4_requirement_scope_view(record)["candidates"]
    source_id = candidates[0].source_id
    for fields, expected in [
        ({"x": "S", "i": "N", "a": "E"}, 0),
        ({"x": "S", "i": "B", "a": "N", "q": "특정 사업 실적 제한"}, 1),
    ]:
        rows, reason = parse_v4_axis_observations(
            _response(source_id, _value(**fields)), candidates,
        )
        assert reason is None and rows is not None
        value, _, _ = reduce_v4_axis_observations(rows, candidates, 0, "")
        assert value == expected


def test_positive_quote_is_source_resolved_and_unrelated_quote_is_ignored() -> None:
    record = _record("공공기관  발주 실적 제한")
    candidates = build_v4_requirement_scope_view(record)["candidates"]
    source_id = candidates[0].source_id
    rows, reason = parse_v4_axis_observations(
        _response(source_id, _value(q="공공기관 발주 실적 제한")), candidates,
    )
    assert reason is None and rows is not None
    assert rows[0]["q"] == "공공기관  발주 실적 제한"

    rows, reason = parse_v4_axis_observations(
        _response(source_id, _value(q="없는 문구")), candidates,
    )
    assert rows is None and reason == "positive_quote_not_exact"

    rows, reason = parse_v4_axis_observations(
        _response(source_id, _value(r="F", m="N", q="관계 없는 인용")), candidates,
    )
    assert reason is None and rows is not None and rows[0]["q"] is None


def test_unknown_axis_falls_back_without_default_positive() -> None:
    record = _record("공공기관 실적 제한")
    candidates = build_v4_requirement_scope_view(record)["candidates"]
    rows, reason = parse_v4_axis_observations(
        _response(candidates[0].source_id, _value(i="U", q=None)), candidates,
    )
    assert reason is None and rows is not None
    value, evidence, diagnostic = reduce_v4_axis_observations(rows, candidates, 1, "old")
    assert (value, evidence) == (1, "old")
    assert diagnostic["reason"] == "unresolved_observation"
