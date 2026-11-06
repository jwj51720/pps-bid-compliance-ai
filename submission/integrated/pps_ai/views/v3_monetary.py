"""Label-blind exact source views for v3 monetary qualification relations."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence


MONEY_PATTERN = re.compile(
    r"(?:"
    r"\d+(?:\.\d+)?\s*억\s*원?"
    r"|\d+(?:\.\d+)?\s*천만\s*원?"
    r"|\d+(?:\.\d+)?\s*만\s*원"
    r"|\d[\d, ]{2,}\s*천\s*원"
    r"|\d[\d, ]{2,}\s*원"
    r")"
)
ANCHOR_PATTERN = re.compile(r"실적")
BEFORE_CHARACTERS = 350
AFTER_CHARACTERS = 500
MAX_CANDIDATE_CHARACTERS = BEFORE_CHARACTERS + AFTER_CHARACTERS + 2


@dataclass(frozen=True)
class V3MonetaryCandidate:
    source_id: str
    doc_id: str
    document_type: str
    document_order: int
    start: int
    end: int
    text: str


def _merge_windows(windows: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(windows):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def build_v3_monetary_view(record: Mapping[str, Any]) -> dict[str, Any]:
    """Inspect every document and retain exact windows with 실적 plus money."""
    candidates: list[V3MonetaryCandidate] = []
    coverage: list[dict[str, Any]] = []
    for order, document in enumerate(record.get("docs") or []):
        text = str(document["text"])
        windows = []
        anchor_count = 0
        for match in ANCHOR_PATTERN.finditer(text):
            anchor_count += 1
            start = max(0, match.start() - BEFORE_CHARACTERS)
            end = min(len(text), match.end() + AFTER_CHARACTERS)
            if MONEY_PATTERN.search(text[start:end]):
                windows.append((start, end))
        merged = _merge_windows(windows)
        for start, end in merged:
            candidates.append(V3MonetaryCandidate(
                source_id=f"M{len(candidates) + 1:02d}",
                doc_id=str(document["doc_id"]),
                document_type=str(document["type"]),
                document_order=order,
                start=start,
                end=end,
                text=text[start:end],
            ))
        coverage.append({
            "doc_id": str(document["doc_id"]),
            "type": str(document["type"]),
            "order": order,
            "characters": len(text),
            "inspected": True,
            "performance_anchor_count": anchor_count,
            "monetary_candidate_count": len(merged),
            "state": "FOUND_SELECTED" if merged else "NOT_FOUND",
        })
    return {
        "id": str(record["id"]),
        "module_id": "native-v3-monetary-view-v1",
        "document_coverage": coverage,
        "candidates": candidates,
        "omission_policy": {
            "selection": "all exact windows containing 실적 and a monetary surface",
            "before_characters": BEFORE_CHARACTERS,
            "after_characters": AFTER_CHARACTERS,
            "candidate_limit": None,
        },
    }


def candidate_index(view: Mapping[str, Any]) -> dict[str, V3MonetaryCandidate]:
    return {candidate.source_id: candidate for candidate in view["candidates"]}


def render_candidates(candidates: Sequence[V3MonetaryCandidate]) -> str:
    return "\n\n".join(
        f"[{candidate.source_id} | {candidate.document_type}:{candidate.doc_id} | "
        f"위치={candidate.start}~{candidate.end}]\n{candidate.text}"
        for candidate in candidates
    )

