"""Organizer exact-code facts remain distinct from applicability decisions."""

from __future__ import annotations

import json

import pytest

from src.pps_ai.facts.product_codes import (
    build_product_facts,
    load_product_index,
    parse_supplied_product_codes,
    render_product_facts,
)


def test_parse_exact_codes_preserves_order_and_deduplicates() -> None:
    parsed = parse_supplied_product_codes(
        "첫품명[1234567890], 둘째품명[0987654321], 다시첫품명[1234567890]"
    )
    assert parsed == (("1234567890", "첫품명"), ("0987654321", "둘째품명"))


def test_parse_preserves_organizer_eight_digit_and_comma_name_entries() -> None:
    parsed = parse_supplied_product_codes(
        "상품권[14111608], 프린터,팩시밀리또는복사기용드럼[4410310901]"
    )
    assert parsed == (
        ("14111608", "상품권"),
        ("4410310901", "프린터,팩시밀리또는복사기용드럼"),
    )


@pytest.mark.parametrize("value", ["품명[123456789]", "품명[1234567890], 나머지", 123])
def test_parse_rejects_unexplained_input(value: object) -> None:
    with pytest.raises(ValueError):
        parse_supplied_product_codes(value)


def test_product_renderer_preserves_note_without_deciding_applicability() -> None:
    facts = build_product_facts(
        {"세부품명번호목록": "구매품[1234567890], 다른품[0987654321]"},
        {"1234567890": {"세부품명": "고시품", "특이사항": "특정 용도만 적용"}},
    )
    assert facts[0].special_note == "특정 용도만 적용"
    assert facts[1].csv_name is None
    rendered = render_product_facts(facts)
    assert "특정 용도만 적용" in rendered
    assert "0987654321" in rendered
    assert "일치하는 행이 없습니다" in rendered
    assert "적용 대상" not in rendered
    assert "matched" not in rendered


def test_no_code_is_unknown_not_negative() -> None:
    assert build_product_facts({"세부품명번호목록": None}, {}) == ()
    assert render_product_facts(()) == "공고 메타데이터에 세부품명번호가 제공되지 않았습니다."


def test_load_index_rejects_non_exact_code(tmp_path) -> None:
    path = tmp_path / "products.json"
    path.write_text(json.dumps({
        "artifact": "competition_products_v1",
        "products": {"123456789": {"세부품명": "품명", "특이사항": ""}},
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="code"):
        load_product_index(path)
