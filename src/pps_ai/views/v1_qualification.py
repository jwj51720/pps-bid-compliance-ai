"""Source-only v1 qualification windows from every supplied document."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from ..domain.models import NoticeRecord, SourceSpan
from .native_full_prompt import DOCUMENT_ORDER


OVERVIEW_CHARS = 1000
QUALIFICATION_MARGIN = 320
ENTITY_MARGIN = 250
QUALIFICATION = re.compile(
    r"입찰\s*참가\s*자격|참가\s*자격|참여\s*자격|참여\s*가능|"
    r"참가\s*가능|참여할\s*수|참가할\s*수|입찰에\s*참가|"
    r"참가자는|참여자는|입찰\s*자격"
)
ENTITY = re.compile(
    r"대학|산학협력단|연구기관|기관|법인|조직|인력|인원|시설|"
    r"서비스망|사업소|지사|지점|보유한|보유하고|제조물품"
)


@dataclass(frozen=True)
class V1SourceCandidate:
    source_id: str
    span: SourceSpan
    categories: tuple[str, ...]


@dataclass(frozen=True)
class V1QualificationView:
    notice_id: str
    version: str
    candidates: tuple[V1SourceCandidate, ...]
    document_coverage: tuple[dict[str, Any], ...]


def _merge_windows(
    windows: list[tuple[int, int, set[str]]],
) -> list[tuple[int, int, set[str]]]:
    merged: list[tuple[int, int, set[str]]] = []
    for start, end, categories in sorted(windows):
        if merged and start <= merged[-1][1]:
            previous_start, previous_end, previous_categories = merged[-1]
            merged[-1] = (
                previous_start,
                max(previous_end, end),
                previous_categories | categories,
            )
        else:
            merged.append((start, end, set(categories)))
    return merged


def build_v1_qualification_view(record: NoticeRecord) -> V1QualificationView:
    return _build_view(record, "v1", QUALIFICATION_MARGIN, include_entity=True)


def build_v1_qualification_view_v2(record: NoticeRecord) -> V1QualificationView:
    return _build_view(record, "v2", 450, include_entity=False)


def _build_view(
    record: NoticeRecord,
    version: str,
    qualification_margin: int,
    include_entity: bool,
) -> V1QualificationView:
    if not record.documents:
        raise ValueError(f"{record.notice_id}: no supplied documents")
    unknown = {document.document_type for document in record.documents} - set(DOCUMENT_ORDER)
    if unknown:
        raise ValueError(f"{record.notice_id}: unknown document types: {sorted(unknown)}")
    candidates: list[V1SourceCandidate] = []
    coverage: list[dict[str, Any]] = []
    for document in sorted(
        record.documents,
        key=lambda value: (DOCUMENT_ORDER[value.document_type], value.order),
    ):
        counts = {"qualification": 0, "entity": 0}
        windows: list[tuple[int, int, set[str]]] = [
            (0, min(OVERVIEW_CHARS, len(document.text)), {"overview"})
        ]
        patterns = [("qualification", QUALIFICATION, qualification_margin)]
        if include_entity:
            patterns.append(("entity", ENTITY, ENTITY_MARGIN))
        for category, pattern, margin in patterns:
            for match in pattern.finditer(document.text):
                counts[category] += 1
                windows.append((
                    max(0, match.start() - margin),
                    min(len(document.text), match.end() + margin),
                    {category},
                ))
        merged = _merge_windows(windows)
        for start, end, categories in merged:
            span = SourceSpan(
                record.notice_id, document.doc_id, document.document_type,
                document.order, start, end, document.text[start:end], document.sha256,
            )
            span.validate(document)
            candidates.append(V1SourceCandidate(
                f"Q{len(candidates) + 1:03d}", span, tuple(sorted(categories)),
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
    return V1QualificationView(record.notice_id, version, tuple(candidates), tuple(coverage))


def render_v1_qualification_view(view: V1QualificationView) -> str:
    lines = ["모든 제공 문서를 검사해 얻은 참가자격 관련 원문 조각:"]
    for candidate in view.candidates:
        span = candidate.span
        lines.append(
            f"[{candidate.source_id} | {span.document_type}/{span.document_id} "
            f"{span.start}:{span.end} | 탐색범주={','.join(candidate.categories)}]"
            f"\n{span.exact_text}"
        )
    return "\n\n".join(lines)


SYSTEM_MESSAGE = """공공 입찰공고의 v1 참가자격 제한을 검토한다.
실제 입찰 참가 가능 여부를 정하는 조건과 평가·증빙·계약이행·과업조건을
구분한다. 특정 기관·법인·인력·시설 표현만으로 위반을 확정하지 말고
일반 적격자의 대안 및 명시적 허용 자격을 함께 살핀다. 원문 조각은
모든 문서를 검사해 찾은 부분이지 전체 문서가 아니다. 보이지 않는
부분에 조건이 없다고 추정하지 않는다. 판단에 필요한 사실이 빠져
있으면 U로 답한다. quote는 제공 문서 원문의 변경 없는 1~500자다.
JSON 이외에는 출력하지 않는다."""
SYSTEM_MESSAGE_V3 = """공공 입찰공고의 v1 참가자격 제한만 검토한다.
Y는 카드의 1 조건이 충족된 위반, N은 카드의 0 조건이 충족된 비위반,
U는 제공된 참가자격 후보가 서로 충돌하거나 판정에 필요한 문맥이 실제로
부족한 경우다. 모든 제공 문서를 scan하여 참가자격 표현 주변을 모았으므로,
원문 전체가 아니라는 이유만으로 U를 선택하지 않는다. 실제 입찰 참가
가능 여부와 평가·증빙서식·계약이행·과업조건을 구분하고, 기관·법인·
인력·시설 단어의 존재만으로 Y를 선택하지 않는다.

Y일 때 quote는 그 위반 제한을 직접 보여주는 제공 문서 원문의 변경 없는
연속 1~500자다. N 또는 U일 때 quote는 반드시 null이다. JSON 이외에는
출력하지 않는다."""
OBSERVATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "state": {"type": "string", "enum": ["Y", "N", "U"]},
        "quote": {"type": ["string", "null"], "maxLength": 500},
    },
    "required": ["state", "quote"],
    "additionalProperties": False,
}
AXIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "target": {"type": "string", "enum": ["Y", "N", "U"]},
        "allowed": {"type": "string", "enum": ["Y", "N", "U"]},
        "quote": {"type": ["string", "null"], "maxLength": 500},
    },
    "required": ["target", "allowed", "quote"],
    "additionalProperties": False,
}
SYSTEM_MESSAGE_V4 = """공공 입찰공고의 v1에 필요한 두 사실만 관측한다.
최종 위반 Y/N은 출력하지 않는다.

target=Y는 실제 입찰 참가자격이 특정 기관 종류·법인 형태 또는 입찰자
자체의 조직·상시 인력·보유 시설·서비스망으로 일반 적격자를 제한하는
경우다. 실적금액·실적대상, 영업소 지역, 법정 등록·허가·면허·신고,
제품·기술 조건만 있는 경우 target=N이다. 평가, 증빙서식, 낙찰 후
이행조건도 target=N이다. 후보가 충돌하거나 역할을 판별할 수 없으면 U다.

allowed는 target=Y인 바로 그 제한이 특수 기술·안전·이행 필요 또는
명시적 허용 근거에 직접 연결되면 Y, 그런 근거가 확인되지 않으면 N,
불명하면 U다. target=N이면 allowed=U다.

target=Y일 때 quote는 해당 제한을 직접 보여주는 제공 문서 원문의 변경
없는 연속 1~500자다. target=N/U이면 quote는 null이다. 모든 제공 문서를
scan한 후보를 보고 답하되 기관·인력·시설 단어만으로 target=Y를 만들지
않는다. JSON 이외에는 출력하지 않는다."""
SYSTEM_MESSAGE_V5 = """공공 입찰공고의 v1에 필요한 두 사실만 관측한다.
최종 위반 Y/N은 출력하지 않는다.

target=Y는 실제 참가자격이 현재 입찰자 자신을 특정 기관 종류·법인 형태로
한정하거나, 입찰자 자신의 임의 조직·상시 인력·보유 시설·서비스망을
요구하여 일반 적격자를 제한하는 경우다. 기관명이 과거 실적의 발주기관·
납품처·고객·사업대상으로만 등장하면 target=N이다. 중소기업·중기업·
소기업·소상공인 등 기업규모 조건도 target=N이다. 실적금액·실적대상,
영업소 지역, 법정 등록·허가·면허·신고, 제품·기술 조건, 평가,
증빙서식, 낙찰 후 이행조건만 있는 경우 target=N이다. 후보가 충돌하거나
역할을 판별할 수 없으면 U다.

allowed는 target=Y인 바로 그 제한이 특수 기술·안전·이행 필요 또는
명시적 허용 근거에 직접 연결되면 Y, 그런 근거가 확인되지 않으면 N,
불명하면 U다. target=N이면 allowed=U다.

target=Y일 때 quote는 해당 제한을 직접 보여주는 제공 문서 원문의 변경
없는 연속 1~500자다. target=N/U이면 quote는 null이다. 모든 제공 문서를
scan한 후보를 보고 답하되 기관·인력·시설 단어만으로 target=Y를 만들지
않는다. JSON 이외에는 출력하지 않는다."""


def build_v1_qualification_task(
    record: NoticeRecord, card_text: str, view: V1QualificationView,
) -> dict[str, Any]:
    if view.notice_id != record.notice_id or view.version != "v2":
        raise ValueError("v1 task requires matching v2 view")
    if not card_text.strip():
        raise ValueError("v1 card is required")
    if {row["doc_id"] for row in view.document_coverage} != {
        document.doc_id for document in record.documents
    }:
        raise ValueError("v1 source view omits a document")
    return {
        "id": record.notice_id,
        "arm": "NATIVE_V1_QUALIFICATION_OBSERVATION_V2",
        "messages": [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": (
                f"[공고] {record.notice_id}\n\n[v1 판정 계약]\n{card_text}\n\n"
                f"[모든 제공 문서의 source-grounded 후보]\n"
                f"{render_v1_qualification_view(view)}"
            )},
        ],
        "schema": OBSERVATION_SCHEMA,
    }


def build_v1_qualification_task_v3(
    record: NoticeRecord, card_text: str, view: V1QualificationView,
) -> dict[str, Any]:
    task = build_v1_qualification_task(record, card_text, view)
    task["arm"] = "NATIVE_V1_QUALIFICATION_OBSERVATION_V3"
    task["messages"][0]["content"] = SYSTEM_MESSAGE_V3
    return task


def build_v1_qualification_axis_task(
    record: NoticeRecord, card_text: str, view: V1QualificationView,
) -> dict[str, Any]:
    task = build_v1_qualification_task(record, card_text, view)
    task["arm"] = "NATIVE_V1_QUALIFICATION_AXIS_OBSERVATION_V4"
    task["messages"][0]["content"] = SYSTEM_MESSAGE_V4
    task["schema"] = AXIS_SCHEMA
    return task


def build_v1_bidder_relation_task(
    record: NoticeRecord, card_text: str, view: V1QualificationView,
) -> dict[str, Any]:
    task = build_v1_qualification_axis_task(record, card_text, view)
    task["arm"] = "NATIVE_V1_BIDDER_RELATION_OBSERVATION_V5"
    task["messages"][0]["content"] = SYSTEM_MESSAGE_V5
    return task
