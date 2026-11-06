"""Source-grounded v22 briefing qualification observation."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from ..domain.models import NoticeRecord, SourceSpan
from ..facts.metadata import build_metadata_facts, render_metadata_facts
from .native_full_prompt import DOCUMENT_ORDER


OVERVIEW_CHARS = 800
ANCHOR_MARGIN = 550
BRIEFING = re.compile(
    r"현장\s*설명|사업\s*설명|제안\s*요청서\s*설명|설명회|"
    r"불참|미참석|참석하지\s*아니|참석업체|참석한\s*자"
)
QUALIFICATION = re.compile(
    r"입찰\s*참가\s*자격|참가\s*자격|제안서\s*제출\s*자격|"
    r"입찰\s*참가\s*대상|입찰\s*참가는\s*허용되지|접수하지\s*않"
)


@dataclass(frozen=True)
class V22SourceCandidate:
    source_id: str
    span: SourceSpan
    categories: tuple[str, ...]


@dataclass(frozen=True)
class V22BriefingView:
    notice_id: str
    version: str
    candidates: tuple[V22SourceCandidate, ...]
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


def build_v22_briefing_view(record: NoticeRecord) -> V22BriefingView:
    if not record.documents:
        raise ValueError(f"{record.notice_id}: no supplied documents")
    unknown = {document.document_type for document in record.documents} - set(DOCUMENT_ORDER)
    if unknown:
        raise ValueError(f"{record.notice_id}: unknown document types: {sorted(unknown)}")
    candidates: list[V22SourceCandidate] = []
    coverage: list[dict[str, Any]] = []
    for document in sorted(
        record.documents,
        key=lambda value: (DOCUMENT_ORDER[value.document_type], value.order),
    ):
        windows: list[tuple[int, int, set[str]]] = [
            (0, min(OVERVIEW_CHARS, len(document.text)), {"overview"}),
        ]
        counts = {"briefing": 0, "qualification": 0}
        for category, pattern in (
            ("briefing", BRIEFING), ("qualification", QUALIFICATION),
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
            candidates.append(V22SourceCandidate(
                source_id=f"S{len(candidates) + 1:03d}",
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
        })
    return V22BriefingView(
        record.notice_id, "v1", tuple(candidates), tuple(coverage),
    )


def render_v22_briefing_view(view: V22BriefingView) -> str:
    lines = ["모든 제공 문서를 검사해 얻은 설명회·참가자격 관련 원문 조각:"]
    for candidate in view.candidates:
        span = candidate.span
        lines.append(
            f"[{candidate.source_id} | {span.document_type}/{span.document_id} "
            f"{span.start}:{span.end} | 탐색범주={','.join(candidate.categories)}]\n"
            f"{span.exact_text}"
        )
    return "\n\n".join(lines)


V22_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "negotiated": {"type": "string", "enum": ["Y", "N", "U"]},
        "briefing": {"type": "string", "enum": ["Y", "N", "U"]},
        "exclusion": {"type": "string", "enum": ["Y", "N", "U"]},
        "quote": {"type": ["string", "null"], "maxLength": 500},
    },
    "required": ["negotiated", "briefing", "exclusion", "quote"],
    "additionalProperties": False,
}
V22_PHASE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "negotiated": {"type": "string", "enum": ["Y", "N", "U"]},
        "pre_submission_briefing": {"type": "string", "enum": ["Y", "N", "U"]},
        "pre_submission_bar": {"type": "string", "enum": ["Y", "N", "U"]},
        "proposal_evaluation_session": {"type": "string", "enum": ["Y", "N", "U"]},
        "quote": {"type": ["string", "null"], "maxLength": 500},
    },
    "required": [
        "negotiated", "pre_submission_briefing", "pre_submission_bar",
        "proposal_evaluation_session", "quote",
    ],
    "additionalProperties": False,
}


SYSTEM_MESSAGE = """공공 입찰공고의 v22에 필요한 세 사실만 관측한다.
최종 위반 Y/N은 출력하지 않는다.

negotiated는 이 입찰의 계약방식이 협상에 의한 계약이면 Y, 다른 방식이면
N, 제공된 주최측 입력 사실과 문서가 충돌하거나 확인할 수 없으면 U다.

briefing은 입찰·제안서 제출 전에 발주기관이 여는 현장설명회 또는
사업설명회가 있으면 Y다. 단순 자료 안내, 제안서 발표·평가, 계약 후
착수·중간·최종 보고회는 N이다. 개최 여부를 알 수 없으면 U다.

exclusion은 바로 그 설명회에 참석하지 않은 업체가 입찰 또는 제안서
제출을 할 수 없다고 명시되면 Y다. 안내·권고·선택 참석이거나 발표자
불참 시 서면평가처럼 입찰 참가 자체가 열려 있으면 N이다. 불명하면 U다.

exclusion=Y일 때 quote는 미참석자의 입찰·제안 제출 배제를 직접 보여주는
제공 문서 원문의 변경 없는 연속 1~500자다. 그 밖에는 quote=null이다.
모든 제공 문서를 scan한 후보와 주최측 입력 사실을 대조한다. `설명회`,
`참석` 단어만으로 Y를 만들지 않는다. JSON 이외에는 출력하지 않는다."""
SYSTEM_MESSAGE_V2 = """공공 입찰공고의 v22에 필요한 절차 관계만 관측한다.
최종 위반 Y/N은 출력하지 않는다. 설명회라는 이름보다 그 행사의 시점과
불참 효과를 구분한다. 두 종류 행사가 함께 있으면 각각 따로 관측한다.

negotiated는 이 입찰의 계약방식이 협상에 의한 계약이면 Y, 다른 방식이면
N, 주최측 입력 사실과 문서가 충돌하거나 확인할 수 없으면 U다.

pre_submission_briefing은 입찰·제안서 제출 전에 발주기관이 사업내용이나
현장을 설명하는 행사가 있으면 Y다. 이미 제출한 제안서를 발표·설명하고
평가위원이 질의하는 세션이나 계약 후 보고회만 있으면 N이다. 모든 제공
문서를 scan한 후보에 어느 쪽 행사도 없으면 N, 역할이 불명하면 U다.

pre_submission_bar는 바로 그 입찰 전 설명회에 불참하면 입찰 참가 또는
제안서 제출 자격이 없거나 제안서를 접수하지 않는다고 명시되면 Y다.
불참해도 제출 가능한 안내·권고이거나, 이미 제출된 제안자를 발표평가에서
제외·서면평가하는 효과만 있으면 N이다. 역할이 불명하면 U다.

proposal_evaluation_session은 이미 제안서를 제출한 업체의 발표·질의응답·
평가 세션이면 Y다. 그 세션 불참자를 평가대상에서 제외하거나 입찰 포기로
간주한다는 문구도 이 축에는 Y지만 pre_submission_bar를 Y로 만들지 않는다.
입찰 전 사업·현장설명회만 있으면 N, 불명하면 U다.

pre_submission_bar=Y일 때 quote는 미참석자의 입찰·제안서 제출 배제를
직접 보여주는 제공 문서 원문의 변경 없는 연속 1~500자다. 그 밖에는
quote=null이다. `설명회`, `참석`, `제외` 단어만으로 절차 단계를 바꾸지
않는다. JSON 이외에는 출력하지 않는다."""


def build_v22_briefing_task(
    record: NoticeRecord, card_text: str, view: V22BriefingView,
) -> dict[str, Any]:
    if view.notice_id != record.notice_id or view.version != "v1":
        raise ValueError("v22 task requires matching v1 view")
    if not card_text.strip():
        raise ValueError("v22 card is required")
    if {row["doc_id"] for row in view.document_coverage} != {
        document.doc_id for document in record.documents
    }:
        raise ValueError("v22 source view omits a document")
    metadata = render_metadata_facts(build_metadata_facts(record.metadata, ("v22",)))
    return {
        "id": record.notice_id,
        "arm": "NATIVE_V22_BRIEFING_OBSERVATION_V1",
        "messages": [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": (
                f"[공고] {record.notice_id}\n\n[v22 판정 계약]\n{card_text}\n\n"
                f"[v22에 필요한 주최측 입력 사실]\n{metadata}\n\n"
                f"[모든 제공 문서의 source-grounded 후보]\n"
                f"{render_v22_briefing_view(view)}"
            )},
        ],
        "schema": V22_SCHEMA,
    }


def build_v22_phase_task(
    record: NoticeRecord, card_text: str, view: V22BriefingView,
) -> dict[str, Any]:
    task = build_v22_briefing_task(record, card_text, view)
    task["arm"] = "NATIVE_V22_PHASE_RELATION_OBSERVATION_V2"
    task["messages"][0]["content"] = SYSTEM_MESSAGE_V2
    task["schema"] = V22_PHASE_SCHEMA
    return task
