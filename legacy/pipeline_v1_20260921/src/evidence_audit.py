"""Offline source-observability helpers for evidence-first experiments.

These helpers deliberately use gold evidence only to evaluate a prospective
selector.  They never produce a model context, retrieval query, or label.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SourceSpan:
    """An unchanged source slice with its document provenance."""

    doc_id: str
    document_type: str
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class EvidenceLocation:
    """A gold-evidence match in one organizer document."""

    doc_id: str
    document_type: str
    start: int
    end: int
    source_text: str
    match_mode: str


def normalize_text(value: str) -> str:
    return unicodedata.normalize("NFC", value).replace("\r", "")


def paragraph_spans(record: dict[str, Any]) -> list[SourceSpan]:
    """Split documents at blank-line paragraph boundaries without rewriting text."""
    result: list[SourceSpan] = []
    for document in record["docs"]:
        text = normalize_text(document["text"])
        start = 0
        for separator in re.finditer(r"\n[ \t]*\n+", text):
            _append_span(result, document, text, start, separator.start())
            start = separator.end()
        _append_span(result, document, text, start, len(text))
    return result


def locate_evidence(record: dict[str, Any], evidence: str) -> EvidenceLocation | None:
    """Find gold evidence, allowing only whitespace-shape normalization.

    The returned ``source_text`` is always the exact original source slice.
    Whitespace fallback is audit-only; it reveals an annotation formatting
    mismatch rather than treating a paraphrase as evidence.
    """
    target = normalize_text(evidence).strip()
    if not target:
        return None
    whitespace_pattern = _whitespace_pattern(target)
    for document in record["docs"]:
        source = normalize_text(document["text"])
        start = source.find(target)
        if start >= 0:
            end = start + len(target)
            return EvidenceLocation(
                document["doc_id"], document["type"], start, end,
                source[start:end], "exact",
            )
        fallback = re.search(whitespace_pattern, source)
        if fallback:
            return EvidenceLocation(
                document["doc_id"], document["type"], fallback.start(), fallback.end(),
                source[fallback.start():fallback.end()], "whitespace_normalized",
            )
    return None


def spans_covering(location: EvidenceLocation, spans: list[SourceSpan]) -> list[SourceSpan]:
    """Return all paragraph spans touched by a located evidence slice."""
    return [
        span for span in spans
        if span.doc_id == location.doc_id
        and span.start < location.end
        and location.start < span.end
    ]


def _append_span(
    result: list[SourceSpan], document: dict[str, Any], text: str, start: int, end: int
) -> None:
    if text[start:end].strip():
        result.append(SourceSpan(
            doc_id=document["doc_id"],
            document_type=document["type"],
            start=start,
            end=end,
            text=text[start:end],
        ))


def _whitespace_pattern(value: str) -> str:
    parts = [re.escape(part) for part in re.split(r"\s+", value) if part]
    return r"\s+".join(parts)
