"""All-document exact source view for v2 performance restrictions."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from ..domain.models import NoticeRecord, SourceSpan
from ..facts.metadata import build_metadata_facts, render_metadata_facts
from .native_full_prompt import DOCUMENT_ORDER


OVERVIEW_CHARS = 800
ANCHOR_MARGIN = 500
V2_ANCHOR_MARGIN = 220
V2_MAX_WINDOW_CHARS = 1600
V2_CHARACTER_CAP = 14000
QUALIFICATION = re.compile(
    r"입찰\s*참가\s*자격|참가\s*자격|참여\s*자격|제안\s*참가\s*자격|"
    r"아래의\s*자격|자격을\s*모두|참가할\s*수\s*있는"
)
PERFORMANCE = re.compile(
    r"과거\s*실적|수행\s*실적|납품\s*실적|이행\s*실적|계약\s*실적|"
    r"유사\s*실적|동종\s*실적|실적\s*증명|실적이\s*있는|실적을\s*보유|실적"
)
SCOPE_OR_EXCEPTION = re.compile(
    r"계약사무규칙|공기업|준정부기관|특수한\s*설비|특수한\s*기술|"
    r"특수\s*설비|특수\s*기술|물품\s*제조|일반\s*용역"
)


@dataclass(frozen=True)
class V2SourceCandidate:
    source_id: str
    span: SourceSpan
    categories: tuple[str, ...]


@dataclass(frozen=True)
class V2PerformanceView:
    notice_id: str
    version: str
    candidates: tuple[V2SourceCandidate, ...]
    document_coverage: tuple[dict[str, Any], ...]


def _merge_windows(
    windows: list[tuple[int, int, set[str]]],
) -> list[tuple[int, int, set[str]]]:
    merged: list[tuple[int, int, set[str]]] = []
    for start, end, categories in sorted(windows):
        if merged and start <= merged[-1][1]:
            old_start, old_end, old_categories = merged[-1]
            merged[-1] = (
                old_start, max(old_end, end), old_categories | categories,
            )
        else:
            merged.append((start, end, set(categories)))
    return merged


def build_v2_performance_view(record: NoticeRecord) -> V2PerformanceView:
    if not record.documents:
        raise ValueError(f"{record.notice_id}: no supplied documents")
    unknown = {document.document_type for document in record.documents} - set(DOCUMENT_ORDER)
    if unknown:
        raise ValueError(f"{record.notice_id}: unknown document types: {sorted(unknown)}")
    candidates: list[V2SourceCandidate] = []
    coverage: list[dict[str, Any]] = []
    for document in sorted(
        record.documents,
        key=lambda value: (DOCUMENT_ORDER[value.document_type], value.order),
    ):
        windows: list[tuple[int, int, set[str]]] = [
            (0, min(OVERVIEW_CHARS, len(document.text)), {"overview"}),
        ]
        counts = {"qualification": 0, "performance": 0, "scope_exception": 0}
        for category, pattern in (
            ("qualification", QUALIFICATION),
            ("performance", PERFORMANCE),
            ("scope_exception", SCOPE_OR_EXCEPTION),
        ):
            for match in pattern.finditer(document.text):
                counts[category] += 1
                windows.append((
                    max(0, match.start() - ANCHOR_MARGIN),
                    min(len(document.text), match.end() + ANCHOR_MARGIN),
                    {category},
                ))
        merged = _merge_windows(windows)
        for start, end, categories in merged:
            span = SourceSpan(
                record.notice_id, document.doc_id, document.document_type,
                document.order, start, end, document.text[start:end], document.sha256,
            )
            span.validate(document)
            candidates.append(V2SourceCandidate(
                source_id=f"P{len(candidates) + 1:03d}", span=span,
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
        })
    return V2PerformanceView(
        notice_id=record.notice_id, version="v1",
        candidates=tuple(candidates), document_coverage=tuple(coverage),
    )


def render_v2_performance_view(view: V2PerformanceView) -> str:
    lines = ["모든 제공 문서를 검사해 얻은 실적·참가자격·적용범위 관련 원문 조각:"]
    for candidate in view.candidates:
        span = candidate.span
        lines.append(
            f"[{candidate.source_id} | {span.document_type}/{span.document_id} "
            f"{span.start}:{span.end} | 탐색범주={','.join(candidate.categories)}]\n"
            f"{span.exact_text}"
        )
    return "\n\n".join(lines)


def _bounded_merge(
    windows: list[tuple[int, int, set[str]]],
) -> list[tuple[int, int, set[str]]]:
    merged: list[tuple[int, int, set[str]]] = []
    for start, end, categories in sorted(windows):
        if merged and start <= merged[-1][1] and end - merged[-1][0] <= V2_MAX_WINDOW_CHARS:
            old_start, old_end, old_categories = merged[-1]
            merged[-1] = (old_start, max(old_end, end), old_categories | categories)
        else:
            merged.append((start, end, set(categories)))
    return merged


def build_v2_performance_view_v2(record: NoticeRecord) -> V2PerformanceView:
    if not record.documents:
        raise ValueError(f"{record.notice_id}: no supplied documents")
    unknown = {document.document_type for document in record.documents} - set(DOCUMENT_ORDER)
    if unknown:
        raise ValueError(f"{record.notice_id}: unknown document types: {sorted(unknown)}")
    ordered_documents = sorted(
        record.documents,
        key=lambda value: (DOCUMENT_ORDER[value.document_type], value.order),
    )
    raw_candidates: list[tuple[SourceSpan, tuple[str, ...], bool]] = []
    coverage: list[dict[str, Any]] = []
    for document in ordered_documents:
        overview_end = min(OVERVIEW_CHARS, len(document.text))
        windows: list[tuple[int, int, set[str]]] = [
            (0, overview_end, {"overview"}),
        ]
        counts = {"qualification": 0, "performance": 0, "scope_exception": 0}
        for category, pattern in (
            ("qualification", QUALIFICATION),
            ("performance", PERFORMANCE),
            ("scope_exception", SCOPE_OR_EXCEPTION),
        ):
            for match in pattern.finditer(document.text):
                counts[category] += 1
                windows.append((
                    max(0, match.start() - V2_ANCHOR_MARGIN),
                    min(len(document.text), match.end() + V2_ANCHOR_MARGIN),
                    {category},
                ))
        merged = _bounded_merge(windows)
        for start, end, categories in merged:
            span = SourceSpan(
                record.notice_id, document.doc_id, document.document_type,
                document.order, start, end, document.text[start:end], document.sha256,
            )
            span.validate(document)
            raw_candidates.append((span, tuple(sorted(categories)), start == 0))
        coverage.append({
            "doc_id": document.doc_id,
            "type": document.document_type,
            "order": document.order,
            "characters": len(document.text),
            "inspected": True,
            "hit_counts": counts,
            "candidate_count": len(merged),
        })

    def priority(index: int) -> tuple[int, int, int, int, int]:
        span, categories, overview = raw_candidates[index]
        category_set = set(categories)
        joint = "qualification" in category_set and "performance" in category_set
        return (
            int(overview), int(joint),
            int("performance" in category_set),
            int("qualification" in category_set),
            -span.document_order * 1000000 - span.start,
        )

    selected: set[int] = set()
    used = 0
    for index in sorted(range(len(raw_candidates)), key=priority, reverse=True):
        span, _, overview = raw_candidates[index]
        length = len(span.exact_text)
        if used + length > V2_CHARACTER_CAP:
            if overview:
                raise ValueError("v2 character cap cannot retain every document overview")
            continue
        selected.add(index)
        used += length
    selected_rows = sorted(
        (raw_candidates[index] for index in selected),
        key=lambda row: (DOCUMENT_ORDER[row[0].document_type], row[0].document_order,
                         row[0].start),
    )
    candidates = tuple(
        V2SourceCandidate(f"P{index:03d}", span, categories)
        for index, (span, categories, _) in enumerate(selected_rows, start=1)
    )
    return V2PerformanceView(record.notice_id, "v2", candidates, tuple(coverage))


V2_OBSERVATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "performance_participation": {"type": "string", "enum": ["Y", "N", "U"]},
        "procurement_role": {
            "type": "string",
            "enum": ["manufacture", "purchase_supply", "service", "works", "other", "U"],
        },
        "explicit_allowance": {"type": "string", "enum": ["Y", "N", "U"]},
        "enterprise_rule_applies": {"type": "string", "enum": ["Y", "N", "U"]},
        "quote": {"type": ["string", "null"], "maxLength": 500},
    },
    "required": [
        "performance_participation", "procurement_role",
        "explicit_allowance", "enterprise_rule_applies", "quote",
    ],
    "additionalProperties": False,
}

V2_OBSERVATION_SYSTEM = """공공 입찰공고의 v2 판단에 필요한 원문 사실만 관측한다.
최종 위반 라벨은 출력하지 않는다. 주최측 입력 메타와 모든 제공 문서의
source-grounded 후보를 대조하고, 후보의 탐색범주만으로 결론내리지 않는다.

performance_participation: 과거 완료된 계약·납품·수행 실적의 금액·규모·
수량이 입찰 참가자격의 문턱이면 Y. 평가점수, 특별신인도, 적격심사,
낙찰자 심사자료, 단순 이력·경력 소개뿐이면 N. 역할이 불명하면 U.

procurement_role: 이 공고의 실제 계약 목적이 제조, 물품 구매·공급,
용역, 공사, 그 밖의 것 중 무엇인지 각각 manufacture, purchase_supply,
service, works, other로 답한다. 입력과 원문이 충돌하면 U. 물품 구매를
물품 제조로 바꾸지 않는다.

explicit_allowance: 바로 그 실적을 참가자격으로 제한하는 명시적 허용
근거가 공고와 카드의 허용 조건상 확인되면 Y. 근거가 없으면 N.
법 적용 또는 허용 조건이 불명하면 U. 일반 법령 이름이나 `기술` 단어만
있다고 Y로 만들지 않는다. 고시금액 비교 자체는 여기서 하지 않는다.

enterprise_rule_applies: 공기업·준정부기관 계약사무규칙이 이 입찰에
실제로 적용된다고 확인되면 Y. 다른 규칙이 확인되면 N. 기관명이나
소관구분만으로 Y로 만들지 않고, 불명하면 U.

performance_participation=Y라면 quote는 그 제한을 직접 보여주는 제공
문서 원문의 변경 없는 연속 1~500자다. 그 밖에는 null이다.
JSON 이외에는 출력하지 않는다."""

_V1_PERFORMANCE_DEFINITION = """performance_participation: 과거 완료된 계약·납품·수행 실적의 금액·규모·
수량이 입찰 참가자격의 문턱이면 Y. 평가점수, 특별신인도, 적격심사,
낙찰자 심사자료, 단순 이력·경력 소개뿐이면 N. 역할이 불명하면 U."""
_V2_PERFORMANCE_DEFINITION = """performance_participation: 다음 두 사실이 같은 실적 제한에 대해
모두 확인될 때만 Y다. (1) 과거 완료 실적에 명시적인 최소 금액·규모·수량
하한이 있다. (2) 그 하한을 충족하지 못한 업체는 입찰 또는 제안에 참가할
수 없다. `경험이 있는` 정도의 서술, 관련 업무 이력, 기관유형 제한은
정량 하한이 없으면 N이다. 평가표의 점수·등급, 적격심사, 낙찰자 심사,
실적증명서 서식, 계약 후 이행기준은 수치가 있어도 참가 문턱이 아니면
N이다. 두 사실의 연결이 불명하면 U다."""
if V2_OBSERVATION_SYSTEM.count(_V1_PERFORMANCE_DEFINITION) != 1:
    raise RuntimeError("v2 base observation paragraph changed")
V2_OBSERVATION_SYSTEM_V2 = V2_OBSERVATION_SYSTEM.replace(
    _V1_PERFORMANCE_DEFINITION, _V2_PERFORMANCE_DEFINITION,
)


def build_v2_performance_task(
    record: NoticeRecord, card_text: str, view: V2PerformanceView,
) -> dict[str, Any]:
    if view.notice_id != record.notice_id or view.version != "v2":
        raise ValueError("v2 task requires matching bounded v2 view")
    if not card_text.strip():
        raise ValueError("v2 card is required")
    if {row["doc_id"] for row in view.document_coverage} != {
        document.doc_id for document in record.documents
    }:
        raise ValueError("v2 source view omits a document")
    metadata = render_metadata_facts(build_metadata_facts(record.metadata, ("v2",)))
    return {
        "id": record.notice_id,
        "arm": "NATIVE_V2_PERFORMANCE_OBSERVATION_V1",
        "messages": [
            {"role": "system", "content": V2_OBSERVATION_SYSTEM},
            {"role": "user", "content": (
                f"[공고] {record.notice_id}\n\n[v2 판정 계약]\n{card_text}\n\n"
                f"[v2에 필요한 주최측 입력 사실]\n{metadata}\n\n"
                f"[모든 제공 문서의 source-grounded 후보]\n"
                f"{render_v2_performance_view(view)}"
            )},
        ],
        "schema": V2_OBSERVATION_SCHEMA,
    }


def build_v2_performance_task_v2(
    record: NoticeRecord, card_text: str, view: V2PerformanceView,
) -> dict[str, Any]:
    task = build_v2_performance_task(record, card_text, view)
    task["arm"] = "NATIVE_V2_PERFORMANCE_OBSERVATION_V2"
    task["messages"][0]["content"] = V2_OBSERVATION_SYSTEM_V2
    return task
