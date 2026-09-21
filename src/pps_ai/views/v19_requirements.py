"""Label-blind exact source views for v19 requirement instances."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any, Mapping, Sequence


# Admission only. These surfaces never determine a semantic field or label.
ANCHOR_PATTERN = re.compile(
    r"확약(?:서)?|협약(?:서)?|보증서|공급\s*증명(?:원|서)?|"
    r"제조자\s*증명(?:원|서)?|정품\s*인증서",
    re.IGNORECASE,
)
BEFORE_CHARACTERS = 700
AFTER_CHARACTERS = 700


@dataclass(frozen=True)
class V19RequirementCandidate:
    source_id: str
    doc_id: str
    document_type: str
    document_order: int
    start: int
    end: int
    text: str
    sha256: str


def _merge_windows(windows: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(windows):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def build_v19_requirement_view(record: Mapping[str, Any]) -> dict[str, Any]:
    """Inspect every supplied document and retain every assurance-like window."""
    candidates: list[V19RequirementCandidate] = []
    coverage: list[dict[str, Any]] = []
    for order, document in enumerate(record.get("docs") or []):
        text = str(document["text"])
        matches = list(ANCHOR_PATTERN.finditer(text))
        windows = _merge_windows([
            (
                max(0, match.start() - BEFORE_CHARACTERS),
                min(len(text), match.end() + AFTER_CHARACTERS),
            )
            for match in matches
        ])
        for start, end in windows:
            candidate_text = text[start:end]
            candidates.append(V19RequirementCandidate(
                source_id=f"R{len(candidates) + 1:02d}",
                doc_id=str(document["doc_id"]),
                document_type=str(document["type"]),
                document_order=order,
                start=start,
                end=end,
                text=candidate_text,
                sha256=hashlib.sha256(candidate_text.encode("utf-8")).hexdigest(),
            ))
        coverage.append({
            "doc_id": str(document["doc_id"]),
            "type": str(document["type"]),
            "order": order,
            "characters": len(text),
            "inspected": True,
            "anchor_count": len(matches),
            "candidate_count": len(windows),
            "state": "FOUND_SELECTED" if windows else "NOT_FOUND",
        })
    return {
        "id": str(record["id"]),
        "module_id": "v19-requirement-instance-view-v1",
        "document_coverage": coverage,
        "candidates": candidates,
        "omission_policy": {
            "selection": "all exact windows around assurance/certificate surfaces",
            "before_characters": BEFORE_CHARACTERS,
            "after_characters": AFTER_CHARACTERS,
            "candidate_limit": None,
            "semantic_labeling": False,
        },
    }


def candidate_index(
    candidates: Sequence[V19RequirementCandidate],
) -> dict[str, V19RequirementCandidate]:
    return {candidate.source_id: candidate for candidate in candidates}


def render_candidates(candidates: Sequence[V19RequirementCandidate]) -> str:
    return "\n\n".join(
        f"[{candidate.source_id} | {candidate.document_type}:{candidate.doc_id} | "
        f"위치={candidate.start}~{candidate.end} | sha256={candidate.sha256}]\n"
        f"{candidate.text}"
        for candidate in candidates
    )
