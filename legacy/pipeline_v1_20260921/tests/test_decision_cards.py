from pathlib import Path

import pytest

from src.data import load_decision_cards, load_item_table
from src.prompt import build_system_prompt
from scripts.build_decision_cards import (
    CARD_TEXT_V6,
    CARD_TEXT_V9_V6_SCOPE,
    CARD_TEXT_V10_V6_V7_SCOPE,
    CARD_TEXT_V16_V14_THRESHOLD,
    CARD_TEXT_V17_V6_THRESHOLD,
    CARD_TEXT_V18_V1_QUALIFICATION_SCOPE,
    CARD_TEXT_V19_V20_THRESHOLD,
    CARD_TEXT_V20_V20_APPLICABILITY_GATE,
    CARD_TEXT_V21_V8_OPERATIONAL,
    CARD_TEXT_V22_V12_PRODUCT_TARGET,
    CARD_TEXT_V23_V7_THRESHOLD,
)


def test_decision_cards_match_official_item_table(tmp_path: Path) -> None:
    item_table = {
        "v1": {"항목명": "항목 1"},
        "v2": {"항목명": "항목 2"},
    }
    path = tmp_path / "cards.json"
    path.write_text(
        '{"cards":{"v1":{"item_name":"항목 1","prompt_text":"1 조건"},'
        '"v2":{"item_name":"항목 2","prompt_text":"2 조건"}}}',
        encoding="utf-8",
    )

    cards = load_decision_cards(path, item_table)

    assert cards["v1"]["prompt_text"] == "1 조건"


def test_decision_card_item_name_mismatch_is_rejected(tmp_path: Path) -> None:
    item_table = {"v1": {"항목명": "항목 1"}}
    path = tmp_path / "cards.json"
    path.write_text(
        '{"cards":{"v1":{"item_name":"다른 항목","prompt_text":"조건"}}}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="item_name"):
        load_decision_cards(path, item_table)


def test_prompt_includes_all_decision_cards() -> None:
    item_table = {f"v{i}": {"항목명": f"항목 {i}", "비고": ""} for i in range(1, 25)}
    cards = {
        item: {"item_name": definition["항목명"], "prompt_text": f"{item} 상세 조건"}
        for item, definition in item_table.items()
    }

    prompt = build_system_prompt(item_table, decision_cards=cards)

    assert "[항목별 상세 판정 카드]" in prompt
    assert "v24 상세 조건" in prompt


def test_v25_v11_completeness_repair_changes_only_v11_and_renders_exceptions() -> None:
    from scripts.build_decision_cards import CARD_TEXT_V25_V11_EXCEPTIONS

    changed = {
        item for item in CARD_TEXT_V10_V6_V7_SCOPE
        if CARD_TEXT_V10_V6_V7_SCOPE[item] != CARD_TEXT_V25_V11_EXCEPTIONS[item]
    }
    assert changed == {"v11"}
    item_table = {
        f"v{i}": {"항목명": f"항목 {i}", "비고": ""}
        for i in range(1, 25)
    }
    cards = {
        item: {"item_name": item_table[item]["항목명"], "prompt_text": text}
        for item, text in CARD_TEXT_V25_V11_EXCEPTIONS.items()
    }
    prompt = build_system_prompt(item_table, decision_cards=cards)
    for condition in (
        "특이사항", "모든 첨부", "중소기업자 중 지명경쟁",
        "우선구매·수의구매", "조합 추천", "유찰 후", "공공기관 특별사정",
        "전자조달 입력 사유", "적용 특별사유", "e11은 항상 빈 문자열",
    ):
        assert condition in prompt


def test_v26_semantic_complete_consolidates_source_repairs() -> None:
    from scripts.build_decision_cards import CARD_TEXT_V26_SEMANTIC_COMPLETE

    assert set(CARD_TEXT_V26_SEMANTIC_COMPLETE) == {
        f"v{i}" for i in range(1, 25)
    }
    for item, conditions in {
        "v2": ("2억 3천만원", "7억 1천만원", "5억원", "입찰추정가격"),
        "v4": ("고시금액 미만 실적제한 여부와 별개", "특정기관 발주실적"),
        "v5": ("2억 3천만원", "7억 1천만원", "입찰추정가격"),
        "v8": ("같은 입찰자", "평가의 점수 산정", "2인 이상 견적 수의계약"),
        "v11": ("조합 추천", "유찰 후", "공공기관 특별사정"),
        "v13": ("제7조의2", "3개 이상의", "공동사업", "별도 지정"),
        "v14": ("2억 3천만원", "특이사항"),
        "v15": ("1억원 이상", "일반 영리 참가자", "검체검사"),
        "v16": ("1억원 이상 2억 3천만원 미만", "모든 첨부", "e16"),
        "v17": ("3인 이하", "2인 미만", "중기업까지"),
        "v18": ("1억원 미만", "필수 확인서", "e18"),
        "v20": ("GATE A", "20억원", "80억원", "상호출자제한기업집단"),
        "v21": ("1천억원 이상", "분담이행", "20% 범위", "4~6%"),
    }.items():
        for condition in conditions:
            assert condition in CARD_TEXT_V26_SEMANTIC_COMPLETE[item]


def test_v24_absence_revision_changes_only_v18_and_preserves_source_roles() -> None:
    from scripts.build_decision_cards import CARD_TEXT_V24_V18_ABSENCE

    changed = {
        item for item in CARD_TEXT_V10_V6_V7_SCOPE
        if CARD_TEXT_V10_V6_V7_SCOPE[item] != CARD_TEXT_V24_V18_ABSENCE[item]
    }
    assert changed == {"v18"}
    text = CARD_TEXT_V24_V18_ABSENCE["v18"]
    for condition in (
        "입찰추정가격", "1억원 미만", "3인 이하", "2인 미만",
        "필수 확인서 요구를 무시하지 않는다", "모든 첨부", "적용 예외",
        "모든 pass", "e18은 항상 빈 문자열",
    ):
        assert condition in text


def test_v22_product_target_revision_changes_only_v12() -> None:
    changed = {
        item for item in CARD_TEXT_V10_V6_V7_SCOPE
        if CARD_TEXT_V10_V6_V7_SCOPE[item] != CARD_TEXT_V22_V12_PRODUCT_TARGET[item]
    }

    assert changed == {"v12"}
    assert "실제 구매대상과 같은 대상인지" in CARD_TEXT_V22_V12_PRODUCT_TARGET["v12"]
    assert "특이사항" in CARD_TEXT_V22_V12_PRODUCT_TARGET["v12"]


def test_v23_threshold_revision_changes_only_v7_and_keeps_model_owned_logic() -> None:
    changed = {
        item for item in CARD_TEXT_V10_V6_V7_SCOPE
        if CARD_TEXT_V10_V6_V7_SCOPE[item] != CARD_TEXT_V23_V7_THRESHOLD[item]
    }

    assert changed == {"v7"}
    text = CARD_TEXT_V23_V7_THRESHOLD["v7"]
    assert "2억 3천만원" in text
    assert "7억 1천만원" in text
    assert "입찰추정가격" in text
    assert "둘 이상의 지역" in text
    assert "유자격자 10인 미만" in text
    assert "2인 이상 견적 수의계약" in text


def test_v27_corrects_only_v23_and_separates_the_three_date_relations() -> None:
    from scripts.build_decision_cards import (
        CARD_TEXT_V26_SEMANTIC_COMPLETE,
        CARD_TEXT_V27_V23_INTERVAL_RELATIONS,
    )

    changed = {
        item for item in CARD_TEXT_V26_SEMANTIC_COMPLETE
        if CARD_TEXT_V26_SEMANTIC_COMPLETE[item]
        != CARD_TEXT_V27_V23_INTERVAL_RELATIONS[item]
    }

    assert changed == {"v23"}
    text = CARD_TEXT_V27_V23_INTERVAL_RELATIONS["v23"]
    for condition in (
        "공고→제안서 마감",
        "설명회→제안서 마감",
        "공고→설명회",
        "40일·20일·10일",
        "7일 전에",
        "제안서 제출마감일의 전날부터 기산",
        "설명일의 전날부터 기산",
    ):
        assert condition in text


def test_v28_corrects_only_v5_local_threshold_selector() -> None:
    from scripts.build_decision_cards import (
        CARD_TEXT_V27_V23_INTERVAL_RELATIONS,
        CARD_TEXT_V28_V5_LOCAL_THRESHOLD_SELECTOR,
    )

    changed = {
        item for item in CARD_TEXT_V27_V23_INTERVAL_RELATIONS
        if CARD_TEXT_V27_V23_INTERVAL_RELATIONS[item]
        != CARD_TEXT_V28_V5_LOCAL_THRESHOLD_SELECTOR[item]
    }

    assert changed == {"v5"}
    text = CARD_TEXT_V28_V5_LOCAL_THRESHOLD_SELECTOR["v5"]
    for condition in (
        "3억 3천만원",
        "1억 5천만원",
        "제5조제1항 적용",
        "서울특별시·부산광역시·인천광역시 관할 군·구",
        "제5조제1항 비적용",
        "모든 시·군·구나 세종시를 일괄 5억원으로 보지 않으며",
    ):
        assert condition in text


def test_v29_corrects_only_v2_threshold_scope() -> None:
    from scripts.build_decision_cards import (
        CARD_TEXT_V28_V5_LOCAL_THRESHOLD_SELECTOR,
        CARD_TEXT_V29_V2_THRESHOLD_SCOPE,
    )

    changed = {
        item for item in CARD_TEXT_V28_V5_LOCAL_THRESHOLD_SELECTOR
        if CARD_TEXT_V28_V5_LOCAL_THRESHOLD_SELECTOR[item]
        != CARD_TEXT_V29_V2_THRESHOLD_SCOPE[item]
    }

    assert changed == {"v2"}
    text = CARD_TEXT_V29_V2_THRESHOLD_SCOPE["v2"]
    for condition in (
        "기획재정부장관 고시금액",
        "2억 3천만원",
        "7억 1천만원",
        "행정안전부 고시금액이나 5억원 분기가 아니라",
        "물품제조는 특수한 설비·기술",
        "용역은 특수한 기술",
        "적용 고시금액 미만",
    ):
        assert condition in text


def test_v30_repairs_the_declared_full_audit_items() -> None:
    from scripts.build_decision_cards import (
        CARD_TEXT_V29_V2_THRESHOLD_SCOPE,
        CARD_TEXT_V30_FULL_SOURCE_CONCORDANCE,
    )

    changed = {
        item for item in CARD_TEXT_V29_V2_THRESHOLD_SCOPE
        if CARD_TEXT_V29_V2_THRESHOLD_SCOPE[item]
        != CARD_TEXT_V30_FULL_SOURCE_CONCORDANCE[item]
    }
    assert changed == {"v3", "v4", "v5", "v6", "v7", "v9", "v12", "v14", "v15"}

    required = {
        "v3": ("3분의 1 이내", "최대 1배", "정확히 1배인 경계"),
        "v4": ("고시금액 이상", "2억 3천만원", "7억 1천만원"),
        "v5": ("종합공사 88억원", "공사 265억원", "종합공사 150억원", "1억 5천만원"),
        "v6": ("종합공사 88억원", "종합공사 150억원", "2인 이상 견적"),
        "v7": ("공사 265억원", "인접지역 납품지·시설 유지관리", "유자격자 10인 미만"),
        "v9": ("생명보호·건강·안전·보건위생", "기술지원·편의성이라는 말만으로"),
        "v12": ("시행령 제10조", "추정가격 1천만원 이상", "같은 제도가 아니므로"),
        "v14": ("제2조의3", "허용하는 근거가 아니다", "별도 법률 근거"),
        "v15": ("1억원 이상 2억 3천만원 미만", "7억1천만원", "규모 제한을 제거"),
    }
    for item, phrases in required.items():
        text = CARD_TEXT_V30_FULL_SOURCE_CONCORDANCE[item]
        for phrase in phrases:
            assert phrase in text


def test_v31_resolves_v4_as_amount_independent_specific_performance_rule() -> None:
    from scripts.build_decision_cards import (
        CARD_TEXT_V30_FULL_SOURCE_CONCORDANCE,
        CARD_TEXT_V31_V4_ORGANIZER_DEFINITION,
    )

    changed = {
        item for item in CARD_TEXT_V30_FULL_SOURCE_CONCORDANCE
        if CARD_TEXT_V30_FULL_SOURCE_CONCORDANCE[item]
        != CARD_TEXT_V31_V4_ORGANIZER_DEFINITION[item]
    }
    assert changed == {"v4"}
    text = CARD_TEXT_V31_V4_ORGANIZER_DEFINITION["v4"]
    assert "입찰추정가격" in text
    assert "별개로 판정" in text
    assert "특정기관 발주실적" in text
    assert "고시금액 이상에서" not in text


def test_v9_scope_revision_changes_only_v6_and_restores_limited_tender_scope() -> None:
    changed = {
        item for item in CARD_TEXT_V6
        if CARD_TEXT_V6[item] != CARD_TEXT_V9_V6_SCOPE[item]
    }

    assert changed == {"v6"}
    assert "국가·지방 제한입찰" in CARD_TEXT_V9_V6_SCOPE["v6"]
    assert "2인 이상 견적 수의계약 등 적용 규정" in CARD_TEXT_V9_V6_SCOPE["v6"]
    assert "지방계약의 고시금액 미만 2인 이상 견적 수의계약 등 적용 유형인지" not in (
        CARD_TEXT_V9_V6_SCOPE["v6"]
    )


def test_v10_scope_revision_changes_only_v7_and_separates_small_contract_allowance() -> None:
    changed = {
        item for item in CARD_TEXT_V9_V6_SCOPE
        if CARD_TEXT_V9_V6_SCOPE[item] != CARD_TEXT_V10_V6_V7_SCOPE[item]
    }

    assert changed == {"v7"}
    assert "국가·지방 제한입찰" in CARD_TEXT_V10_V6_V7_SCOPE["v7"]
    assert "2인 이상 견적 수의계약 등 적용 규정" in (
        CARD_TEXT_V10_V6_V7_SCOPE["v7"]
    )
    assert "v6의 지방 소액수의 적용 유형인지" not in (
        CARD_TEXT_V10_V6_V7_SCOPE["v7"]
    )


def test_v16_threshold_revision_changes_only_v14_and_uses_statutory_selector() -> None:
    changed = {
        item for item in CARD_TEXT_V10_V6_V7_SCOPE
        if CARD_TEXT_V10_V6_V7_SCOPE[item] != CARD_TEXT_V16_V14_THRESHOLD[item]
    }

    assert changed == {"v14"}
    text = CARD_TEXT_V16_V14_THRESHOLD["v14"]
    assert "2억 3천만원" in text
    assert "국가계약법 제4조제1항" in text
    assert "7억 1천만원으로 바꾸지 않는다" in text
    assert "물품 또는 용역" in text
    assert "특이사항 조건" in text


def test_v17_threshold_revision_changes_only_v6_and_preserves_small_contract_exception() -> None:
    changed = {
        item for item in CARD_TEXT_V10_V6_V7_SCOPE
        if CARD_TEXT_V10_V6_V7_SCOPE[item] != CARD_TEXT_V17_V6_THRESHOLD[item]
    }

    assert changed == {"v6"}
    text = CARD_TEXT_V17_V6_THRESHOLD["v6"]
    assert "2억 3천만원" in text
    assert "7억 1천만원" in text
    assert "5억원" in text
    assert "입찰추정가격" in text
    assert "2인 이상 견적 수의계약" in text


def test_v18_revision_changes_only_v1_and_covers_qualification_attributes() -> None:
    changed = {
        item for item in CARD_TEXT_V10_V6_V7_SCOPE
        if CARD_TEXT_V10_V6_V7_SCOPE[item] != CARD_TEXT_V18_V1_QUALIFICATION_SCOPE[item]
    }

    assert changed == {"v1"}
    text = CARD_TEXT_V18_V1_QUALIFICATION_SCOPE["v1"]
    assert "조직·상시 인력·보유 시설·서비스망" in text
    assert "일반 회사·사업자도 실질적으로 참가 가능한 대안" in text
    assert "기관명이나 시설·인력 단어의 존재만으로 1" in text


def test_v19_revision_changes_only_v20_and_completes_sw_threshold_ladder() -> None:
    changed = {
        item for item in CARD_TEXT_V10_V6_V7_SCOPE
        if CARD_TEXT_V10_V6_V7_SCOPE[item] != CARD_TEXT_V19_V20_THRESHOLD[item]
    }

    assert changed == {"v20"}
    text = CARD_TEXT_V19_V20_THRESHOLD["v20"]
    assert "입찰추정가격에 부가가치세를 포함한 금액" in text
    assert "1년 이상 유지관리 계약" in text
    assert "20억원 미만" in text
    assert "40억원 이상 80억원 미만" in text
    assert "상호출자제한기업집단 회사는 금액과 무관" in text
    assert "적용 여부·근거" in text
    assert "일반 중소기업자 제한 문구만으로" in text


def test_v20_revision_changes_only_v20_and_gates_absence_on_actual_sw_scope() -> None:
    changed = {
        item for item in CARD_TEXT_V19_V20_THRESHOLD
        if CARD_TEXT_V19_V20_THRESHOLD[item] != CARD_TEXT_V20_V20_APPLICABILITY_GATE[item]
    }

    assert changed == {"v20"}
    text = CARD_TEXT_V20_V20_APPLICABILITY_GATE["v20"]
    assert "GATE A — 실질 SW 사업" in text
    assert "업무와 무관한 시스템 언급" in text
    assert "소프트웨어사업자 업종 등록만으로는" in text
    assert "즉시 v20=0" in text
    assert "두 GATE를 모두 통과한 뒤에만 부재" in text
    assert "40억원 이상 80억원 미만" in text


def test_v21_revision_changes_only_v8_and_operationalizes_overlap_exceptions() -> None:
    changed = {
        item for item in CARD_TEXT_V10_V6_V7_SCOPE
        if CARD_TEXT_V10_V6_V7_SCOPE[item] != CARD_TEXT_V21_V8_OPERATIONAL[item]
    }

    assert changed == {"v8"}
    text = CARD_TEXT_V21_V8_OPERATIONAL["v8"]
    assert "적격심사·특별신인도·제안서 평가" in text
    assert "같은 입찰자가 모두 충족해야 하는 AND" in text
    assert "2인 이상 견적 수의계약" in text
    assert "그 결합 자체는 v8=0" in text
    assert "별도 항목의 문제" in text
    assert "특수한 기술·공법이 요구되는 공사" in text
    assert "실적 문구만으로 예외를 추정하지 않는다" in text
