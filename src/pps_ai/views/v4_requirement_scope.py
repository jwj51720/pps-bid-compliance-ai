"""Exact preceding heading lines for v4 candidate role interpretation."""

from __future__ import annotations

from dataclasses import replace
import re
from typing import Any, Mapping, Sequence

from .v4_requirements import (
    V4HeadingLine,
    V4RequirementCandidate,
    build_v4_requirement_view,
)


HEADING_PATTERN = re.compile(
    r"(?m)^[ \t]{0,4}(?P<number>[1-9]\d?[.)]|[가-하][.)])[ \t]*(?P<body>[^\n]{1,90})$"
)
MAX_LOOKBACK_CHARACTERS = 2500
MAX_NUMBERED_LINES = 4
MAX_LETTERED_LINES = 4


def preceding_heading_trail(text: str, candidate_start: int) -> tuple[V4HeadingLine, ...]:
    """Preserve a small exact trail; never infer which line governs a candidate."""

    lower = max(0, candidate_start - MAX_LOOKBACK_CHARACTERS)
    numbered: list[V4HeadingLine] = []
    lettered: list[V4HeadingLine] = []
    for match in HEADING_PATTERN.finditer(text, lower, candidate_start):
        if match.end() > candidate_start:
            continue
        heading = V4HeadingLine(match.start(), match.end(), text[match.start():match.end()])
        if match.group("number")[0].isdigit():
            numbered.append(heading)
        else:
            lettered.append(heading)
    selected = [*numbered[-MAX_NUMBERED_LINES:], *lettered[-MAX_LETTERED_LINES:]]
    return tuple(sorted(selected, key=lambda heading: heading.start))


def build_v4_requirement_scope_view(record: Mapping[str, Any]) -> dict[str, Any]:
    """Add label-blind source lines without altering the candidate window."""

    base = build_v4_requirement_view(record)
    documents = {str(document["doc_id"]): str(document["text"]) for document in record.get("docs") or []}
    candidates = tuple(
        replace(
            candidate,
            heading_trail=preceding_heading_trail(documents[candidate.doc_id], candidate.start),
        )
        for candidate in base["candidates"]
    )
    return {
        **base,
        "module_id": "native-v4-requirement-scope-view-v1",
        "candidates": candidates,
        "heading_policy": {
            "lookback_characters": MAX_LOOKBACK_CHARACTERS,
            "max_numbered_lines": MAX_NUMBERED_LINES,
            "max_lettered_lines": MAX_LETTERED_LINES,
            "interpretation": "exact preceding lines, not inferred parent hierarchy",
        },
    }


def render_v4_scoped_candidates(candidates: Sequence[V4RequirementCandidate]) -> str:
    blocks = []
    for candidate in candidates:
        trail = "\n".join(
            f"  {heading.start}~{heading.end}: {heading.text}"
            for heading in candidate.heading_trail
        ) or "  없음"
        blocks.append(
            f"[{candidate.source_id} | {candidate.document_type}:{candidate.doc_id} | "
            f"위치={candidate.start}~{candidate.end}]\n"
            f"[직전 제목형 원문 줄 — 소속 관계는 확정하지 않음]\n{trail}\n"
            f"[실적 후보 원문]\n{candidate.text}"
        )
    return "\n\n".join(blocks)
