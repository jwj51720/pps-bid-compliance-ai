"""Independent, full-source 24-item input construction for admission audit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ..domain.models import NoticeRecord
from ..facts.metadata import build_metadata_facts, render_metadata_facts
from ..facts.product_codes import build_product_facts, render_product_facts


ITEM_IDS = tuple(f"v{index}" for index in range(1, 25))
BLANK_EVIDENCE = {10, 11, 16, 18, 20}
DOCUMENT_ORDER = {
    "공고문": 0, "규격서": 1, "과업지시서": 2,
    "제안요청서": 3, "예외공표서": 4,
}

SYSTEM_MESSAGE = """당신은 공공 입찰공고의 24개 법령 점검항목을 각각 독립적으로 검토한다.
각 항목에서 먼저 적용대상과 필수 사실을 확인하고, 다음으로 실제 제한·의무가
언제 누구에게 작용하는지 확인한 뒤, 같은 조건에 적용되는 예외를 검토한다.
평가자료·낙찰 후 이행조건·전자조달 입력을 공고문의 참가자격으로 바꾸지 않는다.
불명확한 사실을 추측해 위반으로 만들지 않는다. 한 항목의 결론을 다른 항목의
근거로 자동 전파하지 않는다. 문서가 여러 개이면 모두 읽고 문서 간 역할과
상충하는 내용을 함께 대조한다.

출력은 지정된 JSON 한 개다. v1부터 v24까지 각각 0 또는 1로 답한다.
e1부터 e24까지는 v=1의 근거가 실제 제공 문서에 있는 경우에만, 해당 문서
본문의 연속된 변경 없는 1~500자를 복사한다. 메타데이터·카드·제목표지를
근거 문자열로 쓰지 않는다. v=0이면 e는 빈 문자열이다. e10, e11, e16,
e18, e20은 v와 무관하게 항상 빈 문자열이다. JSON 밖 설명을 쓰지 않는다."""


def load_card_texts(path: str | Path) -> dict[str, str]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("card artifact must be an object")
    cards = raw.get("cards")
    if not isinstance(cards, dict) or set(cards) != set(ITEM_IDS):
        raise ValueError("card artifact must contain exactly v1-v24")
    result: dict[str, str] = {}
    for item_id in ITEM_IDS:
        card = cards[item_id]
        if not isinstance(card, dict):
            raise ValueError(f"{item_id}: invalid card")
        name, condition = card.get("item_name"), card.get("prompt_text")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{item_id}: missing name")
        if not isinstance(condition, str) or not condition.strip():
            raise ValueError(f"{item_id}: missing condition")
        result[item_id] = f"{item_id} — {name}\n{condition}"
    return result


def _schema() -> dict[str, Any]:
    properties: dict[str, Any] = {}
    for index in range(1, 25):
        properties[f"v{index}"] = {"type": "integer", "enum": [0, 1]}
    for index in range(1, 25):
        properties[f"e{index}"] = (
            {"type": "string", "enum": [""]}
            if index in BLANK_EVIDENCE
            else {"type": "string", "maxLength": 500}
        )
    return {
        "type": "object", "properties": properties,
        "required": list(properties), "additionalProperties": False,
    }


def _ordered_documents(record: NoticeRecord) -> list[Any]:
    unknown = {document.document_type for document in record.documents} - set(DOCUMENT_ORDER)
    if unknown:
        raise ValueError(f"{record.notice_id}: unknown document types: {sorted(unknown)}")
    return sorted(
        record.documents,
        key=lambda document: (DOCUMENT_ORDER[document.document_type], document.order),
    )


def build_native_full_task(
    record: NoticeRecord,
    cards: Mapping[str, str],
    product_index: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    if set(cards) != set(ITEM_IDS):
        raise ValueError("native full task requires all 24 cards")
    metadata_text = render_metadata_facts(build_metadata_facts(record.metadata, ITEM_IDS))
    product_text = render_product_facts(build_product_facts(record.metadata, product_index))
    card_text = "\n\n".join(cards[item_id] for item_id in ITEM_IDS)
    document_text = "\n\n".join(
        f"[문서 {number}: {document.document_type} / {document.doc_id}]\n{document.text}"
        for number, document in enumerate(_ordered_documents(record), 1)
    )
    user_message = (
        f"[판정 대상 공고] {record.notice_id}\n\n"
        f"[24개 항목별 판정 계약]\n{card_text}\n\n"
        f"[주최측 전자조달 입력 사실]\n{metadata_text}\n\n"
        f"[경쟁제품 CSV exact-code 대조 사실]\n{product_text}\n\n"
        f"[실제 공고 자료 — 모든 제공 문서]\n{document_text}"
    )
    return {
        "id": record.notice_id,
        "arm": "NATIVE_FULL_INPUT_FEASIBILITY_V1",
        "messages": [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": user_message},
        ],
        "schema": _schema(),
    }
