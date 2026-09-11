from pathlib import Path

import pytest

from src.data import load_decision_cards, load_item_table
from src.prompt import build_system_prompt
from scripts.build_decision_cards import CARD_TEXT_V6, CARD_TEXT_V9_V6_SCOPE


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
