"""Label-blind exact source view for v9 target-role observability."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any, Sequence

from ..domain import NoticeRecord


# Admission surfaces only. They do not assign a role, exception, or v9 label.
SEMANTIC_SURFACE_PATTERN = re.compile(
    r"모델(?:명)?|제조사|제조업체|제작사|원제조사|상표|브랜드|제품명|품명|"
    r"형식명|정품|동등(?:품|제품| 이상)?|대체(?:품|제품| 가능)?|호환(?:품|제품| 가능)?|"
    r"part\s*(?:no\.?|number)|model|chipset|manufacturer|brand",
    re.IGNORECASE,
)
TOKEN_PATTERN = re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9][A-Za-z0-9+./_()-]{2,48}")
UNIT_TOKEN_PATTERN = re.compile(
    r"\d+(?:\.\d+)?(?:mm|cm|m|kg|g|gb|tb|mb|kb|hz|khz|mhz|ghz|w|kw|v|a|mah|"
    r"mp|dpi|rpm|lpm|bq|pci)(?:/l)?",
    re.IGNORECASE,
)
BEFORE_CHARACTERS = 650
AFTER_CHARACTERS = 650


@dataclass(frozen=True)
class V9TargetCandidate:
    source_id: str
    doc_id: str
    document_type: str
    document_order: int
    start: int
    end: int
    text: str
    sha256: str
    trigger_kinds: tuple[str, ...]
    trigger_surfaces: tuple[str, ...]


def _looks_like_identifier(surface: str) -> bool:
    if UNIT_TOKEN_PATTERN.fullmatch(surface):
        return False
    if not any(character.isdigit() for character in surface):
        return False
    if not any("A" <= character <= "Z" for character in surface):
        return False
    letters = sum(character.isalpha() for character in surface)
    return letters >= 1 and len(surface) >= 4


def _merge_windows(
    windows: Sequence[tuple[int, int, str, str]],
) -> list[tuple[int, int, tuple[str, ...], tuple[str, ...]]]:
    merged: list[tuple[int, int, list[str], list[str]]] = []
    for start, end, kind, surface in sorted(windows, key=lambda value: (value[0], value[1])):
        if merged and start <= merged[-1][1]:
            prior_start, prior_end, kinds, surfaces = merged[-1]
            merged[-1] = (
                prior_start,
                max(prior_end, end),
                [*kinds, kind],
                [*surfaces, surface],
            )
        else:
            merged.append((start, end, [kind], [surface]))
    return [
        (
            start,
            end,
            tuple(dict.fromkeys(kinds)),
            tuple(dict.fromkeys(surfaces)),
        )
        for start, end, kinds, surfaces in merged
    ]


def build_v9_target_view(record: NoticeRecord) -> dict[str, Any]:
    """Inspect every supplied document and retain broad target-relation windows."""
    candidates: list[V9TargetCandidate] = []
    coverage = []
    for document in record.documents:
        matches: list[tuple[int, int, str, str]] = []
        for match in SEMANTIC_SURFACE_PATTERN.finditer(document.text):
            matches.append((match.start(), match.end(), "SEMANTIC_MARKER", match.group(0)))
        for match in TOKEN_PATTERN.finditer(document.text):
            if _looks_like_identifier(match.group(0)):
                matches.append((match.start(), match.end(), "MODEL_LIKE_TOKEN", match.group(0)))
        windows = _merge_windows([
            (
                max(0, start - BEFORE_CHARACTERS),
                min(len(document.text), end + AFTER_CHARACTERS),
                kind,
                surface,
            )
            for start, end, kind, surface in matches
        ])
        for start, end, kinds, surfaces in windows:
            text = document.text[start:end]
            candidates.append(V9TargetCandidate(
                source_id=f"T{len(candidates) + 1:02d}",
                doc_id=document.doc_id,
                document_type=document.document_type,
                document_order=document.order,
                start=start,
                end=end,
                text=text,
                sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                trigger_kinds=kinds,
                trigger_surfaces=surfaces,
            ))
        coverage.append({
            "doc_id": document.doc_id,
            "type": document.document_type,
            "order": document.order,
            "characters": len(document.text),
            "inspected": True,
            "surface_count": len(matches),
            "candidate_count": len(windows),
            "state": "FOUND_SELECTED" if windows else "NOT_FOUND",
        })
    return {
        "id": record.notice_id,
        "module_id": "v9-target-role-view-v1",
        "document_coverage": coverage,
        "candidates": candidates,
        "omission_policy": {
            "selection": "all exact merged windows around generic target/relation surfaces",
            "before_characters": BEFORE_CHARACTERS,
            "after_characters": AFTER_CHARACTERS,
            "candidate_limit": None,
            "semantic_labeling": False,
        },
    }


def render_v9_candidates(candidates: Sequence[V9TargetCandidate]) -> str:
    return "\n\n".join(
        f"[{candidate.source_id} | {candidate.document_type}:{candidate.doc_id} | "
        f"위치={candidate.start}~{candidate.end} | sha256={candidate.sha256} | "
        f"triggers={','.join(candidate.trigger_kinds)}]\n{candidate.text}"
        for candidate in candidates
    )
