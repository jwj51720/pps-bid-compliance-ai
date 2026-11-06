"""Label-blind exact source views for v4 performance requirements."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any, Mapping, Sequence


ANCHOR_PATTERN = re.compile(r"실적|수행\s*경험|납품\s*경험|이행\s*경험")
CLUSTER_GAP = 300
BEFORE_CHARACTERS = 350
AFTER_CHARACTERS = 500
BOUNDARY_SEARCH = 120


@dataclass(frozen=True)
class V4HeadingLine:
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class V4RequirementCandidate:
    source_id: str
    doc_id: str
    document_type: str
    document_order: int
    start: int
    end: int
    document_sha256: str
    trigger_surfaces: tuple[str, ...]
    text: str
    heading_trail: tuple[V4HeadingLine, ...] = ()


def _cluster_matches(matches: Sequence[re.Match[str]]) -> list[tuple[int, int, tuple[str, ...]]]:
    clusters: list[tuple[int, int, list[str]]] = []
    for match in matches:
        if clusters and match.start() - clusters[-1][1] <= CLUSTER_GAP:
            start, _, surfaces = clusters[-1]
            surfaces.append(match.group(0))
            clusters[-1] = (start, match.end(), surfaces)
        else:
            clusters.append((match.start(), match.end(), [match.group(0)]))
    return [
        (start, end, tuple(dict.fromkeys(surfaces)))
        for start, end, surfaces in clusters
    ]


def _expand_to_line_boundaries(text: str, start: int, end: int) -> tuple[int, int]:
    left = text.rfind("\n", max(0, start - BOUNDARY_SEARCH), start)
    if left >= 0:
        start = left + 1
    right = text.find("\n", end, min(len(text), end + BOUNDARY_SEARCH))
    if right >= 0:
        end = right
    return start, end


def build_v4_requirement_view(record: Mapping[str, Any]) -> dict[str, Any]:
    """Inspect every supplied document and retain performance-requirement windows."""

    candidates: list[V4RequirementCandidate] = []
    coverage: list[dict[str, Any]] = []
    for order, document in enumerate(record.get("docs") or []):
        text = str(document["text"])
        matches = list(ANCHOR_PATTERN.finditer(text))
        clusters = _cluster_matches(matches)
        document_candidates = 0
        for anchor_start, anchor_end, surfaces in clusters:
            start = max(0, anchor_start - BEFORE_CHARACTERS)
            end = min(len(text), anchor_end + AFTER_CHARACTERS)
            start, end = _expand_to_line_boundaries(text, start, end)
            candidate_text = text[start:end]
            if not candidate_text:
                continue
            candidates.append(V4RequirementCandidate(
                source_id=f"R{len(candidates) + 1:03d}",
                doc_id=str(document["doc_id"]),
                document_type=str(document["type"]),
                document_order=order,
                start=start,
                end=end,
                document_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                trigger_surfaces=surfaces,
                text=candidate_text,
            ))
            document_candidates += 1
        coverage.append({
            "doc_id": str(document["doc_id"]),
            "type": str(document["type"]),
            "order": order,
            "characters": len(text),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "inspected": True,
            "anchor_count": len(matches),
            "candidate_count": document_candidates,
            "state": "FOUND_SELECTED" if document_candidates else "NOT_FOUND",
        })
    return {
        "id": str(record["id"]),
        "module_id": "native-v4-requirement-view-v1",
        "document_coverage": coverage,
        "candidates": tuple(candidates),
        "omission_policy": {
            "selection": "all exact clustered performance-requirement windows",
            "anchor_surfaces": ["실적", "수행경험", "납품경험", "이행경험"],
            "cluster_gap": CLUSTER_GAP,
            "before_characters": BEFORE_CHARACTERS,
            "after_characters": AFTER_CHARACTERS,
            "candidate_limit": None,
        },
    }


def render_v4_candidates(candidates: Sequence[V4RequirementCandidate]) -> str:
    return "\n\n".join(
        f"[{candidate.source_id} | {candidate.document_type}:{candidate.doc_id} | "
        f"위치={candidate.start}~{candidate.end}]\n{candidate.text}"
        for candidate in candidates
    )
