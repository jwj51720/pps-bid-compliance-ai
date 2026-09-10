"""Baseline prompt construction without retrieval or item-specific tuning."""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from src.schema import (
    ABSENCE_ITEMS,
    FACT_INVENTORY_CATEGORIES,
    FACT_INVENTORY_CATEGORIES_V2,
    ITEMS,
    PROCEDURE_FACT_FIELDS,
)

DOCUMENT_ORDER = ("공고문", "규격서", "과업지시서", "제안요청서", "예외공표서")
PRODUCT_NAME_WITH_CODE = re.compile(r"([^,\[\]]+)\[\d{10}\]")
OFFICIAL_BASELINE_META_FIELDS = (
    "적용계약법", "업무구분", "계약방법", "낙찰방법", "낙찰하한율",
    "배정예산금액", "입찰추정가격", "소관구분", "공동도급구성방식", "정보화사업여부",
    "세부품명번호목록", "제한지역코드목록", "지역제한여부", "면허업종제한목록", "업종제한여부",
    "조항호내용", "공고게시일자", "개찰예정일자", "긴급공고여부", "입찰방법", "조달방식",
)

OFFICIAL_BASELINE_SYSTEM_HEAD = """당신은 공공 입찰공고의 법령 위반 여부를 점검한다.
공고문과 첨부 문서, 그리고 나라장터 입력 메타를 함께 읽고 아래 24개 항목 각각에 대해
위반 여부(1/0)와 근거 문구를 판정한다.

지켜야 할 것
1. 24개 항목 전부에 답한다. 판단이 어려운 항목도 비워 두지 말고 0으로 낸다.
2. 근거 문구는 반드시 **주어진 문서에 그대로 있는 문장**을 옮긴다. 요약하거나 고쳐 쓰지 않는다.
   원문에 없는 문구는 근거로 인정되지 않는다. 500자를 넘기지 않는다.
3. 아래 '근거 없음' 표시가 붙은 항목은 **있어야 할 문구가 없는 것**이 위반이다.
   인용할 원문이 존재하지 않으므로 근거 문구를 null로 둔다.

판정할 24개 항목"""

OFFICIAL_BASELINE_SYSTEM_TAIL = """
출력은 JSON 하나로만 낸다. 키는 v1~v24, 각 값은 {\"위반여부\": 0 또는 1, \"근거문구\": 문자열 또는 null}이다.
설명이나 머리말을 덧붙이지 않는다."""

OFFICIAL_BASELINE_LABELS_ONLY_HEAD = """당신은 공공 입찰공고의 법령 위반 여부를 점검한다.
공고문과 첨부 문서, 그리고 나라장터 입력 메타를 함께 읽고 아래 24개 항목 각각에 대해
위반 여부(1/0)를 판정한다.

지켜야 할 것
1. 24개 항목 전부에 답한다. 판단이 어려운 항목도 비워 두지 말고 0으로 낸다.
2. 항목명을 단순 키워드로 판단하지 말고, 공고 자료와 나라장터 입력 메타를 함께 대조한다.
3. 아래 '근거 없음' 표시가 붙은 항목은 **있어야 할 문구가 없는 것**이 위반이다.

판정할 24개 항목"""

OFFICIAL_BASELINE_LABELS_ONLY_TAIL = """
출력은 JSON 하나로만 낸다. 키는 v1~v24이고 각 값은 0 또는 1이다.
설명이나 머리말을 덧붙이지 않는다."""

TRIAGE_SYSTEM_HEAD = """당신은 공공 입찰공고의 법령 위반 사전검토를 담당한다.
아래 공고 자료와 나라장터 입력 메타를 읽고, 각 항목을 최종 위반 판정 전에
어떤 검토 경로로 보낼지 분류한다. 이것은 최종 0/1 판정도, 근거문구 추출도 아니다.

상태의 뜻
1. `명시근거`: 공고 자료에 실제 제한·요구·불일치로 볼 만한 문구가 있어 엄격한 최종 판정이 필요하다.
2. `부재검토`: 필요한 조건의 부재를 전체적으로 확인해야 하므로 엄격한 최종 판정이 필요하다.
3. `불명확`: 관련 문구나 적용 전제가 있어 엄격한 최종 판정이 필요하다.
4. `해당없음`: 현재 자료에서 관련 사실을 확인하지 못했다. 이는 최종 위반 아님이나 법적 결론이 아니다.

`[근거 없음]` 표시 항목은 자료가 짧거나 적용 여부가 불명확해도 `해당없음`으로 끝내지 말고
`부재검토`로 둔다. 항목명을 키워드만으로 넓혀 해석하지 말고, 공고 밖 사실을 보충하지 않는다.

사전검토할 항목
"""

TRIAGE_SYSTEM_TAIL = """
출력은 JSON 객체 하나로만 낸다. 키는 지정된 v이고 값은 `명시근거`, `부재검토`,
`불명확`, `해당없음` 중 하나다. 설명, 위반여부, 근거문구를 덧붙이지 않는다."""

LOCATOR_SYSTEM_HEAD = """당신은 공공 입찰공고 원문의 위치 탐색을 담당한다.
아래 공고 자료와 나라장터 입력 메타를 읽고, 지정 항목과 관련된 실제 원문 문구가
보이면 그 문구를 변경 없이 찾아낸다. 이것은 위반 여부 판정도, 법령 해석도,
근거문구 확정도 아니다.

각 항목에 대해 실제 제한·요구·불일치로 연결될 수 있는 공고 자료 원문의 연속
부분문자열 하나만 반환한다. 관련 문구가 없거나 확실히 그대로 복사할 수 없으면 null을
반환한다. null은 위반이 아니라는 뜻이 아니다. 메타데이터·판정 카드·공고 밖 사실을
문구로 반환하지 않는다.

탐색할 항목
"""

LOCATOR_SYSTEM_TAIL = """
출력은 JSON 객체 하나로만 낸다. 키는 지정된 v이고 값은 원문 문자열 또는 null이다.
설명, 위반여부, 근거문구라는 결론을 덧붙이지 않는다."""

FACT_INVENTORY_SYSTEM = """당신은 공공 입찰공고 원문에서 사실을 빠짐없이 정리하는 담당자다.
이 단계에서는 법령 위반 여부, v 항목의 0/1, 허용 여부, 예외 적용 여부를 판단하지 않는다.
아래 공고 자료 원문만 읽고, 실제 참가자격·제한·요구·예외·금액·날짜·비교값이 담긴
원문 문구를 해당 사실 유형별로 최대 3개씩 변경 없이 복사한다.

반환 대상은 다음과 같다.
- 참가자격_실적_지역: 기관·면허·실적·지역의 실제 참가조건
- 제품_기업_직접생산: 세부품명, 직접생산, 중소/소기업 제한 또는 예외
- 규격_모델_기술요구: 특정 제조사·모델·호환/동등품·기술 요구
- 제출서류_확약서: 제안·입찰 전/후 제출해야 하는 확약서·서류와 시점
- 계약방식_공동계약: 계약·낙찰 방식, 공동수급 방식, 구성원 지분 조건
- 일정_설명회: 공고·설명회·제안서/입찰 마감의 실제 날짜와 참석 조건
- 금액_메타대조: 예산·추정가격·기초금액과 문서에 명시된 계약/지역/업종 값

관련 사실이 없으면 빈 배열로 둔다. 요약, 해석, 메타데이터의 값, 법령 설명, 위반 판단을
쓰지 않는다. 문구는 반드시 아래 공고 자료 원문에 있는 연속 문자열이어야 한다."""


def build_fact_inventory_system_prompt(
    max_excerpts: int = 3,
    categories: tuple[str, ...] = FACT_INVENTORY_CATEGORIES,
) -> str:
    """Return the source-only fact contract with a declared category cap."""
    if max_excerpts not in {3, 4}:
        raise ValueError("fact inventory max_excerpts must be 3 or 4")
    if categories not in {FACT_INVENTORY_CATEGORIES, FACT_INVENTORY_CATEGORIES_V2}:
        raise ValueError("fact inventory categories must be a supported version")
    prompt = FACT_INVENTORY_SYSTEM.replace("최대 3개씩", f"최대 {max_excerpts}개씩")
    if categories == FACT_INVENTORY_CATEGORIES_V2:
        prompt = prompt.replace(
            "\n\n관련 사실이 없으면",
            "\n- 예외_허용_적용범위: 예외·면제·허용·대체 가능·동등 이상·불참 허용처럼 "
            "제한·요구의 적용 범위를 실제로 바꾸는 문구\n\n관련 사실이 없으면",
        )
    return prompt


def append_fact_inventory(
    messages: list[dict[str, str]], inventory: dict[str, tuple[tuple[str, str], ...]],
    position: str = "after_source",
    categories: tuple[str, ...] = FACT_INVENTORY_CATEGORIES,
) -> list[dict[str, str]]:
    """Attach source-labelled factual excerpts as non-final navigation material."""
    if categories not in {FACT_INVENTORY_CATEGORIES, FACT_INVENTORY_CATEGORIES_V2}:
        raise ValueError("fact inventory categories must be a supported version")
    if set(inventory) != set(categories):
        raise ValueError("fact inventory must provide every factual category")
    lines = [
        "[전체 공고 자료에서 수집한 원문 사실 — 최종 판정 아님]",
        "아래는 모든 공고 자료를 먼저 읽어 변경 없이 복사한 사실 후보이다. 누락·중복이 있을 수 있다.",
        "각 후보를 0/1 또는 법령 해석으로 자동 변환하지 말고, 앞의 판정 카드·메타·공고 자료와 대조해 최종 판단한다.",
        "후보가 없다는 것은 위반 없음이 아니다. 근거문구가 필요하면 아래 후보 또는 앞의 공고 자료에 있는 원문만 그대로 사용한다.",
        "",
    ]
    for category in categories:
        lines.append(f"- {category}:")
        values = inventory[category]
        if not values:
            lines.append("  - 수집된 원문 후보 없음")
        else:
            for doc_id, excerpt in values:
                lines.append(f"  - [{doc_id}] {excerpt}")
    navigation = "\n".join(lines)
    if position == "after_source":
        return [*messages, {"role": "user", "content": navigation}]
    if position != "before_source":
        raise ValueError("fact inventory position must be after_source or before_source")
    if not messages or messages[-1]["role"] != "user":
        raise ValueError("before-source inventory requires a final user message")
    prefix, marker, source = messages[-1]["content"].partition("[공고 자료 원문]\n")
    if not marker:
        raise ValueError("before-source inventory requires an organizer source section")
    return [
        *messages[:-1],
        {"role": "user", "content": f"{prefix.rstrip()}\n\n{navigation}\n\n{marker}{source}"},
    ]


TIMELINE_FACT_SYSTEM = """당신은 공공 입찰공고 원문에서 일정 사실만 정리한다.
위반 여부, v 항목의 0/1, 최소 기간 계산, 허용 여부를 판단하지 않는다.
아래 원문에 실제로 있는 연속 문구만 역할별로 최대 2개씩 그대로 복사한다.
- 공고일: 공고 게시·공고일 문구
- 현장설명회일시: 현장·사업설명회 일시 문구
- 제안서_접수마감: 제안서 제출·접수 마감 일시 문구
- 가격입찰_마감: 가격입찰서 제출 마감 일시 문구
- 긴급_재공고_표시: 긴급공고 또는 재공고 문구
관련 문구가 없으면 빈 배열이다. 메타데이터, 법령 설명, 요약, 위반 판단은 쓰지 않는다."""


def build_timeline_fact_system_prompt() -> str:
    """Return the fixed source-only v23 role-extraction contract."""
    return TIMELINE_FACT_SYSTEM


def build_source_only_fact_messages(system_prompt: str, source: str) -> list[dict[str, str]]:
    """Make a source-only navigation message with no metadata or card facts."""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"[공고 자료 원문]\n{source}"},
    ]


def append_timeline_fact_navigation(messages: list[dict[str, str]], facts: dict[str, tuple[tuple[str, str], ...]]) -> list[dict[str, str]]:
    """Append source-grounded date roles without any label implication."""
    lines = ["[일정 원문 사실 안내 — 최종 판정 아님]",
             "후보가 없다고 0이 아니며, 날짜 역할·기간·위반 여부는 공고 원문과 판정 카드를 다시 읽어 판단한다."]
    for role, values in facts.items():
        text = " | ".join(f"[{doc_id}] {excerpt}" for doc_id, excerpt in values)
        lines.append(f"- {role}: {text or '후보없음 (이는 0이 아님)'}")
    if not messages or messages[-1]["role"] != "user":
        raise ValueError("timeline navigation requires a final user message")
    return [
        *messages[:-1],
        {"role": "user", "content": messages[-1]["content"] + "\n\n" + "\n".join(lines)},
    ]


PROCEDURE_FACT_SYSTEM = """당신은 공공 입찰공고 원문에서 절차·사실 관계를 탐색한다.
이 단계는 법령 위반 여부, v 항목의 0/1, 허용 여부, 예외 적용 여부, 날짜·금액 계산,
metadata 값 추정, 근거문구 확정을 하지 않는다. 아래 공고 자료 원문에서만 각 관계의
endpoint가 함께 이해되는 변경 없는 연속 문자열을 최대 2개씩 복사한다.

- 참가자격_관계: 같은 참가자격 조항의 대상·실적·지역 제한 및 그 보충/예외
- 제품자격_관계: 제품·직접생산·기업 제한과 실제 참가자격 범위
- 규격요구_관계: 제조사·모델·기술 요구와 동등품/필요성 보충
- 제출서류_관계: 확약서·서류와 제출 시점/목적
- 공동계약_관계: 공동계약 방식·구성원 역할·최소 지분
- 일정참가_관계: 일정 역할·참석 및 참가자격 결과
- 공고메타_대조값: 예산·계약방식·지역·업종 중 원문에 명시된 값 자체

한 문자열 안에 관계 endpoint가 함께 있으면 그것을 우선한다. 서로 떨어져 있으면 같은
관계를 이해하는 데 필요한 원문 문자열만 source order로 최대 두 개 반환한다. 관련 원문이
없으면 빈 배열이다. 요약·해석·법령명·metadata·라벨·계산값을 쓰지 않는다."""


def build_procedure_fact_system_prompt() -> str:
    """Return EXP181's fixed source-only relation-navigation contract."""
    return PROCEDURE_FACT_SYSTEM


def append_procedure_fact_navigation(
    messages: list[dict[str, str]],
    facts: dict[str, tuple[tuple[str, str], ...]],
) -> list[dict[str, str]]:
    """Append an advisory source-procedure ledger to a final V/E message."""
    if set(facts) != set(PROCEDURE_FACT_FIELDS):
        raise ValueError("procedure navigation must provide every relation field")
    lines = [
        "[공고 절차 원문 관계 안내 — 최종 판정 아님]",
        "아래는 원문에서 먼저 수집한 관계 후보이다. 누락·중복·역할 오류가 있을 수 있다.",
        "후보를 0/1·법률판단·metadata 사실로 자동 변환하지 말고, 판정 카드·friendly metadata·원문 전체와 다시 대조한다.",
        "후보가 없다는 것은 위반 없음이 아니다. 근거문구는 아래 후보 또는 공고 원문에 있는 변경 없는 문자열만 사용한다.",
    ]
    for field in PROCEDURE_FACT_FIELDS:
        values = facts[field]
        lines.append(f"- {field}:")
        lines.extend(
            f"  - [{doc_id}] {excerpt}" for doc_id, excerpt in values
        ) if values else lines.append("  - 수집된 원문 후보 없음")
    if not messages or messages[-1]["role"] != "user":
        raise ValueError("procedure navigation requires a final user message")
    return [
        *messages,
        {"role": "user", "content": "\n".join(lines)},
    ]

SYSTEM_HEAD = """당신은 공공 입찰공고의 법령 위반 여부를 점검한다.
아래의 공고 자료와 나라장터 입력 메타데이터를 법령 기준과 대조하여, 지정 항목별 위반 여부와 근거 문구를 판정한다.

규칙:
1. v1~v24를 모두 출력한다. 판단이 어려우면 위반여부를 0으로 둔다.
2. 근거문구는 주어진 문서에 그대로 존재하는 연속 부분문자열이어야 한다. 요약하거나 수정하지 말고 500자를 넘기지 않는다.
3. 위반여부가 0이면 근거문구는 null이다.
4. [부재탐지] 항목은 필요한 문구가 없는 경우가 위반이므로 근거문구를 항상 null로 둔다.

판정 항목:"""

LABELS_ONLY_SYSTEM_HEAD = """당신은 공공 입찰공고의 법령 위반 여부를 점검한다.
아래의 공고 자료와 나라장터 입력 메타데이터를 법령 기준과 대조하여, 지정 항목별 위반 여부를 판정한다.

규칙:
1. 지정된 모든 v를 출력한다. 판단이 어려우면 위반여부를 0으로 둔다.
2. 항목명을 단순 키워드 탐지로 판단하지 말고, 공고 자료 원문에서 해당 항목의 법적 요건을 모두 충족하는 명시적 제한·요구·불일치를 확인한 경우에만 1로 둔다.
3. 판단할 때 공고 자료의 실제 내용과 나라장터 입력 메타의 적용계약법, 업무구분, 금액, 계약·낙찰방법, 지역·업종·공동계약 정보를 함께 검토한다.
4. [부재탐지] 항목은 필요한 문구와 조건이 공고 자료 전체에 없을 때만 1이고, 있으면 0이다.
5. 서로 비슷한 항목도 각각의 항목명·공식 참조·비고에 맞춰 독립적으로 판단한다. 문구 하나가 여러 항목의 위반을 자동으로 뜻하지는 않는다.
6. v24는 문서의 명시적 내용과 나라장터 입력 메타의 대응 필드를 비교해 실제 불일치가 확인될 때만 1로 판단한다.

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

# A role directive is deliberately narrow: it reinforces careful application
# of the supplied cards, but never creates new legal facts or changes a
# card's 0/1 condition.  Keep it separate from ``mode`` so experiments can
# isolate professional-duty wording from reasoning-workflow wording.
COMPLIANCE_EXPERT_DUTY_V1 = """

[심사 책임]
당신은 공공계약 법령 컴플라이언스 사전심사를 담당하는 법률 전문가다. 이 판정은
감사·분쟁 검토를 견뎌야 하는 심사기록이므로, 각 항목을 독립된 법적 쟁점으로
다룬다. 항목별 판단 카드를 빠뜨리지 말고 적용 전제, 1 조건, 0 조건을 공고 자료
원문과 나라장터 입력 메타데이터에 하나씩 대조한 뒤 판단한다.

카드의 조건을 모두 확인하지 않은 채 위험 신호·키워드만으로 1을 정하는 것과,
실제 제한·요구·불일치를 놓치는 것은 모두 허용되지 않는다. 공고 밖 사실이나
제공되지 않은 법령 내용을 보충하지 않는다. 카드의 0 조건이 적용되거나 필수
사실을 확인할 수 없으면 0으로 판단한다.
"""

# This is deliberately a process-only directive.  It must not add legal
# thresholds, item-specific facts, or a different evidence contract: those
# belong to the organizer item table or a separately versioned card policy.
# Keeping the directive short also lets EXP127 isolate reading order from the
# large card/context changes in earlier experiments.
SOURCE_FIRST_WORKFLOW_V1 = """

[판정 순서]
각 항목을 답하기 전에 다음 순서로 조용히 확인한다.
1. 공고 자료 원문에서 실제 제한·요구·불일치 또는 필요한 문구의 부재를 찾는다.
2. 나라장터 입력 메타는 그 문구의 적용 조건과 같은 항목의 값인지 대조하는 데만 사용한다.
3. 한 문구를 비슷한 여러 항목의 위반으로 넓혀 해석하지 말고, 각 항목을 독립적으로 판단한다.
4. 확인되지 않은 사실·문서 밖 사유는 보충하지 않는다. 판단이 불명확하면 0으로 둔다.
"""

SYSTEM_TAIL = """출력은 JSON 객체 하나로만 작성한다. 키는 v1~v24이고 값은
{\"위반여부\": 0 또는 1, \"근거문구\": 문자열 또는 null} 형식이다. 설명이나 머리말을 추가하지 않는다."""

LABELS_ONLY_SYSTEM_TAIL = """출력은 JSON 객체 하나로만 작성한다. 키는 지정된 v이고 값은 각각 0 또는 1이다. 설명이나 머리말을 추가하지 않는다."""

ANCHOR_SYSTEM_HEAD = """당신은 공공 입찰공고의 법령 위반 여부를 점검한다.
아래의 공고 자료와 나라장터 입력 메타데이터를 법령 기준과 대조하여, 지정 항목별 위반 여부와 판단어구를 판정한다.

규칙:
1. 지정된 모든 v를 출력한다. 판단이 어려우면 위반여부를 0으로 둔다.
2. 판단어구는 주어진 공고 자료 원문에 그대로 존재하는 연속 부분문자열이어야 한다. 요약하거나 수정하지 말고 12~120자로 작성한다.
3. 위반여부가 0이면 판단어구는 null이다.
4. [부재탐지] 항목은 필요한 문구가 없는 경우가 위반이므로 판단어구를 항상 null로 둔다.

판정 항목:"""

ANCHOR_SYSTEM_TAIL = """출력은 JSON 객체 하나로만 작성한다. 키는 지정된 v이고 값은
{\"위반여부\": 0 또는 1, \"판단어구\": 문자열 또는 null} 형식이다. 설명이나 머리말을 추가하지 않는다."""

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

LABELS_ONLY_DOCUMENT_GUIDANCE = """

[원문 확인 규칙]
`# 공고 자료` 아래에 제시된 공고 자료 원문만 실제 제한·요구·불일치 및 필요한 문구의 부재를 확인하는 대상이다.
`[공고문 앵커:...]`는 같은 공고의 배경을 알리는 보조 문맥이다. 메타데이터와 참고 법령은 적용 조건을 판단하는 기준이며, 이들만으로 1을 정하지 않는다.

정부계약 컴플라이언스 위반은 추측이나 위험 신호가 아니라, 해당 항목의 법적 요건을
실제로 충족하는 명시적 제한·요구·불일치여야 한다.
1. 공고 자료 원문에서 항목과 관련된 실제 문장을 찾는다.
2. 그 문장이 해당 v 항목의 핵심 조건을 모두 충족하는지 메타데이터·판정 카드·참고 법령으로 확인한다.
3. 조건이 하나라도 불명확하거나, 단순 키워드·일반 관행·의심에 그치면 0으로 둔다.
4. 부재탐지가 아닌 항목은 공고 자료 원문에 해당 법적 조건을 뒷받침하는 실제 연속 문구가 있을 때만 1로 둔다.
5. [부재탐지] 항목은 필요한 문구·조건이 없을 때만 1, 있으면 0이다.
"""


def _render_card_text(
    prompt_text: str, *, indent: str = "", output_mode: str = "labels_and_evidence"
) -> str:
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
    if output_mode == "labels_only":
        prompt_text = re.sub(r"\s*1이면 근거문구는[^.]*[.]", "", prompt_text)
    elif output_mode == "labels_and_anchor":
        prompt_text = re.sub(r"1이면 근거문구는([^.]*)[.]", r"1이면 판단어구는\1.", prompt_text)
    labels = ("적용 확인", "부재탐지", "1 조건", "0 조건")
    pattern = r"(?=(?:" + "|".join(re.escape(label) for label in labels) + r"): )"
    parts = [part.strip() for part in re.split(pattern, prompt_text) if part.strip()]
    return "\n".join(f"{indent}- {part}" for part in parts)


def build_triage_system_prompt(
    item_table: dict[str, dict[str, Any]],
    decision_cards: dict[str, dict[str, Any]] | None,
    active_items: tuple[str, ...] = ITEMS,
) -> str:
    """Build B-stage routing instructions without a final-label contract."""
    if not active_items or any(item not in item_table for item in active_items):
        raise ValueError("triage prompt requires known active items")
    lines = []
    for item in active_items:
        definition = item_table[item]
        tag = "  [근거 없음]" if definition.get("부재탐지") else ""
        note = f" ({definition['비고']})" if definition.get("비고") else ""
        card = (
            "\n  판정 카드: " + decision_cards[item]["prompt_text"]
            if decision_cards else ""
        )
        lines.append(f"- {item}: {definition['항목명']}{note}{tag}{card}")
    return TRIAGE_SYSTEM_HEAD + "\n".join(lines) + TRIAGE_SYSTEM_TAIL


def build_locator_system_prompt(
    item_table: dict[str, dict[str, Any]],
    decision_cards: dict[str, dict[str, Any]] | None,
    active_items: tuple[str, ...],
    locator_policy: str = "strict_v1",
) -> str:
    """Build a non-final locator instruction for non-absence item snippets."""
    if not active_items or any(item not in item_table or item in ABSENCE_ITEMS for item in active_items):
        raise ValueError("locator prompt requires known non-absence active items")
    if locator_policy not in {"strict_v1", "broad_candidate_v1"}:
        raise ValueError("unsupported locator policy")
    broad_guidance = ""
    if locator_policy == "broad_candidate_v1":
        broad_guidance = (
            "\n[넓은 후보 탐색]\n"
            "여기서는 항목의 1 조건을 충족하는지, 예외가 있는지, 위반인지 판단하지 않는다. "
            "해당 항목과 관계될 수 있는 실제 제한·요구·금액·날짜·기관·지역·모델·확약서·"
            "메타 대조 대상 문구를 넓게 하나 찾는다. 나중 최종 판단에서 0이 될 문구도 반환한다.\n"
        )
    lines = []
    for item in active_items:
        definition = item_table[item]
        note = f" ({definition['비고']})" if definition.get("비고") else ""
        card = (
            "\n  판정 카드: " + decision_cards[item]["prompt_text"]
            if decision_cards else ""
        )
        lines.append(f"- {item}: {definition['항목명']}{note}{card}")
    return LOCATOR_SYSTEM_HEAD + broad_guidance + "\n".join(lines) + LOCATOR_SYSTEM_TAIL


def append_locator_navigation(
    messages: list[dict[str, str]], snippets: dict[str, str], active_items: tuple[str, ...]
) -> list[dict[str, str]]:
    """Append untrusted navigation cues without converting them into evidence."""
    if set(snippets) != set(active_items):
        raise ValueError("locator navigation must cover exactly the locator item set")
    lines = [
        "[원문 위치 탐색 보조 결과]",
        "아래 결과는 별도 탐색 단계가 찾은 후보일 뿐이다. 누락·오류가 있을 수 있으며, "
        "그 자체로 위반·무위반 또는 근거문구가 아니다.",
        "반드시 앞의 공고 자료 원문, 나라장터 입력 메타, 항목별 판정 카드를 다시 대조해 "
        "v1~v24의 최종 V/E를 판정한다. `찾지 못함`을 0으로 해석하지 않는다.",
        "",
    ]
    for item in active_items:
        value = snippets[item]
        rendered = f"`{value}`" if value else "찾지 못함"
        lines.append(f"- {item}: {rendered}")
    return [*messages, {"role": "user", "content": "\n".join(lines)}]


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
    profile: str = "default",
    role_directive: str = "standard",
    item_catalog_style: str = "minimal",
    output_mode: str = "labels_and_evidence",
) -> str:
    if role_directive not in {"standard", "compliance_expert_v1", "source_first_v1"}:
        raise ValueError(
            "role_directive must be standard, compliance_expert_v1, or source_first_v1"
        )
    duty_text = (
        COMPLIANCE_EXPERT_DUTY_V1
        if role_directive == "compliance_expert_v1"
        else SOURCE_FIRST_WORKFLOW_V1
        if role_directive == "source_first_v1"
        else ""
    )
    if profile in {
        "official_baseline_v1", "official_baseline_subset_v1", "complete_fact_v1",
        "complete_fact_subset_v1",
    }:
        if (
            (profile in {"official_baseline_v1", "complete_fact_v1"} and active_items != ITEMS)
            or output_mode not in {"labels_and_evidence", "labels_only"}
        ):
            raise ValueError("official_baseline_v1 and complete_fact_v1 require all items and VE or labels-only output")
        if item_catalog_style not in {"minimal", "official_references"}:
            raise ValueError("item_catalog_style must be minimal or official_references")
        lines = []
        for item in active_items:
            definition = item_table[item]
            tag = "  [근거 없음]" if definition.get("부재탐지") and output_mode == "labels_only" else "  [근거 없음 — null]" if definition.get("부재탐지") else ""
            note = f" ({definition['비고']})" if definition.get("비고") else ""
            if layout == "markdown_v2":
                reference = ""
                if item_catalog_style == "official_references":
                    national = definition.get("국가계약법", "")
                    local = definition.get("지방계약법", "")
                    reference = f"\n- **공식 참조**: 국가계약 {national} / 지방계약 {local}"
                lines.append(
                    f"### `{item}` — {definition['항목명']}{tag}"
                    + (f"\n- **항목표 비고**: {definition['비고']}" if definition.get("비고") else "")
                    + reference
                    + (
                        "\n- **판정 카드**\n"
                        + _render_card_text(decision_cards[item]["prompt_text"], indent="  ", output_mode=output_mode)
                        if decision_cards else ""
                    )
                )
            else:
                reference = ""
                if item_catalog_style == "official_references":
                    reference = (
                        f"\n  국가계약법 참조: {definition.get('국가계약법', '')}"
                        f"\n  지방계약법 참조: {definition.get('지방계약법', '')}"
                    )
                card = (
                    "\n  판정 카드: " + decision_cards[item]["prompt_text"]
                    if decision_cards else ""
                )
                lines.append(f"- {item}: {definition['항목명']}{note}{tag}{reference}{card}")
        head = OFFICIAL_BASELINE_LABELS_ONLY_HEAD if output_mode == "labels_only" else OFFICIAL_BASELINE_SYSTEM_HEAD
        tail = OFFICIAL_BASELINE_LABELS_ONLY_TAIL if output_mode == "labels_only" else OFFICIAL_BASELINE_SYSTEM_TAIL
        if profile in {"official_baseline_subset_v1", "complete_fact_subset_v1"}:
            item_list = ", ".join(active_items)
            item_count = len(active_items)
            head = (
                head.replace("아래 24개 항목 각각", f"아래 지정 항목({item_list}) 각각")
                .replace("24개 항목 전부", f"지정 항목({item_list}) 전부")
                .replace("판정할 24개 항목", f"판정할 {item_count}개 항목")
            )
            tail = tail.replace("v1~v24", item_list)
        if layout == "markdown_v2":
            head = "# 역할\n" + head.replace("\n\n지켜야 할 것", "\n\n# 기본 규칙\n지켜야 할 것").replace("\n\n판정할 24개 항목", "\n\n# 판정 항목")
            tail = "# 출력 형식\n" + tail.strip()
        return head + duty_text + "\n" + "\n".join(lines) + "\n" + tail
    if profile != "default":
        raise ValueError(
            "profile must be default, official_baseline_v1, official_baseline_subset_v1, or "
            "complete_fact_v1, complete_fact_subset_v1"
        )
    lines = []
    sparse_anchor = output_mode == "labels_and_sparse_evidence"
    # Sparse output changes only JSON serialization.  Retain every normal VE
    # instruction, card rendering rule, and document-evidence requirement.
    semantic_output_mode = "labels_and_evidence" if sparse_anchor else output_mode
    if not active_items or any(item not in ITEMS for item in active_items):
        raise ValueError("active_items must be a non-empty subset of v1..v24")
    if layout not in {"plain", "markdown", "markdown_v2"}:
        raise ValueError("layout must be plain, markdown, or markdown_v2")
    if semantic_output_mode not in {"labels_and_evidence", "labels_only", "labels_and_anchor"}:
        raise ValueError("output_mode must be labels_and_evidence, labels_only, or labels_and_anchor")
    if semantic_output_mode == "labels_only" and v8_composite_enabled:
        raise ValueError("labels_only does not support v8 composite observations")
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
                    + _render_card_text(prompt_text, indent="  ", output_mode=semantic_output_mode)
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
    scope_guidance = (
        LABELS_ONLY_DOCUMENT_GUIDANCE if document_scoped and semantic_output_mode == "labels_only"
        else DOCUMENT_SCOPED_GUIDANCE.replace("근거 문구", "판단어구").replace("근거문구", "판단어구").replace("근거 문서", "판정 대상 문서").replace("위반 근거", "판정 어구").replace("근거로", "판정에") if document_scoped and semantic_output_mode == "labels_and_anchor"
        else DOCUMENT_SCOPED_GUIDANCE if document_scoped else ""
    )
    card_guidance = ""
    if decision_cards and layout == "plain":
        card_guidance = (
            ("\n\n## 항목별 상세 판정 카드\n" if layout == "markdown" else "\n\n[항목별 상세 판정 카드]\n")
            +
            "각 카드의 1 조건을 모두 만족할 때만 1이다. 카드의 0 조건 하나라도 해당하거나 "
            "확인할 수 없으면 0이다. 카드의 법령 참조는 판단 범위이고, "
            + ("공고/첨부문서 원문에서 실제 문구를 확인해 판단한다.\n" if semantic_output_mode == "labels_only" else "판단어구는 언제나 공고/첨부문서 원문에서만 그대로 복사한다.\n" if semantic_output_mode == "labels_and_anchor" else "근거문구는 언제나 공고/첨부문서 원문에서만 인용한다.\n")
            + "\n\n".join(
                (f"### {item} | {decision_cards[item]['item_name']}\n" if layout == "markdown" else f"[{item} | {decision_cards[item]['item_name']}]\n")
                + _render_card_text(decision_cards[item]["prompt_text"], output_mode=semantic_output_mode)
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
    head = (LABELS_ONLY_SYSTEM_HEAD if semantic_output_mode == "labels_only" else ANCHOR_SYSTEM_HEAD if semantic_output_mode == "labels_and_anchor" else SYSTEM_HEAD).replace("아래 24개 항목 각각", f"아래 지정 항목({item_range}) 각각")
    head = head.replace("1. v1~v24를 모두 출력한다.", f"1. {', '.join(active_items)}을 모두 출력한다.")
    tail = (LABELS_ONLY_SYSTEM_TAIL if semantic_output_mode == "labels_only" else ANCHOR_SYSTEM_TAIL if semantic_output_mode == "labels_and_anchor" else SYSTEM_TAIL).replace("v1~v24", ", ".join(active_items)).replace("지정된 v", ", ".join(active_items))
    absence_only = set(active_items) == set(ABSENCE_ITEMS)
    v24_only = active_items == ("v24",)
    group_workflow = ""
    if absence_only:
        group_workflow = """

# 부재 항목 판정 순서
1. **적용 확인**: 각 카드의 적용 확인 조건을 먼저 충족하는지 메타데이터와 공고 자료로 확인한다.
2. **필수 문구 확인**: 이 메시지의 `# 공고 자료`에 있는 모든 문서 조각에서 각 카드가 요구하는 제한·조건·예외 문구가 하나라도 있는지 찾는다.
3. **판정**: 적용 대상이고 필요한 문구가 이 문서 조각들에 전혀 없을 때만 1이다. 문구가 있거나, 적용 여부가 불명확하면 0이다.
4. **문서 묶음 결합**: 이 호출은 공고 자료의 한 문서 묶음만 확인한다. 최종 판정은 모든 문서 묶음의 결과를 시스템이 결합한다. 근거문구는 항상 null로 둔다.
"""
    elif v24_only:
        group_workflow = """

# v24 대조 순서
1. **공고 값 찾기**: 공고 자료에서 예산·가격, 계약·낙찰방법, 지역제한, 업종제한 중 실제 값이 명시된 필드만 찾는다.
2. **같은 필드 대조**: `v24 메타데이터 대조 체크리스트`의 같은 의미 필드와 한 쌍씩 비교한다.
3. **판정**: 두 값이 실제로 양립 불가능할 때만 1이다. 참가자격·지역·업종 제한 문구가 있다는 사실만으로는 불일치가 아니다. 대응 값이 없거나 불명확하면 0이다.
4. **근거문구**: 1이면 불일치한 공고 자료 원문의 값을 그대로 인용한다.
"""
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
            item_rule = (
                "각 항목은 아래 카드의 **적용 확인**, **1 조건**, **0 조건**을 순서대로 확인한다. "
                "1 조건을 모두 충족할 때만 1이고, 0 조건 또는 불확실성이 있으면 0이다."
                if decision_cards
                else
                "각 항목의 항목명과 비고를 기준으로, 공고 자료의 실제 제한·요구·불일치가 "
                "그 항목의 위반을 뜻하는지 확인한다. 불확실하면 0이다."
            )
            workflow = """

# 판정 순서
1. **공고 자료 확인**: `# 공고 자료` 아래의 공고 자료 원문에서 해당 문구를 찾는다.
2. **항목별 판단**: """ + item_rule + """
3. **명시 확인**: 부재탐지가 아닌 항목은 공고 자료 원문에 해당 법적 조건을 뒷받침하는 실제 연속 문구가 있을 때만 1로 둔다.
4. **출력**: 모든 v를 판단한 뒤 아래 JSON 객체 하나만 출력한다.
"""
            if semantic_output_mode == "labels_and_evidence":
                workflow = workflow.replace(
                    "3. **명시 확인**: 부재탐지가 아닌 항목은 공고 자료 원문에 해당 법적 조건을 뒷받침하는 실제 연속 문구가 있을 때만 1로 둔다.\n4. **출력**", "3. **근거 확정**: 부재탐지가 아닌 항목을 1로 둘 때는 공고 자료 원문의 변경 없는 연속 문구를 복사한다. 복사할 수 없으면 0이다.\n4. **출력**"
                )
            elif semantic_output_mode == "labels_and_anchor":
                workflow = workflow.replace(
                    "3. **명시 확인**: 부재탐지가 아닌 항목은 공고 자료 원문에 해당 법적 조건을 뒷받침하는 실제 연속 문구가 있을 때만 1로 둔다.\n4. **출력**", "3. **판단어구 확정**: 부재탐지가 아닌 항목을 1로 둘 때는 공고 자료 원문의 변경 없는 연속 문구를 판단어구로 복사한다. 복사할 수 없으면 0이다.\n4. **출력**"
                )
            scope_guidance = workflow + group_workflow + scope_guidance
            skeleton = ",\n".join(
                (f'  "{item}": 0' if output_mode == "labels_only" else f'  "{item}": {{"위반여부": 0, "판단어구": null}}' if output_mode == "labels_and_anchor" else f'  "{item}": {{"위반여부": 0, "근거문구": null}}')
                for item in active_items
            )
            tail = (
                "# 출력 형식\n설명·분석·Markdown 없이 아래 키만 가진 JSON 객체 하나를 출력한다. 각 값은 0 또는 1이다.\n```json\n{\n" + skeleton + "\n}\n```"
                if output_mode == "labels_only" else "# 출력 형식\n설명·분석·Markdown 없이 아래 키만 가진 JSON 객체 하나를 출력한다. 각 `위반여부`는 0 또는 1이며, 0이면 `판단어구`는 null이다.\n```json\n{\n" + skeleton + "\n}\n```" if output_mode == "labels_and_anchor" else
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
            + ("아래는 위반 여부를 판정할 때 적용할 기준이다. 법령 원문 또는 대회 제공 법령 기반 요약의 조건과 공고 자료를 대조해 판정한다. 참고자료만으로 1을 정하지 않는다.\n" if output_mode == "labels_only" else "아래는 위반 여부를 판정할 때 적용할 기준이다. 법령 원문 또는 대회 제공 법령 기반 요약의 조건과 공고 자료를 대조해 판정한다. 참고자료는 공고문이 아니며 위반 근거문구도 아니다. 위반여부를 1로 할 때의 근거문구는 반드시 공고 자료 원문에서만 그대로 복사한다.\n")
            + reference_text
        )
    prompt = f"{head}{duty_text}\n" + "\n".join(lines) + f"\n{guidance}{scope_guidance}{card_guidance}{merge_guidance}{navigation_guidance}{candidate_guidance}"
    if layout == "markdown_v2":
        prompt += reference_section + "\n\n" + tail
    else:
        prompt += "\n" + tail + reference_section
    if sparse_anchor:
        sparse_labels = ",".join(f'"{item}":0' for item in active_items)
        sparse_absence = ",".join(
            f'"{item}":"필수조건_확인"' for item in active_items if item in ABSENCE_ITEMS
        )
        sparse_contract = f"""
# 출력 형식
설명 없이 JSON 객체 하나를 출력한다.
- `판정`에는 모든 v의 0 또는 1을 넣는다.
- `발췌`에는 1인 부재탐지 이외 항목마다 공고 자료 원문의 변경 없는 연속 `근거문구`를 반드시 한 번 넣는다. 0인 항목은 발췌에 넣지 않는다.
- `부재검토`에는 부재탐지 항목마다 `필수조건_확인`, `미확인`, `비적용_또는_불명` 중 하나를 넣는다. 이는 검토 기록이며 `판정`의 0/1을 바꾸지 않는다.
```json
{{"판정":{{{sparse_labels}}},"발췌":[],"부재검토":{{{sparse_absence}}}}}
```
"""
        prompt = prompt.rsplit("# 출력 형식", 1)[0] + sparse_contract
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


def build_official_baseline_context(record: dict[str, Any], max_chars: int | None) -> str:
    """Match organizer baseline ``build_context`` byte-for-byte in policy."""
    order = {name: index for index, name in enumerate((*DOCUMENT_ORDER, "기타"))}
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
        if max_chars is not None and used + len(header) + len(body) > max_chars:
            if index == 0:
                body = body[: max(0, max_chars - len(header))]
                truncated = True
            else:
                dropped[document["type"]] += 1
                continue
        chunks.append(header + body)
        used += len(header) + len(body)
    for document_type, count in (record.get("dropped_doc_counts") or {}).items():
        dropped[document_type] += count
    text = "\n\n".join(chunks)
    if truncated:
        text += "\n\n[절단] 공고문 뒷부분이 길이 예산으로 잘렸다"
    if dropped:
        text += "\n\n[미수록 문서] " + ", ".join(
            f"{name} {count}건" for name, count in sorted(dropped.items())
        )
    return text


def format_official_baseline_meta(record: dict[str, Any]) -> str:
    lines = []
    for field in OFFICIAL_BASELINE_META_FIELDS:
        if field in record["meta"]:
            value = record["meta"][field]
            lines.append(f"- {field}: {'미기재' if value is None else value}")
    return "\n".join(lines)


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
    prompt_profile: str = "default",
    metadata_style: str = "full_json",
    output_mode: str = "labels_and_evidence",
    task_profile: str = "general",
) -> list[dict[str, str]]:
    if prompt_profile in {
        "official_baseline_v1", "official_baseline_subset_v1", "complete_fact_v1",
        "complete_fact_subset_v1",
    }:
        if output_mode not in {"labels_and_evidence", "labels_only"}:
            raise ValueError("official_baseline_v1 supports VE or labels-only output")
        if metadata_style not in {"official_lines", "full_json"}:
            raise ValueError("metadata_style must be official_lines or full_json")
        context = document_context if document_context is not None else build_official_baseline_context(record, max_document_chars)
        metadata = (
            format_official_baseline_meta(record)
            if metadata_style == "official_lines"
            else json.dumps(record["meta"], ensure_ascii=False, sort_keys=True, indent=2)
        )
        if "# 역할" in system_prompt:
            product_section = (
                "\n\n# 대회 제공 경쟁제품 고시 확인\n"
                + competition_product_context
                if competition_product_context else ""
            )
            user_prompt = (
                "# 나라장터 입력 메타데이터\n"
                + (metadata if metadata_style == "official_lines" else "```json\n" + metadata + "\n```")
                + product_section
                + "\n\n# 공고 자료\n" + context
                + "\n\n# 출력\n모든 v의 위반여부와 근거문구를 JSON 객체 하나로 출력한다."
            )
        elif prompt_profile in {"complete_fact_v1", "complete_fact_subset_v1"}:
            product_section = (
                "\n\n[대회 제공 경쟁제품 고시 확인]\n"
                + competition_product_context.rstrip()
                if competition_product_context else ""
            )
            user_prompt = (
                f"[나라장터 입력 메타]\n{metadata}"
                + product_section
                + f"\n\n[공고 자료 원문]\n{context}\n"
            )
        else:
            product_section = (
                "\n\n[대회 제공 경쟁제품 고시 확인]\n"
                + competition_product_context
                if competition_product_context else ""
            )
            user_prompt = (
                f"[공고 ID] {record['id']}\n\n"
                f"[나라장터 입력 메타]\n{metadata}\n\n"
                + product_section
                + f"[문서]\n{context}\n"
            )
        return [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    if prompt_profile != "default":
        raise ValueError(
            "prompt_profile must be default, official_baseline_v1, official_baseline_subset_v1, or "
            "complete_fact_v1"
        )
    sparse_evidence = output_mode == "labels_and_sparse_evidence"
    semantic_output_mode = "labels_and_evidence" if sparse_evidence else output_mode
    if semantic_output_mode not in {"labels_and_evidence", "labels_only", "labels_and_anchor"}:
        raise ValueError("output_mode must be labels_and_evidence, labels_only, or labels_and_anchor")
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
        if semantic_output_mode == "labels_only":
            user_prompt = (
                "# 나라장터 입력 메타데이터\n"
                "아래 값은 적용 법령·금액·계약방식 등을 공고 자료와 대조할 때 쓰는 입력값이다. 이 값만으로 1을 정하지 않는다.\n"
                "```json\n" + metadata + "\n```"
                + fact_section
                + "\n\n# 공고 자료\n"
                "아래 공고 자료 원문에서 실제 제한·요구·불일치와 필요한 문구의 부재를 확인하고, 입력 메타데이터는 적용 조건을 대조하는 데 사용한다.\n"
                + document_text
                + "\n\n# 출력\n"
                "지정된 모든 v의 위반여부를 0 또는 1로 판단한 JSON 객체 하나만 출력한다."
            )
        elif semantic_output_mode == "labels_and_anchor":
            user_prompt = (
                "# 나라장터 입력 메타데이터\n"
                "아래 값은 적용 법령·금액·계약방식 등을 공고문과 대조할 때 쓰는 입력값이다. 단독으로 위반을 정하지 않는다.\n"
                "```json\n" + metadata + "\n```" + fact_section + "\n\n# 공고 자료\n"
                "아래 공고 자료 원문에서만 판단어구를 그대로 복사할 수 있다.\n" + document_text
                + "\n\n# 출력\n" + ("`판정`에 모든 v의 0/1을 넣는다. 1인 부재탐지 이외 항목은 `발췌` 배열에 공고 자료 원문의 정확 문구를 반드시 넣는다. 부재탐지는 `부재검토`에 상태를 넣는다. JSON 객체 하나만 출력한다." if sparse_evidence else "지정된 모든 v를 판단한다. 1이면 공고 자료 원문의 판단어구를 넣고, 0이면 null을 넣는다. 설명 없이 지정된 키만 가진 JSON 객체 하나를 출력한다.")
            )
        else:
            sparse_output_instruction = (
                "`판정`에는 모든 v의 0/1을 넣는다. 1인 부재탐지 이외 항목은 `발췌` 배열에 "
                "공고 자료 원문의 정확한 `근거문구`를 반드시 한 번 넣는다. 부재탐지는 `부재검토`에 "
                "검토 상태를 넣는다. 설명 없이 JSON 객체 하나만 출력한다."
            )
            document_intro = (
                "아래 공고 자료 원문만 부재탐지가 아닌 항목의 근거문구로 인용할 수 있다."
                if task_profile != "absence"
                else "아래 공고 자료는 이 부재 판정 호출이 확인할 문서 묶음이다. 각 항목의 필수 문구가 이 문서 묶음에 있는지 확인한다. 부재 항목의 근거문구는 항상 null이다."
            )
            output_instruction = (
                sparse_output_instruction
                if sparse_evidence
                else "지정된 모든 v를 판단한다. 부재 항목은 1이어도 근거문구를 null로 두고, 0도 null로 둔다. 설명 없이 지정된 키만 가진 JSON 객체 하나를 출력한다."
                if task_profile == "absence"
                else "지정된 모든 v를 판단한다. 1이면 공고 자료 원문의 근거문구를 넣고, 0이면 null을 넣는다. 설명 없이 지정된 키만 가진 JSON 객체 하나를 출력한다."
            )
            user_prompt = (
                "# 나라장터 입력 메타데이터\n"
                "아래 값은 적용 법령·금액·계약방식 등을 공고문과 대조할 때 쓰는 입력값이다. 단독으로 위반 근거문구가 될 수 없다.\n"
                "```json\n" + metadata + "\n```"
                + fact_section
                + "\n\n# 공고 자료\n"
                + document_intro + "\n"
                + document_text
                + "\n\n# 출력\n"
                + output_instruction
            )
    else:
        output_instruction = (
            "각 v의 위반여부를 0 또는 1로 판단한 JSON 객체 하나만 출력한다."
            if semantic_output_mode == "labels_only"
            else "1이면 공고 자료 원문의 판단어구를 넣고, 0이면 null을 넣는다. 설명 없이 JSON 객체 하나만 출력한다."
            if semantic_output_mode == "labels_and_anchor"
            else "1이면 공고 자료 원문의 근거문구를 넣고, 0이면 null을 넣는다. 설명 없이 JSON 객체 하나만 출력한다."
        )
        user_prompt = (
            f"[나라장터 입력 메타데이터]\n{metadata}{facts}\n\n"
            f"[문서]\n{document_text}\n\n"
            "[출력]\n"
            + ("메타데이터 값만으로 1을 정하지 말고 공고 자료의 실제 내용과 함께 대조한다. " if semantic_output_mode == "labels_only" else "")
            + "나라장터 입력 메타데이터와 공고 자료를 대조하여 지정된 모든 v를 판정한다. "
            + output_instruction
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
    general_items = [item for item in ("v12", "v14", "v15", "v16", "v17", "v18") if item in active_items]
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


def append_untrusted_review_draft(
    messages: list[dict[str, str]],
    judgment: dict[str, dict[str, Any]],
    active_items: tuple[str, ...] = ITEMS,
) -> list[dict[str, str]]:
    """Append first-pass labels as explicitly non-source review material.

    This supports the two-pass adjudication *preview* without treating an
    earlier model response as evidence.  In particular, evidence strings are
    intentionally omitted: the final reviewer must locate its own unchanged
    substring in the actual notice documents.
    """
    if len(messages) != 2 or messages[0].get("role") != "system" or messages[1].get("role") != "user":
        raise ValueError("review draft requires one system message and one user message")
    if not active_items or any(item not in judgment for item in active_items):
        raise ValueError("review draft is missing an active-item judgment")
    labels: list[str] = []
    for item in active_items:
        value = judgment[item].get("위반여부")
        if value not in {0, 1}:
            raise ValueError(f"review draft has invalid label for {item}")
        labels.append(f"- {item}: {value}")
    review_text = (
        "\n\n[1차 검토 초안 — 공고 자료가 아님]\n"
        "아래 값은 다른 검토자의 임시 판단일 뿐이며, 사실·법령·근거문구가 아니다. "
        "초안의 0 또는 1을 따르거나 인용하지 말고, 반드시 위의 나라장터 입력 메타와 "
        "공고 자료 원문을 다시 읽어 독립적으로 판정한다. 위반여부를 1로 둘 때의 근거문구는 "
        "이 초안이 아니라 공고 자료 원문에서만 그대로 복사한다.\n"
        + "\n".join(labels)
        + "\n\n[재심사]\n"
        "24개 항목을 모두 다시 판단하여, 지시된 JSON 하나만 출력한다."
    )
    return [messages[0], {"role": "user", "content": messages[1]["content"] + review_text}]


def append_untrusted_vonly_drafts(
    messages: list[dict[str, str]],
    judgments: tuple[dict[str, dict[str, Any]], ...],
    active_items: tuple[str, ...] = ITEMS,
) -> list[dict[str, str]]:
    """Append multiple advisory V-only readings; the resolver still owns labels."""
    if len(messages) != 2 or messages[0].get("role") != "system" or messages[1].get("role") != "user":
        raise ValueError("V-only draft review requires one system message and one user message")
    if len(judgments) < 2:
        raise ValueError("V-only draft review requires at least two independent drafts")
    lines = [
        "\n\n[독립 V-only 검토 초안 — 공고 자료가 아님]",
        "아래 값들은 서로 독립된 임시 판단일 뿐이며, 사실·법령·근거문구가 아니다. "
        "다수결이나 어느 초안도 따르지 말고, 위의 metadata·판정 카드·공고 자료 원문을 "
        "다시 읽어 각 항목을 독립적으로 최종 판단한다.",
    ]
    for index, judgment in enumerate(judgments, 1):
        if any(item not in judgment or judgment[item].get("위반여부") not in {0, 1} for item in active_items):
            raise ValueError("V-only draft is missing a valid active-item label")
        lines.append(f"- 독립초안 {index}: " + ", ".join(
            f"{item}={judgment[item]['위반여부']}" for item in active_items
        ))
    lines.extend(["", "[최종 V-only 재판정]", "지정된 모든 v를 0 또는 1로 JSON 하나에 출력한다."])
    return [messages[0], {"role": "user", "content": messages[1]["content"] + "\n".join(lines)}]


def build_inventory_system_prompt(
    item_table: dict[str, dict[str, Any]],
    decision_cards: dict[str, dict[str, Any]] | None,
    active_items: tuple[str, ...] = ITEMS,
) -> str:
    """Build stage-1 instructions that collect source facts, never labels."""
    cards = build_system_prompt(
        item_table,
        decision_cards=decision_cards,
        active_items=active_items,
        profile="complete_fact_v1",
    )
    cards = cards.replace(
        "공고문과 첨부 문서, 그리고 나라장터 입력 메타를 함께 읽고 아래 24개 항목 각각에 대해\n"
        "위반 여부(1/0)와 근거 문구를 판정한다.",
        "공고문과 첨부 문서, 그리고 나라장터 입력 메타를 함께 읽고 아래 항목의\n"
        "최종 판정에 필요한 실제 원문 사실을 수집한다.",
    ).replace(
        "지켜야 할 것\n1. 24개 항목 전부에 답한다. 판단이 어려운 항목도 비워 두지 말고 0으로 낸다.\n"
        "2. 근거 문구는 반드시 **주어진 문서에 그대로 있는 문장**을 옮긴다. 요약하거나 고쳐 쓰지 않는다.\n"
        "   원문에 없는 문구는 근거로 인정되지 않는다. 500자를 넘기지 않는다.\n"
        "3. 아래 '근거 없음' 표시가 붙은 항목은 **있어야 할 문구가 없는 것**이 위반이다.\n"
        "   인용할 원문이 존재하지 않으므로 근거 문구를 null로 둔다.",
        "수집 원칙\n- 모든 지정 항목에 대해 관련 원문 사실이 있으면 한 구절만 수집한다.\n"
        "- 이 단계에서는 위반 여부·근거문구·부재 위반을 확정하지 않는다.",
    )
    cards = re.sub(r"\n출력은 JSON 하나로만 낸다\.[\s\S]*?설명이나 머리말을 덧붙이지 않는다\.", "", cards)
    return cards + """

[원문 사실 수집 — 최종 판정 아님]
이번 작업은 위반 여부를 판정하지 않는다. 각 항목마다 이 문서 묶음에서 관련될 수 있는
실제 원문 한 구절만 찾는다. 그 구절은 제한·요구·금액·날짜·기관·지역·제품·예외처럼
나중 판단에 필요한 사실일 수 있으며, 위반을 뜻하지 않아도 된다.

- 문서에 실제로 연속해서 있는 문구만 그대로 복사한다. 요약·추론·법령 문구는 쓰지 않는다.
- 관련 문구를 찾지 못하면 null이다. null은 위반 없음이나 비적용이 아니다.
- 부재탐지 항목은 필요한 조건 또는 예외 문구를 발견했을 때만 그 원문을 복사한다.
  null은 이 문서 묶음에서만 발견하지 못했다는 관찰이다.
- 각 항목은 최대 하나의 짧은 구절(500자 이하)만 반환한다.

설명·판정·Markdown 없이 v별 문자열 또는 null만 가진 JSON 객체 하나를 출력한다.
"""


def append_source_inventory(
    messages: list[dict[str, str]],
    inventory: dict[str, list[tuple[str, str]]],
    absence_pack_summary: dict[str, str],
    active_items: tuple[str, ...] = ITEMS,
) -> list[dict[str, str]]:
    """Attach non-authoritative current-notice excerpts to the final task."""
    if len(messages) != 2:
        raise ValueError("source inventory requires system/user message pair")
    lines = [
        "[전체 공고 자료에서 수집한 원문 후보 — 최종 판정이나 법령 근거가 아님]",
        "아래는 다른 단계가 현재 공고 자료에서 그대로 복사한 후보다. 후보가 있어도 위반이 아니며, 후보가 없어도 0이 아니다.",
        "반드시 위 공고 자료·metadata·판정 카드를 다시 대조하여 독립적으로 모든 v를 판정한다.",
    ]
    for item in active_items:
        candidates = inventory.get(item, [])
        if candidates:
            rendered = " | ".join(f"[{doc_id}] {text}" for doc_id, text in candidates)
            lines.append(f"- {item}: {rendered}")
        elif item in absence_pack_summary:
            lines.append(f"- {item}: {absence_pack_summary[item]}")
        else:
            lines.append(f"- {item}: 후보없음 (이는 0이 아님)")
    return [messages[0], {"role": "user", "content": messages[1]["content"] + "\n\n" + "\n".join(lines)}]


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
