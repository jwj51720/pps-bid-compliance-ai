"""V17 relation windows retain provenance without interpreting labels."""

from __future__ import annotations

from src.pps_ai.domain.models import NoticeDocument, NoticeRecord
from src.pps_ai.views.v17_full_source import build_v17_relation_task
from src.pps_ai.views.v17_relation_view import (
    build_v17_relation_view, build_v17_relation_view_v2,
    build_v17_relation_view_v3,
)


def test_every_document_is_inspected_and_spans_are_exact() -> None:
    documents = (
        NoticeDocument.from_raw("n1", 0, {
            "doc_id": "D0", "type": "공고문",
            "text": "공고 개요" + "가" * 1500 + "중소기업 참가자격" + "나" * 700,
        }),
        NoticeDocument.from_raw("n1", 1, {
            "doc_id": "D1", "type": "규격서",
            "text": "제품 규격" + "다" * 1500 + "1234567890" + "라" * 700,
        }),
    )
    record = NoticeRecord("n1", documents, {}, {}, {}, {})
    view = build_v17_relation_view(record)
    assert [row["doc_id"] for row in view.document_coverage] == ["D0", "D1"]
    assert all(row["inspected"] for row in view.document_coverage)
    assert view.document_coverage[0]["hit_counts"]["enterprise"] == 1
    assert view.document_coverage[1]["hit_counts"]["product_code"] == 1
    assert any("1234567890" in candidate.span.exact_text for candidate in view.candidates)
    for candidate in view.candidates:
        candidate.span.validate(documents[candidate.span.document_order])


def test_relation_task_uses_source_spans_not_full_document() -> None:
    text = "공고 개요" + "가" * 5000 + "중소기업 참가자격" + "나" * 5000
    document = NoticeDocument.from_raw("n1", 0, {
        "doc_id": "D0", "type": "공고문", "text": text,
    })
    record = NoticeRecord("n1", (document,), {
        "입찰추정가격": 50_000_000, "업무구분": "일반용역",
        "계약방법": "제한경쟁", "조항호내용": "입력 조항",
        "세부품명번호목록": None,
    }, {}, {}, {})
    task = build_v17_relation_task(record, "v17 카드", {}, build_v17_relation_view(record))
    user = task["messages"][1]["content"]
    assert "중소기업 참가자격" in user
    assert "[모든 문서의 source-grounded 관계 단서]" in user
    assert "가" * 4000 not in user
    assert task["arm"] == "NATIVE_V17_RELATION_VIEW_OBSERVATION_V1"


def test_v2_adds_card_exception_sources_without_changing_v1() -> None:
    phrase = "다른 법률에 따른 지명계약"
    text = "공고 개요" + "가" * 2500 + phrase + "나" * 2500
    document = NoticeDocument.from_raw("n1", 0, {
        "doc_id": "D0", "type": "공고문", "text": text,
    })
    record = NoticeRecord("n1", (document,), {}, {}, {}, {})
    v1 = build_v17_relation_view(record)
    v2 = build_v17_relation_view_v2(record)
    assert v1.version == "v1"
    assert v2.version == "v2"
    assert not any(phrase in row.span.exact_text for row in v1.candidates)
    assert any(phrase in row.span.exact_text for row in v2.candidates)


def test_v3_adds_deep_purchase_target_without_changing_v2() -> None:
    phrase = "구매내역: 의료 장비 일식"
    text = "공고 개요" + "가" * 2500 + phrase + "나" * 2500
    document = NoticeDocument.from_raw("n1", 0, {
        "doc_id": "D0", "type": "공고문", "text": text,
    })
    record = NoticeRecord("n1", (document,), {}, {}, {}, {})
    v2 = build_v17_relation_view_v2(record)
    v3 = build_v17_relation_view_v3(record)
    assert v2.version == "v2"
    assert v3.version == "v3"
    assert not any(phrase in row.span.exact_text for row in v2.candidates)
    assert any(phrase in row.span.exact_text for row in v3.candidates)
    assert v3.document_coverage[0]["hit_counts"]["purchase"] == 1
    for candidate in v3.candidates:
        candidate.span.validate(document)
