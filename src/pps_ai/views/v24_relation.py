"""High-recall, label-blind source views for the four v24 comparison axes."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence


AXIS_TERMS: dict[str, tuple[str, ...]] = {
    "amount": (
        "사업예산", "사업비", "총사업비", "예산", "추정가격", "기초금액",
        "부가가치세", "부가세", "금액", "계약금액",
    ),
    "contract": (
        "계약방법", "입찰방법", "입찰방식", "일반경쟁", "제한경쟁",
        "지명경쟁", "수의계약", "수의견적", "협상에 의한 계약",
    ),
    "region": (
        "주된 영업소", "본점", "본사", "사업장 소재지", "소재지가",
        "소재한 업체", "지역제한", "관할구역", "지역 업체",
    ),
    "industry": (
        "업종코드", "업종을 등록", "입찰참가자격 등록", "면허", "허가를 받은",
        "신고를 한", "등록한 자", "등록을 필한", "사업자등록",
    ),
}

AXIS_PREFIX = {"amount": "A", "contract": "C", "region": "R", "industry": "I"}


@dataclass(frozen=True)
class V24Candidate:
    source_id: str
    axis: str
    doc_id: str
    document_type: str
    document_order: int
    start: int
    end: int
    text: str
    terms: tuple[str, ...]


def _window(text: str, position: int, term_length: int) -> tuple[int, int]:
    left_break = text.rfind("\n\n", 0, position)
    right_break = text.find("\n\n", position + term_length)
    start = 0 if left_break < 0 else left_break + 2
    end = len(text) if right_break < 0 else right_break
    if end - start > 900:
        start = max(start, position - 360)
        end = min(end, position + term_length + 520)
    return start, end


def build_v24_relation_view(
    record: Mapping[str, Any], *, max_axis_characters: int = 8000,
) -> dict[str, Any]:
    raw_candidates: dict[str, list[tuple[int, int, int, str, str, tuple[str, ...]]]] = {
        axis: [] for axis in AXIS_TERMS
    }
    document_coverage: list[dict[str, Any]] = []
    for order, document in enumerate(record.get("docs") or []):
        text = str(document["text"])
        counts: dict[str, int] = {}
        for axis, terms in AXIS_TERMS.items():
            windows: dict[tuple[int, int], set[str]] = {}
            for term in terms:
                for match in re.finditer(re.escape(term), text, flags=re.IGNORECASE):
                    start, end = _window(text, match.start(), len(match.group(0)))
                    windows.setdefault((start, end), set()).add(term)
            counts[axis] = len(windows)
            for (start, end), hits in windows.items():
                raw_candidates[axis].append((
                    order, start, end, str(document["doc_id"]),
                    str(document["type"]), tuple(sorted(hits)),
                ))
        document_coverage.append({
            "doc_id": str(document["doc_id"]),
            "type": str(document["type"]),
            "order": order,
            "characters": len(text),
            "axis_candidate_counts": counts,
            "inspected": True,
        })
    candidates: dict[str, list[V24Candidate]] = {}
    documents = list(record.get("docs") or [])
    for axis, rows in raw_candidates.items():
        rows.sort(key=lambda row: (-len(row[5]), row[0], row[1], row[2]))
        selected: list[tuple[int, int, int, str, str, tuple[str, ...]]] = []
        used = 0
        seen: set[tuple[str, int, int]] = set()
        for row in rows:
            identity = (row[3], row[1], row[2])
            if identity in seen:
                continue
            length = row[2] - row[1]
            if selected and used + length > max_axis_characters:
                continue
            selected.append(row)
            seen.add(identity)
            used += length
        selected.sort(key=lambda row: (row[0], row[1], row[2]))
        axis_candidates: list[V24Candidate] = []
        for index, row in enumerate(selected, 1):
            order, start, end, doc_id, document_type, terms = row
            text = str(documents[order]["text"])[start:end]
            axis_candidates.append(V24Candidate(
                source_id=f"{AXIS_PREFIX[axis]}{index:02d}", axis=axis,
                doc_id=doc_id, document_type=document_type,
                document_order=order, start=start, end=end, text=text, terms=terms,
            ))
        candidates[axis] = axis_candidates
    return {
        "id": str(record["id"]),
        "module_id": "native-v24-relation-view-v1",
        "document_coverage": document_coverage,
        "candidates": candidates,
        "omission_policy": {
            "max_axis_characters": max_axis_characters,
            "reason": "ranked generic axis terms then ordered exact windows",
        },
    }


def candidate_index(view: Mapping[str, Any]) -> dict[str, V24Candidate]:
    return {
        candidate.source_id: candidate
        for values in view["candidates"].values()
        for candidate in values
    }


def render_v24_candidates(candidates: Sequence[V24Candidate]) -> str:
    blocks = []
    for candidate in candidates:
        terms = ", ".join(candidate.terms)
        blocks.append(
            f"[{candidate.source_id} | {candidate.document_type}:{candidate.doc_id} | "
            f"위치={candidate.start}~{candidate.end} | 탐지어={terms}]\n{candidate.text}"
        )
    return "\n\n".join(blocks) if blocks else "(후보 없음)"
