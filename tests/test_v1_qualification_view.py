"""V1 qualification source windows retain all-document provenance."""

from __future__ import annotations

from src.pps_ai.domain.models import NoticeDocument, NoticeRecord
from src.pps_ai.views.v1_qualification import (
    build_v1_qualification_view, build_v1_qualification_view_v2,
)


def test_v1_view_scans_attachments_and_validates_exact_spans() -> None:
    documents = (
        NoticeDocument.from_raw("n1", 0, {
            "doc_id": "N", "type": "공고문", "text": "공고 개요" + "가" * 1800,
        }),
        NoticeDocument.from_raw("n1", 1, {
            "doc_id": "A", "type": "제안요청서",
            "text": "첨부 개요" + "나" * 1600 + "대학교만 입찰 참가 가능" + "다" * 500,
        }),
    )
    record = NoticeRecord("n1", documents, {}, {}, {}, {})
    view = build_v1_qualification_view(record)
    assert [row["doc_id"] for row in view.document_coverage] == ["N", "A"]
    assert all(row["inspected"] for row in view.document_coverage)
    assert any(
        "대학교만 입찰 참가 가능" in candidate.span.exact_text
        for candidate in view.candidates
    )
    for candidate in view.candidates:
        candidate.span.validate(documents[candidate.span.document_order])


def test_v1_view_does_not_turn_missing_search_terms_into_a_label() -> None:
    document = NoticeDocument.from_raw("n1", 0, {
        "doc_id": "N", "type": "공고문", "text": "간단한 입찰 공고문",
    })
    record = NoticeRecord("n1", (document,), {}, {}, {}, {})
    view = build_v1_qualification_view(record)
    assert view.document_coverage[0]["hit_counts"] == {
        "qualification": 0, "entity": 0,
    }
    assert len(view.candidates) == 1
    assert view.candidates[0].span.exact_text == document.text


def test_v2_uses_qualification_context_not_unrelated_entity_mentions() -> None:
    text = (
        "공고 개요" + "가" * 1600 + "발주기관 시설 안내" + "나" * 1600
        + "입찰 참가자격: 대학교만 가능" + "다" * 500
    )
    document = NoticeDocument.from_raw("n1", 0, {
        "doc_id": "N", "type": "공고문", "text": text,
    })
    record = NoticeRecord("n1", (document,), {}, {}, {}, {})
    v1 = build_v1_qualification_view(record)
    v2 = build_v1_qualification_view_v2(record)
    assert v1.version == "v1"
    assert v2.version == "v2"
    assert len(v1.candidates) > len(v2.candidates)
    assert any("입찰 참가자격: 대학교만 가능" in row.span.exact_text
               for row in v2.candidates)
    assert not any("발주기관 시설 안내" in row.span.exact_text
                   for row in v2.candidates)
