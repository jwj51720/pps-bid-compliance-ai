"""Full-document source windows preserve offsets and expose bounded omissions."""

from __future__ import annotations

import pytest

from src.pps_ai.domain.models import NoticeDocument, NoticeRecord
from src.pps_ai.views.native_source_windows import (
    build_source_windows, evidence_covered, select_bounded_source_view,
)


def _record(texts: tuple[str, ...]) -> NoticeRecord:
    documents = tuple(
        NoticeDocument.from_raw("n1", order, {
            "doc_id": f"D{order}",
            "type": "공고문" if order == 0 else "규격서",
            "text": text,
        })
        for order, text in enumerate(texts)
    )
    return NoticeRecord("n1", documents, {}, {}, {}, {})


def test_full_window_index_covers_500_character_evidence_at_stride_boundary() -> None:
    text = "가" * 430 + "나" * 500 + "다" * 800
    record = _record((text,))
    windows = build_source_windows(record)
    assert evidence_covered(windows, "나" * 500)
    assert windows[0].span.start == 0
    assert windows[-1].span.end == len(text)
    assert all(window.span.exact_text == text[window.span.start:window.span.end]
               for window in windows)


def test_bounded_view_keeps_a_provenanced_window_from_each_document() -> None:
    record = _record(("입찰참가자격" + "가" * 2000, "규격" + "나" * 2000))
    windows = build_source_windows(record)
    view = select_bounded_source_view(record, windows, character_cap=2100)
    assert view.inspected_documents == ("D0", "D1")
    assert {window.span.document_id for window in view.selected} == {"D0", "D1"}
    assert view.omitted
    assert view.selected_characters <= 2100


def test_too_small_cap_does_not_silently_drop_attachment() -> None:
    record = _record(("가" * 1000, "나" * 1000))
    with pytest.raises(ValueError, match="one window per document"):
        select_bounded_source_view(record, build_source_windows(record), character_cap=1000)
