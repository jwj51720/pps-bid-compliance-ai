"""Immutable organizer-input and provenance types."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping


@dataclass(frozen=True)
class NoticeDocument:
    notice_id: str
    doc_id: str
    document_type: str
    order: int
    text: str
    sha256: str

    @classmethod
    def from_raw(cls, notice_id: str, order: int, raw: Mapping[str, Any]) -> "NoticeDocument":
        text = raw.get("text")
        if not isinstance(text, str) or not text:
            raise ValueError(f"{notice_id}: document {order} has empty/non-string text")
        doc_id = raw.get("doc_id")
        document_type = raw.get("type")
        if not isinstance(doc_id, str) or not doc_id:
            raise ValueError(f"{notice_id}: document {order} has invalid doc_id")
        if not isinstance(document_type, str) or not document_type:
            raise ValueError(f"{notice_id}: document {order} has invalid type")
        return cls(
            notice_id=notice_id,
            doc_id=doc_id,
            document_type=document_type,
            order=order,
            text=text,
            sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        )


@dataclass(frozen=True)
class NoticeRecord:
    notice_id: str
    documents: tuple[NoticeDocument, ...]
    metadata: Mapping[str, Any]
    input_completeness: Mapping[str, Any]
    dropped_document_counts: Mapping[str, Any]
    raw: Mapping[str, Any]


@dataclass(frozen=True)
class SourceSpan:
    notice_id: str
    document_id: str
    document_type: str
    document_order: int
    start: int
    end: int
    exact_text: str
    document_sha256: str

    def validate(self, document: NoticeDocument) -> None:
        if (
            self.notice_id != document.notice_id
            or self.document_id != document.doc_id
            or self.document_type != document.document_type
            or self.document_order != document.order
            or self.document_sha256 != document.sha256
        ):
            raise ValueError("source span/document identity mismatch")
        if not 0 <= self.start < self.end <= len(document.text):
            raise ValueError("source span offset out of range")
        if document.text[self.start:self.end] != self.exact_text:
            raise ValueError("source span is not an exact document substring")
