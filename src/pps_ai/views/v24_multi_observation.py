"""Label-blind exact source views for multi-observation v24 comparison."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence


AXIS_TERMS: dict[str, tuple[str, ...]] = {
    "amount": (
        "사업예산", "사업비", "총사업비", "소요예산", "예산액", "추정가격",
        "기초금액",
    ),
    "contract": (
        "계약방법", "입찰방법", "입찰방식", "계약방식", "일반경쟁", "제한경쟁",
        "지명경쟁", "수의계약", "수의견적", "협상에 의한 계약",
    ),
    "region": (
        "주된 영업소", "본점 소재지", "본사 소재지", "사업장 소재지", "소재지가",
        "소재한 업체", "소재한 자", "지역제한", "관할구역", "지역 업체",
    ),
    "industry": (
        "업종코드", "업종 코드", "업종을 등록", "입찰참가자격 등록", "면허업종",
        "면허를", "허가를 받은", "신고를 한", "등록한 업체", "등록한 자",
        "등록을 필한", "직접생산확인",
    ),
}

AXIS_PREFIX = {"amount": "A", "contract": "C", "region": "R", "industry": "I"}
MAX_WINDOW_CHARACTERS = 2000


@dataclass(frozen=True)
class V24AtomicCandidate:
    source_id: str
    axis: str
    doc_id: str
    document_type: str
    document_order: int
    start: int
    end: int
    text: str
    terms: tuple[str, ...]


def _blocks(text: str) -> list[tuple[int, int]]:
    """Return non-empty blank-line separated blocks with exact offsets."""
    separators = list(re.finditer(r"\n[ \t]*\n", text))
    boundaries = [0] + [match.end() for match in separators]
    ends = [match.start() for match in separators] + [len(text)]
    blocks = []
    for start, end in zip(boundaries, ends):
        while start < end and text[start] in "\r\n":
            start += 1
        while end > start and text[end - 1] in "\r\n":
            end -= 1
        if text[start:end].strip():
            blocks.append((start, end))
    return blocks or [(0, len(text))]


def _table_aware_window(
    text: str, blocks: Sequence[tuple[int, int]], position: int, term_length: int,
) -> tuple[int, int]:
    block_index = next(
        (index for index, (start, end) in enumerate(blocks) if start <= position < end),
        0,
    )
    first = max(0, block_index - 1)
    last = min(len(blocks) - 1, block_index + 3)
    start, end = blocks[first][0], blocks[last][1]
    if end - start > MAX_WINDOW_CHARACTERS:
        start = max(blocks[block_index][0], position - 360)
        end = min(len(text), position + term_length + 760)
    return start, end


def _merge_windows(
    rows: Sequence[tuple[int, int, tuple[str, ...]]],
) -> list[tuple[int, int, tuple[str, ...]]]:
    merged: list[tuple[int, int, set[str]]] = []
    for start, end, terms in sorted(rows):
        if merged and start <= merged[-1][1] and max(end, merged[-1][1]) - merged[-1][0] <= MAX_WINDOW_CHARACTERS:
            old_start, old_end, old_terms = merged[-1]
            old_terms.update(terms)
            merged[-1] = (old_start, max(old_end, end), old_terms)
        else:
            merged.append((start, end, set(terms)))
    return [(start, end, tuple(sorted(terms))) for start, end, terms in merged]


def _round_robin_select(
    by_document: Mapping[int, Sequence[tuple[int, int, tuple[str, ...]]]],
    max_characters: int,
) -> tuple[list[tuple[int, int, int, tuple[str, ...]]], dict[int, int]]:
    selected: list[tuple[int, int, int, tuple[str, ...]]] = []
    omitted = {order: 0 for order in by_document}
    used = 0
    max_depth = max((len(rows) for rows in by_document.values()), default=0)
    for depth in range(max_depth):
        for order in sorted(by_document):
            rows = by_document[order]
            if depth >= len(rows):
                continue
            start, end, terms = rows[depth]
            length = end - start
            if used + length <= max_characters:
                selected.append((order, start, end, terms))
                used += length
            else:
                omitted[order] += 1
    selected.sort(key=lambda row: (row[0], row[1], row[2]))
    return selected, omitted


def build_v24_multi_observation_view(
    record: Mapping[str, Any], *, max_axis_characters: int = 6850,
) -> dict[str, Any]:
    documents = list(record.get("docs") or [])
    raw: dict[str, dict[int, list[tuple[int, int, tuple[str, ...]]]]] = {
        axis: {} for axis in AXIS_TERMS
    }
    document_coverage: list[dict[str, Any]] = []
    for order, document in enumerate(documents):
        text = str(document["text"])
        blocks = _blocks(text)
        counts: dict[str, int] = {}
        for axis, terms in AXIS_TERMS.items():
            windows: dict[tuple[int, int], set[str]] = {}
            for term in terms:
                for match in re.finditer(re.escape(term), text, flags=re.IGNORECASE):
                    start, end = _table_aware_window(text, blocks, match.start(), len(match.group(0)))
                    windows.setdefault((start, end), set()).add(term)
            merged = _merge_windows([
                (start, end, tuple(hits)) for (start, end), hits in windows.items()
            ])
            raw[axis][order] = merged
            counts[axis] = len(merged)
        document_coverage.append({
            "doc_id": str(document["doc_id"]),
            "type": str(document["type"]),
            "order": order,
            "characters": len(text),
            "axis_candidate_counts": counts,
            "inspected": True,
        })

    candidates: dict[str, list[V24AtomicCandidate]] = {}
    axis_coverage: dict[str, list[dict[str, Any]]] = {}
    for axis, by_document in raw.items():
        selected, omitted = _round_robin_select(by_document, max_axis_characters)
        selected_counts = {order: 0 for order in range(len(documents))}
        values: list[V24AtomicCandidate] = []
        for index, (order, start, end, terms) in enumerate(selected, 1):
            selected_counts[order] += 1
            document = documents[order]
            values.append(V24AtomicCandidate(
                source_id=f"{AXIS_PREFIX[axis]}{index:02d}",
                axis=axis,
                doc_id=str(document["doc_id"]),
                document_type=str(document["type"]),
                document_order=order,
                start=start,
                end=end,
                text=str(document["text"])[start:end],
                terms=terms,
            ))
        candidates[axis] = values
        coverage_rows = []
        for order in range(len(documents)):
            found = len(by_document.get(order, ()))
            chosen = selected_counts[order]
            missing = found - chosen
            state = "NOT_FOUND" if found == 0 else ("FOUND_SELECTED" if missing == 0 else "UNOBSERVED")
            coverage_rows.append({
                "document_order": order,
                "found": found,
                "selected": chosen,
                "omitted": missing,
                "state": state,
            })
        axis_coverage[axis] = coverage_rows
    return {
        "id": str(record["id"]),
        "module_id": "native-v24-multi-observation-view-v2",
        "document_coverage": document_coverage,
        "axis_coverage": axis_coverage,
        "candidates": candidates,
        "omission_policy": {
            "max_axis_characters": max_axis_characters,
            "selection": "document-balanced round-robin over table-aware exact windows",
        },
    }


def candidate_index(view: Mapping[str, Any]) -> dict[str, V24AtomicCandidate]:
    return {
        candidate.source_id: candidate
        for values in view["candidates"].values()
        for candidate in values
    }


def render_candidates(candidates: Sequence[V24AtomicCandidate]) -> str:
    blocks = []
    for candidate in candidates:
        blocks.append(
            f"[{candidate.source_id} | {candidate.document_type}:{candidate.doc_id} | "
            f"위치={candidate.start}~{candidate.end}]\n{candidate.text}"
        )
    return "\n\n".join(blocks) if blocks else "(후보 없음)"
