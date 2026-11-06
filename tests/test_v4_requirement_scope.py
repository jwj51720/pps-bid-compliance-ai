from __future__ import annotations

from src.pps_ai.decisions.v4_requirements import build_v4_scope_task, build_v4_task
from src.pps_ai.views.v4_requirement_scope import build_v4_requirement_scope_view
from src.pps_ai.views.v4_requirements import build_v4_requirement_view


def _record(text: str) -> dict[str, object]:
    return {"id": "N1", "docs": [{"doc_id": "D1", "type": "공고문", "text": text}]}


def test_scope_view_preserves_candidate_and_exact_heading_provenance() -> None:
    text = (
        "3. 입찰참가자격\n\n공공기관 실적이 있는 업체\n\n"
        "7. 규격 입찰서 제출\n\n라. 제출서류\n\n"
        "1. 실적증명서 1부"
    )
    record = _record(text)
    base = build_v4_requirement_view(record)
    scoped = build_v4_requirement_scope_view(record)
    assert len(base["candidates"]) == len(scoped["candidates"])
    for before, after in zip(base["candidates"], scoped["candidates"], strict=True):
        assert (before.doc_id, before.start, before.end, before.text) == (
            after.doc_id, after.start, after.end, after.text
        )
        for heading in after.heading_trail:
            assert text[heading.start:heading.end] == heading.text
            assert heading.end <= after.start


def test_scope_prompt_exposes_heading_trail_without_declaring_parent() -> None:
    text = (
        "7. 규격 입찰서 제출\n\n라. 제출서류\n\n1. 신청서\n\n"
        + "가" * 400
        + "\n2. 실적증명서 제출"
    )
    record = _record(text)
    candidate = build_v4_requirement_scope_view(record)["candidates"][0]
    task = build_v4_scope_task(record, [candidate])
    user = task["messages"][1]["content"]
    assert "7. 규격 입찰서 제출" in user
    assert "라. 제출서류" in user
    assert "소속 관계는 확정하지 않음" in user
    assert "제출서류 목록에 실적증명서" in task["messages"][0]["content"]
    assert task["schema"] == build_v4_task(record, [candidate])["schema"]


def test_scope_view_leaves_unknown_heading_empty() -> None:
    record = _record("실적 조건")
    candidate = build_v4_requirement_scope_view(record)["candidates"][0]
    assert candidate.heading_trail == ()
    assert "  없음" in build_v4_scope_task(record, [candidate])["messages"][1]["content"]
