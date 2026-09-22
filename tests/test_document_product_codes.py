"""Document-code facts keep provenance and never infer purchased-item role."""

from __future__ import annotations

from src.pps_ai.domain.models import NoticeDocument, NoticeRecord
from src.pps_ai.facts.document_product_codes import (
    collect_document_product_mentions, render_document_product_mentions,
)


def test_document_codes_scan_attachments_and_preserve_exact_context() -> None:
    notice = NoticeDocument.from_raw("n1", 0, {
        "doc_id": "D0", "type": "공고문", "text": "공고 안내",
    })
    attachment = NoticeDocument.from_raw("n1", 1, {
        "doc_id": "D1", "type": "규격서",
        "text": "구매 품명 A[1234567890]; 자격용 B[0987654321]",
    })
    record = NoticeRecord("n1", (notice, attachment), {}, {}, {}, {})
    mentions = collect_document_product_mentions(record, {
        "1234567890": {"세부품명": "대상품", "특이사항": "특정 용도만 적용"},
    })
    assert len(mentions) == 2
    assert mentions[0].code_span.document_id == "D1"
    assert mentions[0].code_span.exact_text == "1234567890"
    assert mentions[0].context_span.exact_text == attachment.text
    assert mentions[0].special_note == "특정 용도만 적용"
    assert mentions[1].csv_name is None
    rendered = render_document_product_mentions(mentions)
    assert "구매대상인지 참가자격용인지 별도 확인" in rendered
    assert "특정 용도만 적용" in rendered
    assert "D1" in rendered


def test_embedded_longer_digit_string_is_not_a_ten_digit_code() -> None:
    document = NoticeDocument.from_raw("n1", 0, {
        "doc_id": "D0", "type": "공고문",
        "text": "12345678901 1234567890 012345678901",
    })
    record = NoticeRecord("n1", (document,), {}, {}, {}, {})
    mentions = collect_document_product_mentions(record, {})
    assert [mention.code for mention in mentions] == ["1234567890"]
