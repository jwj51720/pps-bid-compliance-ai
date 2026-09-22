"""Exact full-document windows and a label-blind bounded source view."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ..domain.models import NoticeRecord, SourceSpan


WINDOW_CHARS = 950
STRIDE_CHARS = 450

# Topic words from organizer item descriptions/cards, never dev-label examples.
TOPIC_LEXEMES = (
    "참가자격", "실적", "지역", "본점", "중소기업", "소기업", "소상공인",
    "직접생산", "확약서", "공동", "지분", "설명회", "모델", "제조사",
    "규격", "계약방법", "추정가격", "제안서", "제출서류", "업종", "면허",
    "공고일", "납품", "금액", "예산", "기술지원", "과업", "제한",
)


@dataclass(frozen=True)
class SourceWindow:
    span: SourceSpan
    topic_count: int


@dataclass(frozen=True)
class BoundedSourceView:
    selected: tuple[SourceWindow, ...]
    omitted: tuple[SourceWindow, ...]
    inspected_documents: tuple[str, ...]
    selected_characters: int
    character_cap: int


def build_source_windows(record: NoticeRecord) -> tuple[SourceWindow, ...]:
    windows: list[SourceWindow] = []
    for document in record.documents:
        for start in range(0, len(document.text), STRIDE_CHARS):
            end = min(start + WINDOW_CHARS, len(document.text))
            span = SourceSpan(
                notice_id=record.notice_id,
                document_id=document.doc_id,
                document_type=document.document_type,
                document_order=document.order,
                start=start,
                end=end,
                exact_text=document.text[start:end],
                document_sha256=document.sha256,
            )
            span.validate(document)
            score = sum(lexeme in span.exact_text for lexeme in TOPIC_LEXEMES)
            windows.append(SourceWindow(span, score))
    return tuple(windows)


def select_bounded_source_view(
    record: NoticeRecord,
    windows: Sequence[SourceWindow],
    *,
    character_cap: int = 18000,
) -> BoundedSourceView:
    if character_cap < 1:
        raise ValueError("positive character cap required")
    expected_documents = {document.doc_id for document in record.documents}
    indexed_documents = {window.span.document_id for window in windows}
    if indexed_documents != expected_documents:
        raise ValueError("source-window index does not cover all documents")
    document_map = {document.doc_id: document for document in record.documents}
    for window in windows:
        window.span.validate(document_map[window.span.document_id])

    priority: list[int] = []
    first_by_document: dict[str, int] = {}
    for index, window in enumerate(windows):
        first_by_document.setdefault(window.span.document_id, index)
    priority.extend(first_by_document.values())
    mandatory_ids = set(priority)
    remainder = sorted(
        (index for index in range(len(windows)) if index not in mandatory_ids),
        key=lambda index: (-windows[index].topic_count,
                           windows[index].span.document_order,
                           windows[index].span.start),
    )
    priority.extend(remainder)

    selected_ids: set[int] = set()
    used = 0
    required = mandatory_ids
    for index in priority:
        length = len(windows[index].span.exact_text)
        if used + length <= character_cap:
            selected_ids.add(index)
            used += length
        elif index in required:
            raise ValueError("character cap cannot retain one window per document")
    selected = tuple(windows[index] for index in range(len(windows)) if index in selected_ids)
    omitted = tuple(windows[index] for index in range(len(windows)) if index not in selected_ids)
    return BoundedSourceView(
        selected=selected,
        omitted=omitted,
        inspected_documents=tuple(document.doc_id for document in record.documents),
        selected_characters=used,
        character_cap=character_cap,
    )


def evidence_covered(windows: Sequence[SourceWindow], evidence: str) -> bool:
    return any(evidence in window.span.exact_text for window in windows)


def render_source_view(view: BoundedSourceView) -> str:
    lines = ["[주최측 제공 문서에서 확인한 변경 없는 원문 조각]"]
    for window in view.selected:
        span = window.span
        lines.append(
            f"[{span.document_type}/{span.document_id} {span.start}:{span.end}]\n"
            f"{span.exact_text}"
        )
    return "\n\n".join(lines)
