from __future__ import annotations

import json

from src.pps_ai.decisions.v4_requirements import (
    build_v4_schema,
    build_v4_task,
    decide_v4,
)
from src.pps_ai.views.v4_requirements import build_v4_requirement_view


def _record(texts: list[str]) -> dict[str, object]:
    return {
        "id": "N1",
        "docs": [
            {"doc_id": f"D{i}", "type": "공고문" if i == 0 else "제안요청서", "text": text}
            for i, text in enumerate(texts)
        ],
    }


def _response(view: dict[str, object], values: list[dict[str, object]]) -> dict[str, object]:
    candidates = view["candidates"]
    return {
        "finish_reason": "stop",
        "invalid": False,
        "content": json.dumps({
            "observations": {
                candidate.source_id: value for candidate, value in zip(candidates, values, strict=True)
            },
        }, ensure_ascii=False),
    }


def _value(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {"r": "O", "m": "N", "x": "N", "a": "N", "n": "N", "q": None}
    value.update(changes)
    return value


def test_task_and_schema_require_every_candidate_key() -> None:
    record = _record(["참가자격 실적 조건", "평가 실적 표"])
    view = build_v4_requirement_view(record)
    schema = build_v4_schema(view["candidates"])
    assert schema["properties"]["observations"]["required"] == ["R001", "R002"]
    task = build_v4_task(record, view["candidates"])
    system = task["messages"][0]["content"]
    assert "최종 v4나 위반 0/1은 출력하지 않는다" in system
    assert "평가표와 실적증명서 양식을 참가자격으로 바꾸지 않는다" in system


def test_positive_requires_same_candidate_relation_and_exact_quote() -> None:
    record = _record(["입찰참가자는 공공기관 발주 실적이 있어야 한다."])
    view = build_v4_requirement_view(record)
    quote = "공공기관 발주 실적이 있어야 한다"
    response = _response(view, [_value(r="Q", m="Y", x="I", a="N", n="N", q=quote)])
    value, evidence, diagnostic = decide_v4(response, view["candidates"], 0, "")
    assert (value, evidence) == (1, quote)
    assert diagnostic["decision"] == "POSITIVE_PROOF"

    bad = _response(view, [_value(r="Q", m="Y", x="I", a="N", n="N", q="없는 문구")])
    value, evidence, diagnostic = decide_v4(bad, view["candidates"], 0, "")
    assert (value, evidence) == (0, "")
    assert diagnostic["fallback"]


def test_evaluation_and_form_candidates_prove_negative() -> None:
    record = _record(["평가 실적은 가점", "실적증명서 서식"])
    view = build_v4_requirement_view(record)
    response = _response(view, [_value(r="E"), _value(r="F")])
    value, evidence, diagnostic = decide_v4(response, view["candidates"], 1, "old")
    assert (value, evidence) == (0, "")
    assert diagnostic["decision"] == "NEGATIVE_PROOF"


def test_general_allowance_or_concrete_necessity_excludes_candidate() -> None:
    record = _record(["일반 유사 실적", "특정 실적이나 동등 실적 허용", "안전상 특정 실적 필요"])
    view = build_v4_requirement_view(record)
    response = _response(view, [
        _value(r="Q", m="Y", x="G"),
        _value(r="Q", m="Y", x="S", a="E"),
        _value(r="Q", m="Y", x="S", n="C"),
    ])
    value, _, diagnostic = decide_v4(response, view["candidates"], 1, "old")
    assert value == 0
    assert diagnostic["decision"] == "NEGATIVE_PROOF"


def test_unknown_or_missing_candidate_falls_back() -> None:
    record = _record(["실적 조건 불명"])
    view = build_v4_requirement_view(record)
    response = _response(view, [_value(r="U", m="U", x="U", a="U", n="U")])
    value, evidence, diagnostic = decide_v4(response, view["candidates"], 1, "old")
    assert (value, evidence) == (1, "old")
    assert diagnostic["reason"] == "unresolved_observation"

    parsed = json.loads(response["content"])
    parsed["observations"] = {}
    response["content"] = json.dumps(parsed)
    _, _, diagnostic = decide_v4(response, view["candidates"], 1, "old")
    assert diagnostic["reason"] == "candidate_key_mismatch"


def test_negative_quote_is_rejected_to_keep_evidence_contract_unambiguous() -> None:
    record = _record(["평가 실적은 가점"])
    view = build_v4_requirement_view(record)
    response = _response(view, [_value(r="E", q="평가 실적")])
    _, _, diagnostic = decide_v4(response, view["candidates"], 0, "")
    assert diagnostic["reason"] == "negative_quote_must_be_null"
