"""Baseline prompt construction without retrieval or item-specific tuning."""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from src.schema import ABSENCE_ITEMS, ITEMS

DOCUMENT_ORDER = ("공고문", "규격서", "과업지시서", "제안요청서", "예외공표서")
PRODUCT_NAME_WITH_CODE = re.compile(r"([^,\[\]]+)\[\d{10}\]")

SYSTEM_HEAD = """당신은 공공 입찰공고의 법령 위반 여부를 점검한다.
아래의 공고 자료와 나라장터 입력 메타데이터를 법령 기준과 대조하여, 지정 항목별 위반 여부와 근거 문구를 판정한다.

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

DOCUMENT_SCOPED_GUIDANCE = """

[근거 문구 규칙]
`# 공고 자료` 아래에 제시된 공고 자료 원문만 위반 근거로 사용할 수 있다.
`[공고문 앵커:...]`는 같은 공고의 배경을 알리는 보조 문맥이며 근거 문서가 아니다.
메타데이터와 참고 법령도 판정 기준일 뿐 근거 문서가 아니다.

정부계약 컴플라이언스 위반은 추측이나 위험 신호가 아니라, 해당 항목의 법적 요건을
실제로 충족하는 명시적 제한·요구·불일치여야 한다.
1. 공고 자료 원문에서 항목에 해당하는 정확한 문장을 찾는다.
2. 그 문장이 해당 v 항목의 핵심 조건을 모두 충족하는지 메타데이터·판정 카드·참고 법령으로 확인한다.
3. 조건이 하나라도 불명확하거나, 단순 키워드·일반 관행·의심에 그치면 0으로 둔다.
4. 부재탐지가 아닌 항목을 1로 둘 때는 공고 자료 원문의 변경 없는 연속 부분문자열을 근거문구로 복사한다. 복사할 수 없으면 0이다.
5. [부재탐지] 항목은 필요한 문구·조건이 없을 때만 1, 있으면 0이다. 근거문구는 null이다.
"""


def _render_card_text(prompt_text: str, *, indent: str = "") -> str:
    """Render the maintained card facts as short, scannable conditions.

    The decision-card artifact deliberately owns the wording.  This renderer
    only supplies visual structure; it must not add legal conditions.
    """
    # Cards were authored before the model-facing section name was standardized.
    # This is display-only terminology normalization, not a change to any card
    # condition or legal threshold.
    # Do not replace the preceding Korean subject particle ("이") together
    # with the noun.  For example, "실적제한이 대상 문서에" must remain
    # grammatically separated as "실적제한이 공고 자료 원문에".
    prompt_text = prompt_text.replace("대상 문서", "공고 자료 원문")
    labels = ("적용 확인", "부재탐지", "1 조건", "0 조건")
    pattern = r"(?=(?:" + "|".join(re.escape(label) for label in labels) + r"): )"
    parts = [part.strip() for part in re.split(pattern, prompt_text) if part.strip()]
    return "\n".join(f"{indent}- {part}" for part in parts)


def build_system_prompt(
    item_table: dict[str, dict[str, Any]],
    mode: str = "baseline",
    reference_text: str | None = None,
    document_scoped: bool = False,
    decision_cards: dict[str, dict[str, Any]] | None = None,
    reference_navigation: str | None = None,
    v8_composite_enabled: bool = False,
    candidate_detection: bool = False,
    active_items: tuple[str, ...] = ITEMS,
    layout: str = "plain",
) -> str:
    lines = []
    if not active_items or any(item not in ITEMS for item in active_items):
        raise ValueError("active_items must be a non-empty subset of v1..v24")
    if layout not in {"plain", "markdown", "markdown_v2"}:
        raise ValueError("layout must be plain, markdown, or markdown_v2")
    item_range = "~".join((active_items[0], active_items[-1])) if len(active_items) > 1 else active_items[0]
    for item in active_items:
        definition = item_table[item]
        absence = " [부재탐지]" if item in ABSENCE_ITEMS else ""
        note = f" (참고: {definition['비고']})" if definition.get("비고") else ""
        if layout in {"markdown", "markdown_v2"}:
            card = ""
            if decision_cards:
                prompt_text = decision_cards[item]["prompt_text"]
                card = (
                    "\n- **판정 카드**\n"
                    + _render_card_text(prompt_text, indent="  ")
                )
            lines.append(
                f"### `{item}` — {definition['항목명']}\n"
                f"- **판정 유형**: {'필요 문구의 부재를 검사' if item in ABSENCE_ITEMS else '명시적 위반 문구를 검사'}"
                + (f"\n- **항목표 비고**: {definition['비고']}" if definition.get("비고") else "")
                + card
            )
        elif mode == "structured":
            lines.append(
                f"- {item}: {definition['항목명']}{absence}"
                f"{' | 비고: ' + definition['비고'] if definition.get('비고') else ''}\n"
                f"  국가계약법 참조: {definition.get('국가계약법', '')}\n"
                f"  지방계약법 참조: {definition.get('지방계약법', '')}"
            )
        else:
            lines.append(f"- {item}: {definition['항목명']}{absence}{note}")
    guidance = STRUCTURED_GUIDANCE if mode == "structured" else GUIDED_GUIDANCE if mode == "guided" else ""
    scope_guidance = DOCUMENT_SCOPED_GUIDANCE if document_scoped else ""
    card_guidance = ""
    if decision_cards and layout == "plain":
        card_guidance = (
            ("\n\n## 항목별 상세 판정 카드\n" if layout == "markdown" else "\n\n[항목별 상세 판정 카드]\n")
            +
            "각 카드의 1 조건을 모두 만족할 때만 1이다. 카드의 0 조건 하나라도 해당하거나 "
            "확인할 수 없으면 0이다. 카드의 법령 참조는 판단 범위이고, 근거문구는 언제나 "
            "공고/첨부문서 원문에서만 인용한다.\n"
            + "\n\n".join(
                (f"### {item} | {decision_cards[item]['item_name']}\n" if layout == "markdown" else f"[{item} | {decision_cards[item]['item_name']}]\n")
                + _render_card_text(decision_cards[item]["prompt_text"])
                + (
                    "\n병합관찰 선택지: "
                    + ", ".join(decision_cards[item]["merge_contract"]["states"])
                    + "\n병합관찰 설명: "
                    + decision_cards[item]["merge_contract"]["instruction"]
                    if v8_composite_enabled and item == "v8" and decision_cards[item].get("merge_contract")
                    else ""
                )
                for item in active_items
            )
        )
    merge_guidance = ""
    if v8_composite_enabled:
        merge_guidance = (
            "\n\n[v8 문서 간 결합 관찰]\n"
            "v8 판정과 별도로 v8병합관찰에 상태 하나와 관찰근거문구를 출력한다. "
            "실적·지역·둘다 상태의 관찰근거문구는 반드시 공고문 원문의 변경 없는 연속 부분문자열이어야 한다. "
            "공고문 원문 밖 정보, 공고문 앵커, metadata, 참고자료만으로 상태를 정하지 않는다. "
            "판단할 수 없으면 상태는 검토, 관찰근거문구는 null이다."
        )
    # Profile names, chunk keys, paths, and item-to-chunk routing are audit
    # metadata.  They stay in the manifest/output, never in the model message.
    # Keep the parameter for backward-compatible callers while deliberately
    # omitting it from the prompt.
    navigation_guidance = ""
    candidate_guidance = """

[후보 탐지 모드]
출력의 1은 법적 최종 위반 확정이 아니라, 공고문 원문에 해당 항목을 재검증할 가치가 있는
명시 문구가 있다는 뜻이다. 공고문 원문의 제한·요구·수치·불일치 문구가 항목과 관련되면, 법적 예외나
금액 조건이 아직 불확실해도 1과 그 문구를 출력한다. 문구가 전혀 없으면 0이다. 부재탐지 항목은
이 후보 탐지에서 항상 0으로 출력한다.
""" if candidate_detection else ""
    head = SYSTEM_HEAD.replace("아래 24개 항목 각각", f"아래 지정 항목({item_range}) 각각")
    head = head.replace("1. v1~v24를 모두 출력한다.", f"1. {', '.join(active_items)}을 모두 출력한다.")
    tail = SYSTEM_TAIL.replace("v1~v24", ", ".join(active_items))
    if layout in {"markdown", "markdown_v2"}:
        head = "# 역할\n" + head.replace("\n\n규칙:", "\n\n# 기본 규칙").replace("\n\n판정 항목:", "\n\n# 판정 항목")
        if decision_cards:
            head = head.replace(
                "# 판정 항목",
                "# 판정 항목\n각 항목은 아래 카드의 **적용 확인**, **1 조건**, **0 조건**을 순서대로 확인한다. "
                "1 조건을 모두 충족할 때만 1이고, 0 조건 또는 불확실성이 있으면 0이다.",
            )
        scope_guidance = scope_guidance.replace("[근거 문구 규칙]", "# 근거 문구 규칙")
        merge_guidance = merge_guidance.replace("[v8 문서 간 결합 관찰]", "# v8 문서 간 결합 관찰")
        candidate_guidance = candidate_guidance.replace("[후보 탐지 모드]", "# 후보 탐지 모드")
        if guidance:
            guidance = "\n\n# 판정 절차\n" + guidance.strip()
        if layout == "markdown_v2":
            workflow = """

# 판정 순서
1. **공고 자료 확인**: `# 공고 자료` 아래의 공고 자료 원문에서 해당 문구를 찾는다.
2. **v별 카드 적용**: 각 v의 적용 확인 → 1 조건 → 0 조건 순서로 확인한다.
3. **근거 확정**: 부재탐지가 아닌 항목을 1로 둘 때는 공고 자료 원문의 변경 없는 연속 문구를 복사한다. 복사할 수 없으면 0이다.
4. **출력**: 모든 v를 판단한 뒤 아래 JSON 객체 하나만 출력한다.
"""
            scope_guidance = workflow + scope_guidance
            skeleton = ",\n".join(
                f'  "{item}": {{"위반여부": 0, "근거문구": null}}'
                for item in active_items
            )
            tail = (
                "# 출력 형식\n"
                "설명·분석·Markdown 없이 아래 키만 가진 JSON 객체 하나를 출력한다. "
                "각 `위반여부`는 0 또는 1이며, 0이면 `근거문구`는 null이다.\n"
                "```json\n{\n" + skeleton + "\n}\n```"
            )
        else:
            tail = "# 출력 형식\n" + tail
    reference_section = ""
    if reference_text:
        reference_section = (
            ("\n\n# 참고 법령·고시 — 판정 기준\n" if layout in {"markdown", "markdown_v2"} else "\n\n[참고 법령·고시 — 판정 기준]\n")
            + "아래는 위반 여부를 판정할 때 적용할 기준이다. 법령 원문 또는 대회 제공 법령 기반 요약의 조건과 공고 자료를 대조해 판정한다. 참고자료는 공고문이 아니며 위반 근거문구도 아니다. "
            "위반여부를 1로 할 때의 근거문구는 반드시 공고 자료 원문에서만 그대로 복사한다.\n"
            + reference_text
        )
    prompt = f"{head}\n" + "\n".join(lines) + f"\n{guidance}{scope_guidance}{card_guidance}{merge_guidance}{navigation_guidance}{candidate_guidance}"
    if layout == "markdown_v2":
        prompt += reference_section + "\n\n" + tail
    else:
        prompt += "\n" + tail + reference_section
    return prompt


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
    competition_product_context: str | None = None,
    v24_comparison_context: str | None = None,
    markdown_sections: bool = False,
) -> list[dict[str, str]]:
    metadata = json.dumps(record["meta"], ensure_ascii=False, sort_keys=True, indent=2)
    facts = ""
    if include_normalized_facts:
        facts = (
            "\n\n[정규화된 공고 사실 — 원본 메타에서만 생성]\n"
            + json.dumps(normalize_notice_facts(record["meta"]), ensure_ascii=False, indent=2)
        )
    if competition_product_context is not None:
        facts += (
            "\n\n[대회 제공 경쟁제품 고시 조회 결과]\n"
            + competition_product_context
        )
    if v24_comparison_context is not None:
        facts += "\n\n[v24 메타데이터 대조 체크리스트]\n" + v24_comparison_context
    document_text = document_context if document_context is not None else build_document_context(record, max_document_chars)
    if markdown_sections:
        fact_section = ""
        if facts:
            fact_section = "\n\n# 공고 보조 정보\n" + facts.strip()
        user_prompt = (
            "# 나라장터 입력 메타데이터\n"
            "아래 값은 적용 법령·금액·계약방식 등을 공고문과 대조할 때 쓰는 입력값이다. 단독으로 위반 근거문구가 될 수 없다.\n"
            "```json\n" + metadata + "\n```"
            + fact_section
            + "\n\n# 공고 자료\n"
            "아래에 제시된 공고 자료 원문만 부재탐지가 아닌 항목의 근거문구로 인용할 수 있다.\n"
            + document_text
            + "\n\n# 출력\n"
            "지정된 모든 v를 판단한다. 1이면 공고 자료 원문의 근거문구를 넣고, 0이면 null을 넣는다. 설명 없이 지정된 키만 가진 JSON 객체 하나를 출력한다."
        )
    else:
        user_prompt = (
            f"[나라장터 입력 메타데이터]\n{metadata}{facts}\n\n"
            f"[문서]\n{document_text}\n\n"
            "[출력]\n참고 법령·판정 카드·메타데이터와 공고 자료를 대조하여 지정된 모든 v를 판정한다. "
            "1이면 공고 자료 원문의 근거문구를 넣고, 0이면 null을 넣는다. 설명 없이 JSON 객체 하나만 출력한다."
        )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def format_competition_product_context(
    record: dict[str, Any], fact: dict[str, Any], active_items: tuple[str, ...] = ITEMS
) -> str:
    """Translate exact CSV lookup facts into concise, model-facing Korean.

    The raw fact keeps codes and source IDs for auditability. This layer does
    not expose implementation state names or identifiers to the model.
    """
    status = fact["status"]
    if status == "matched":
        names = ", ".join(product["세부품명"] for product in fact["matched_products"])
        finding = (
            "이 공고에서 확인된 세부품명이 대회 제공 중소기업자간 경쟁제품 고시에 "
            f"등재되어 있습니다: {names}."
        )
    elif status == "not_matched":
        raw_value = str(record["meta"].get("세부품명번호목록") or "")
        names = [name.strip() for name in PRODUCT_NAME_WITH_CODE.findall(raw_value)]
        description = f"(기재 세부품명: {', '.join(names)})" if names else ""
        finding = (
            "나라장터 메타에 세부품명이 기재되어 있으나, 대회 제공 경쟁제품 고시에서 "
            f"정확히 일치하는 경쟁제품을 확인하지 못했습니다. {description}"
        ).strip()
    elif status == "unknown":
        finding = (
            "나라장터 메타와 공고 문서에서 경쟁제품 고시와 정확히 대조할 수 있는 "
            "세부품명 식별정보를 확인하지 못했습니다. 이는 비경쟁제품 또는 비적용이라는 "
            "판정이 아니라, 이 조회만으로 품목 분류를 확정할 수 없다는 뜻입니다."
        )
    else:
        raise ValueError(f"unknown competition product status: {status}")
    guidance: list[str] = []
    competition_items = [item for item in ("v10", "v11", "v13") if item in active_items]
    general_items = [item for item in ("v16", "v18") if item in active_items]
    if competition_items:
        guidance.append(
            f"이 조회 결과는 {'·'.join(competition_items)}의 경쟁제품 적용대상 확인에만 사용합니다. "
            "정확히 매칭되면 경쟁제품 근거로 사용하고, 정확히 미매칭되면 그 사실을 사용합니다. "
            "조회 불가만으로 0 또는 1을 정하지 말고, 공고의 물품·참가자격·요구 문구와 금액을 계속 대조하십시오. "
            "매칭된 경우에도 해당 항목의 다른 조건을 모두 확인해야 합니다."
        )
    if general_items:
        guidance.append(
            f"{'·'.join(general_items)} 판단에는 경쟁제품으로 정확히 확인된 품목을 일반제품으로 사용하지 마십시오. "
            "조회 불가는 일반제품 배제 근거가 아니므로, 공고의 물품·금액·제한 또는 예외 문구를 계속 확인하십시오."
        )
    return f"{finding}\n" + " ".join(guidance)


def format_v24_comparison_context(record: dict[str, Any]) -> str:
    """Render the only metadata fields that v24 may compare to source text.

    This is a deterministic restatement of organizer metadata, not a classifier.
    It keeps the model from treating any ordinary eligibility restriction as a
    notice-to-metadata mismatch.
    """
    meta = record["meta"]
    fields = {
        "예산·가격": {
            "배정예산금액": meta.get("배정예산금액"),
            "입찰추정가격": meta.get("입찰추정가격"),
        },
        "계약방법": {"계약방법": meta.get("계약방법"), "낙찰방법": meta.get("낙찰방법")},
        "지역제한": {"지역제한여부": meta.get("지역제한여부"), "제한지역코드목록": meta.get("제한지역코드목록")},
        "업종제한": {"업종제한여부": meta.get("업종제한여부"), "면허업종제한목록": meta.get("면허업종제한목록")},
    }
    return (
        "다음은 대조 가능한 나라장터 입력값이다. 공고 자료에 같은 의미의 값이 명시된 경우에만 "
        "한 쌍씩 비교한다. 공고의 참가자격·제한 문구가 존재한다는 사실만으로 불일치가 되지 않는다. "
        "두 값이 실제로 양립 불가능할 때만 v24=1이며, 값이 없거나 대응이 불명확하면 v24=0.\n"
        + json.dumps(fields, ensure_ascii=False, sort_keys=True)
    )


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
