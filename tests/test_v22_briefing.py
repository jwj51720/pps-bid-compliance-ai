"""Native v22 source view and prompt contract."""

from src.pps_ai.domain.models import NoticeDocument, NoticeRecord
from src.pps_ai.views.v22_briefing import (
    build_v22_briefing_task, build_v22_briefing_view, build_v22_phase_task,
)


def _record() -> NoticeRecord:
    first = NoticeDocument.from_raw("n1", 0, {
        "doc_id": "D0", "type": "공고문",
        "text": "계약방법은 협상에 의한 계약입니다. 참가자격은 별도 문서를 봅니다.",
    })
    second = NoticeDocument.from_raw("n1", 1, {
        "doc_id": "D1", "type": "제안요청서",
        "text": "사업설명회를 개최하며 불참 업체는 제안서를 제출할 수 없습니다.",
    })
    return NoticeRecord(
        "n1", (first, second), {"낙찰방법": "협상에의한계약"}, {}, {}, {},
    )


def test_v22_view_covers_every_document_with_exact_spans() -> None:
    record = _record()
    view = build_v22_briefing_view(record)
    assert [row["doc_id"] for row in view.document_coverage] == ["D0", "D1"]
    documents = {document.doc_id: document for document in record.documents}
    assert any("불참 업체" in candidate.span.exact_text for candidate in view.candidates)
    for candidate in view.candidates:
        candidate.span.validate(documents[candidate.span.document_id])


def test_v22_task_renders_only_needed_human_metadata_and_contract() -> None:
    record = _record()
    task = build_v22_briefing_task(record, "1 조건: 필수 참석 제한", build_v22_briefing_view(record))
    user = task["messages"][1]["content"]
    assert "낙찰방식 입력: 협상에의한계약" in user
    assert "입찰추정가격" not in user
    assert "불참 업체는 제안서를 제출할 수 없습니다" in user
    assert task["schema"]["required"] == [
        "negotiated", "briefing", "exclusion", "quote",
    ]


def test_v22_phase_task_keeps_pre_submission_and_evaluation_separate() -> None:
    record = _record()
    task = build_v22_phase_task(record, "1 조건: 필수 참석 제한", build_v22_briefing_view(record))
    system = task["messages"][0]["content"]
    assert "pre_submission_bar" in system
    assert "proposal_evaluation_session" in system
    assert task["schema"]["required"] == [
        "negotiated", "pre_submission_briefing", "pre_submission_bar",
        "proposal_evaluation_session", "quote",
    ]
