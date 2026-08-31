"""Baseline prompt construction without retrieval or item-specific tuning."""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from src.schema import ABSENCE_ITEMS, ITEMS

DOCUMENT_ORDER = ("공고문", "규격서", "과업지시서", "제안요청서", "예외공표서")

SYSTEM_HEAD = """당신은 공공 입찰공고의 법령 위반 여부를 점검한다.
공고문, 첨부 문서, 나라장터 입력 메타를 함께 읽고 아래 24개 항목 각각의 위반 여부와 근거 문구를 판정한다.

규칙:
1. v1~v24를 모두 출력한다. 판단이 어려우면 위반여부를 0으로 둔다.
2. 근거문구는 주어진 문서에 그대로 존재하는 연속 부분문자열이어야 한다. 요약하거나 수정하지 말고 500자를 넘기지 않는다.
3. 위반여부가 0이면 근거문구는 null이다.
4. [부재탐지] 항목은 필요한 문구가 없는 경우가 위반이므로 근거문구를 항상 null로 둔다.

판정 항목:"""

STRUCTURED_GUIDANCE = """
판정 원칙:
5. 항목명을 단순 키워드 탐지로 판단하지 말고, 문서의 실제 제한 내용과 나라장터 입력 메타의 적용계약법, 업무구분, 금액, 계약·낙찰방법, 지역·업종·공동계약 정보를 함께 검토한다.
6. 각 항목에 적힌 공식 참조와 비고는 판정 시 확인할 범위를 안내한다. 제공되지 않은 법령 내용이나 공고 밖 사실을 만들어 내지 않는다.
7. 서로 비슷한 항목도 각각의 항목명·공식 참조·비고에 맞춰 독립적으로 판단한다. 문구 하나가 여러 항목의 위반을 자동으로 뜻하지는 않는다.
8. v24는 문서의 명시적 내용과 나라장터 입력 메타의 대응 필드를 비교해 실제 불일치가 확인될 때만 1로 판단한다.
"""

GUIDED_GUIDANCE = """
판정 절차:
5. 각 항목마다 먼저 공고문·첨부문서에서 해당 제한 또는 기재 여부를 확인하고, 그 다음 나라장터 입력 메타에서 적용계약법, 업무구분, 추정가격, 계약·낙찰방법, 지역·업종·공동계약 정보를 대조한다.
6. 단어 또는 숫자 하나가 보인다는 이유만으로 위반으로 판단하지 않는다. 그 문구가 해당 항목의 제한·부재·불일치를 실제로 뜻하는지 확인한다.
7. 서로 비슷한 항목은 구분한다. 한 항목에 맞는 사유가 다른 항목의 위반을 자동으로 뜻하지는 않는다.
8. v24는 문서와 메타의 대응 값이 실제로 다를 때만 1로 판단한다. 단순 표현 차이, 문서에 없는 메타 값, 추정은 불일치 근거가 아니다.
"""

SYSTEM_TAIL = """출력은 JSON 객체 하나로만 작성한다. 키는 v1~v24이고 값은
{\"위반여부\": 0 또는 1, \"근거문구\": 문자열 또는 null} 형식이다. 설명이나 머리말을 추가하지 않는다."""


def build_system_prompt(item_table: dict[str, dict[str, Any]], mode: str = "baseline") -> str:
    lines = []
    for item in ITEMS:
        definition = item_table[item]
        absence = " [부재탐지]" if item in ABSENCE_ITEMS else ""
        note = f" (참고: {definition['비고']})" if definition.get("비고") else ""
        if mode == "structured":
            lines.append(
                f"- {item}: {definition['항목명']}{absence}"
                f"{' | 비고: ' + definition['비고'] if definition.get('비고') else ''}\n"
                f"  국가계약법 참조: {definition.get('국가계약법', '')}\n"
                f"  지방계약법 참조: {definition.get('지방계약법', '')}"
            )
        else:
            lines.append(f"- {item}: {definition['항목명']}{absence}{note}")
    guidance = STRUCTURED_GUIDANCE if mode == "structured" else GUIDED_GUIDANCE if mode == "guided" else ""
    return f"{SYSTEM_HEAD}\n" + "\n".join(lines) + f"\n{guidance}\n{SYSTEM_TAIL}"


def build_document_context(record: dict[str, Any], max_chars: int | None) -> str:
    order = {name: index for index, name in enumerate(DOCUMENT_ORDER)}
    documents = sorted(
        record["docs"],
        key=lambda document: (order.get(document["type"], len(order)), document["doc_id"]),
    )
    chunks: list[str] = []
    dropped: Counter[str] = Counter()
    used = 0
    truncated = False
    for index, document in enumerate(documents):
        header = f"[{document['type']}:{document['doc_id']}]\n"
        body = document["text"]
        if max_chars is not None:
            remaining = max_chars - used - len(header)
            if remaining <= 0:
                dropped[document["type"]] += 1
                continue
            if len(body) > remaining:
                if index == 0:
                    body = body[:remaining]
                    truncated = True
                else:
                    dropped[document["type"]] += 1
                    continue
        chunk = header + body
        chunks.append(chunk)
        used += len(chunk)
    for document_type, count in (record.get("dropped_doc_counts") or {}).items():
        dropped[document_type] += count
    if truncated:
        chunks.append("[절단] 첫 문서의 뒷부분이 입력 길이 제한으로 제외됨")
    if dropped:
        summary = ", ".join(f"{key} {value}건" for key, value in sorted(dropped.items()))
        chunks.append(f"[미수록 문서] {summary}")
    return "\n\n".join(chunks)


def _ordered_documents(record: dict[str, Any]) -> list[dict[str, Any]]:
    order = {name: index for index, name in enumerate(DOCUMENT_ORDER)}
    return sorted(
        record["docs"],
        key=lambda document: (order.get(document["type"], len(order)), document["doc_id"]),
    )


def build_split_document_contexts(
    record: dict[str, Any],
    max_chars: int,
    notice_anchor_chars: int = 4000,
) -> list[str]:
    """Pack ordered documents into independently readable bounded contexts.

    The character limit is an experiment-time surrogate only. Submission code
    must replace it with the supplied Gemma tokenizer's exact token count.
    Every pass begins with a short announcement anchor when one is available;
    document fragments retain their source type and ID so a positive finding can
    be traced to its pass. A document longer than the remaining payload budget
    is split rather than silently omitted.
    """
    if max_chars < 1:
        raise ValueError("max_chars must be positive")
    documents = _ordered_documents(record)
    announcements = [document for document in documents if document["type"] == "공고문"]
    anchor = ""
    if announcements and notice_anchor_chars:
        document = announcements[0]
        header = f"[공고문 앵커:{document['doc_id']}]\n"
        body_limit = max(0, min(notice_anchor_chars, max_chars - len(header)))
        anchor = header + document["text"][:body_limit]

    # Include every source document in order. The announcement anchor is context
    # only; its full text remains part of the ordered payload.
    fragments: list[tuple[str, str]] = []
    for document in documents:
        header = f"[{document['type']}:{document['doc_id']}]\n"
        text = document["text"]
        fragments.append((header, text))

    contexts: list[str] = []
    current: list[str] = []
    used = 0
    anchor_prefix = (anchor + "\n\n") if anchor else ""
    payload_limit = max_chars - len(anchor_prefix)
    if payload_limit <= 0:
        # A tiny configured limit must still make forward progress.
        anchor_prefix = ""
        payload_limit = max_chars

    def flush() -> None:
        nonlocal current, used
        if current:
            contexts.append(anchor_prefix + "\n\n".join(current))
            current = []
            used = 0

    for header, text in fragments:
        available_for_body = payload_limit - len(header)
        if available_for_body <= 0:
            raise ValueError("max_chars is too small to include a document header")
        offset = 0
        while offset < len(text) or (not text and offset == 0):
            separator_chars = 2 if current else 0
            remaining = payload_limit - used - separator_chars - len(header)
            if remaining <= 0:
                flush()
                continue
            if offset == 0 and len(text) <= remaining:
                current.append(header + text)
                used += separator_chars + len(header) + len(text)
                offset = len(text)
                continue
            if offset == 0 and current:
                flush()
                continue
            take = min(remaining, len(text) - offset)
            if take <= 0:
                flush()
                continue
            continuation = "" if offset == 0 else f" [계속 {offset}]"
            fragment_header = header.rstrip("\n") + continuation + "\n"
            separator_chars = 2 if current else 0
            body_room = payload_limit - used - separator_chars - len(fragment_header)
            if body_room <= 0:
                flush()
                continue
            take = min(body_room, len(text) - offset)
            current.append(fragment_header + text[offset : offset + take])
            used += separator_chars + len(fragment_header) + take
            offset += take
            if offset < len(text):
                flush()
            if not text:
                offset = 1
    flush()
    return contexts


def build_messages(
    record: dict[str, Any],
    system_prompt: str,
    max_document_chars: int | None,
    include_normalized_facts: bool = False,
    document_context: str | None = None,
) -> list[dict[str, str]]:
    metadata = json.dumps(record["meta"], ensure_ascii=False, sort_keys=True, indent=2)
    facts = ""
    if include_normalized_facts:
        facts = (
            "\n\n[정규화된 공고 사실 — 원본 메타에서만 생성]\n"
            + json.dumps(normalize_notice_facts(record["meta"]), ensure_ascii=False, indent=2)
        )
    user_prompt = (
        f"[공고 ID] {record['id']}\n\n"
        f"[나라장터 입력 메타]\n{metadata}{facts}\n\n"
        f"[문서]\n{document_context if document_context is not None else build_document_context(record, max_document_chars)}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def normalize_notice_facts(meta: dict[str, Any]) -> dict[str, Any]:
    """Expose stable notice metadata without consulting reference-data packages."""
    product_value = str(meta.get("세부품명번호목록") or "")
    return {
        "적용계약법": meta.get("적용계약법"),
        "업무구분": meta.get("업무구분"),
        "추정가격원": meta.get("입찰추정가격"),
        "배정예산원": meta.get("배정예산금액"),
        "계약방법": meta.get("계약방법"),
        "낙찰방법": meta.get("낙찰방법"),
        "세부품명번호": re.findall(r"\[(\d{10})\]", product_value),
        "세부품명원문": meta.get("세부품명번호목록"),
        "지역제한": {"여부": meta.get("지역제한여부"), "목록": meta.get("제한지역코드목록")},
        "업종제한": {"여부": meta.get("업종제한여부"), "목록": meta.get("면허업종제한목록")},
        "공동도급구성방식": meta.get("공동도급구성방식"),
        "긴급공고여부": meta.get("긴급공고여부"),
    }
