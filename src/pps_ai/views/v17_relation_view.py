"""Exact v17 source relations from every supplied document, without labels."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from ..domain.models import NoticeRecord, SourceSpan


OVERVIEW_CHARS = 1300
ENTERPRISE_CONTEXT_CHARS = 500
EXCEPTION_CONTEXT_CHARS = 600
CODE_CONTEXT_CHARS = 150
PURCHASE_CONTEXT_CHARS = 450

ENTERPRISE = re.compile(
    r"중소기업|중[·ㆍ‧]\s*소기업|중기업|소기업|소상공인|기업\s*규모"
)
EXCEPTION = re.compile(
    r"유찰|우선조달|비영리|적격자가|3인\s*이하|2인\s*미만|"
    r"제2조의3|제2조의2|예외|특별사유"
)
EXCEPTION_V2 = re.compile(
    EXCEPTION.pattern + r"|우선구매|수의(?:계약|구매)|지명(?:계약|경쟁)|"
    r"특정\s*(?:성능|기술|품질)|목적\s*달성|다른\s*(?:법률|법령)"
)
PRODUCT_CODE = re.compile(r"(?<![0-9])[0-9]{10}(?![0-9])")
PURCHASE = re.compile(
    r"공고명|사업명|입찰건명|구매내역|구매품목|구매물품|물품내역|"
    r"입찰에\s*부치는\s*사항|사업내용|과업개요|과업내용|과업목적|"
    r"품명|용역명|구매대상|납품내역"
)


@dataclass(frozen=True)
class V17RelationSpan:
    source_id: str
    span: SourceSpan
    categories: tuple[str, ...]


@dataclass(frozen=True)
class V17RelationView:
    notice_id: str
    version: str
    candidates: tuple[V17RelationSpan, ...]
    document_coverage: tuple[dict[str, Any], ...]


def _merge(
    windows: list[tuple[int, int, set[str]]],
) -> list[tuple[int, int, set[str]]]:
    merged: list[tuple[int, int, set[str]]] = []
    for start, end, categories in sorted(windows, key=lambda row: (row[0], row[1])):
        if merged and start <= merged[-1][1]:
            previous_start, previous_end, previous_categories = merged[-1]
            merged[-1] = (
                previous_start, max(previous_end, end),
                previous_categories | categories,
            )
        else:
            merged.append((start, end, set(categories)))
    return merged


def build_v17_relation_view(record: NoticeRecord) -> V17RelationView:
    return _build_view(record, EXCEPTION, "v1")


def build_v17_relation_view_v2(record: NoticeRecord) -> V17RelationView:
    return _build_view(record, EXCEPTION_V2, "v2")


def build_v17_relation_view_v3(record: NoticeRecord) -> V17RelationView:
    return _build_view(record, EXCEPTION_V2, "v3", purchase_pattern=PURCHASE)


def _build_view(
    record: NoticeRecord,
    exception_pattern: re.Pattern[str],
    version: str,
    purchase_pattern: re.Pattern[str] | None = None,
) -> V17RelationView:
    candidates: list[V17RelationSpan] = []
    coverage: list[dict[str, Any]] = []
    for document in record.documents:
        counts = {"overview": 1, "enterprise": 0, "exception": 0, "product_code": 0}
        if purchase_pattern is not None:
            counts["purchase"] = 0
        windows: list[tuple[int, int, set[str]]] = [
            (0, min(len(document.text), OVERVIEW_CHARS), {"overview"})
        ]
        patterns = [
            ("enterprise", ENTERPRISE, ENTERPRISE_CONTEXT_CHARS),
            ("exception", exception_pattern, EXCEPTION_CONTEXT_CHARS),
            ("product_code", PRODUCT_CODE, CODE_CONTEXT_CHARS),
        ]
        if purchase_pattern is not None:
            patterns.append(("purchase", purchase_pattern, PURCHASE_CONTEXT_CHARS))
        for category, pattern, margin in patterns:
            for match in pattern.finditer(document.text):
                counts[category] += 1
                windows.append((
                    max(0, match.start() - margin),
                    min(len(document.text), match.end() + margin),
                    {category},
                ))
        merged = _merge(windows)
        for start, end, categories in merged:
            span = SourceSpan(
                record.notice_id, document.doc_id, document.document_type,
                document.order, start, end, document.text[start:end],
                document.sha256,
            )
            span.validate(document)
            candidates.append(V17RelationSpan(
                source_id=f"R{len(candidates) + 1:03d}",
                span=span,
                categories=tuple(sorted(categories)),
            ))
        coverage.append({
            "doc_id": document.doc_id,
            "type": document.document_type,
            "order": document.order,
            "characters": len(document.text),
            "inspected": True,
            "hit_counts": counts,
            "candidate_count": len(merged),
            "state": "FOUND_SELECTED" if any(
                counts[category] for category in counts if category != "overview"
            ) else "OVERVIEW_ONLY_NOT_FOUND",
        })
    return V17RelationView(
        notice_id=record.notice_id,
        version=version,
        candidates=tuple(candidates),
        document_coverage=tuple(coverage),
    )


def render_v17_relation_view(view: V17RelationView) -> str:
    lines = ["모든 제공 문서를 훑은 뒤 v17 관계 단서가 있는 원문 조각:"]
    for candidate in view.candidates:
        span = candidate.span
        roles = ",".join(candidate.categories)
        lines.append(
            f"[{candidate.source_id} | {span.document_type}/{span.document_id} "
            f"{span.start}:{span.end} | 탐색범주={roles}]\n{span.exact_text}"
        )
    return "\n\n".join(lines)
