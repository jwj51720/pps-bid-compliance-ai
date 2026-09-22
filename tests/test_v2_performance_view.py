"""V2 source view scans every supplied document with exact provenance."""

from src.pps_ai.domain.models import NoticeDocument, NoticeRecord
from src.pps_ai.views.v2_performance import (
    build_v2_performance_task, build_v2_performance_view,
    build_v2_performance_task_v2, build_v2_performance_view_v2,
    render_v2_performance_view,
)


def _record() -> NoticeRecord:
    first = NoticeDocument.from_raw("n1", 0, {
        "doc_id": "D0", "type": "공고문",
        "text": "입찰참가자격: 최근 3년간 유사용역 수행실적 3천만원 이상인 업체.",
    })
    second = NoticeDocument.from_raw("n1", 1, {
        "doc_id": "D1", "type": "제안요청서",
        "text": "제안서 평가용 실적증명서를 제출한다.",
    })
    metadata = {
        "적용계약법": "국가계약법", "업무구분": "물품(내자)",
        "소관구분": "기타공공기관", "입찰추정가격": 100_000_000,
        "계약방법": "제한경쟁", "낙찰방법": "최저가",
    }
    return NoticeRecord("n1", (first, second), metadata, {}, {}, {})


def test_v2_view_covers_documents_and_preserves_exact_spans() -> None:
    record = _record()
    view = build_v2_performance_view(record)
    assert [row["doc_id"] for row in view.document_coverage] == ["D0", "D1"]
    documents = {document.doc_id: document for document in record.documents}
    assert any("3천만원" in candidate.span.exact_text for candidate in view.candidates)
    assert any("평가용" in candidate.span.exact_text for candidate in view.candidates)
    for candidate in view.candidates:
        candidate.span.validate(documents[candidate.span.document_id])


def test_v2_render_includes_source_identity_and_categories() -> None:
    rendered = render_v2_performance_view(build_v2_performance_view(_record()))
    assert "공고문/D0" in rendered
    assert "제안요청서/D1" in rendered
    assert "탐색범주=" in rendered


def test_v2_bounded_view_keeps_every_document_and_exact_provenance() -> None:
    record = _record()
    view = build_v2_performance_view_v2(record)
    assert view.version == "v2"
    assert [row["doc_id"] for row in view.document_coverage] == ["D0", "D1"]
    documents = {document.doc_id: document for document in record.documents}
    for candidate in view.candidates:
        candidate.span.validate(documents[candidate.span.document_id])


def test_v2_task_renders_card_metadata_documents_and_observation_schema() -> None:
    record = _record()
    view = build_v2_performance_view_v2(record)
    task = build_v2_performance_task(record, "1 조건: 실적 제한", view)
    assert task["arm"] == "NATIVE_V2_PERFORMANCE_OBSERVATION_V1"
    system, user = (message["content"] for message in task["messages"])
    assert "purchase_supply" in system
    assert "performance_participation" in system
    assert "입찰추정가격 입력: 100,000,000원" in user
    assert "1 조건: 실적 제한" in user
    assert "공고문/D0" in user and "제안요청서/D1" in user
    assert "최근 3년간 유사용역" in user
    assert set(task["schema"]["required"]) == {
        "performance_participation", "procurement_role",
        "explicit_allowance", "enterprise_rule_applies", "quote",
    }


def test_v2_task_revision_changes_only_performance_definition() -> None:
    record = _record()
    view = build_v2_performance_view_v2(record)
    old = build_v2_performance_task(record, "card", view)
    new = build_v2_performance_task_v2(record, "card", view)
    assert old["schema"] == new["schema"]
    assert old["messages"][1] == new["messages"][1]
    assert old["messages"][0]["role"] == new["messages"][0]["role"]
    assert "최소 금액·규모·수량" in new["messages"][0]["content"]
    assert "평가표의 점수·등급" in new["messages"][0]["content"]
    assert old["messages"][0]["content"] != new["messages"][0]["content"]
