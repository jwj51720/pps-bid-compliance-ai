"""Metadata facts are item-scoped, typed, and do not decide labels."""

from __future__ import annotations

import pytest

from src.pps_ai.facts.metadata import (
    ITEM_METADATA_FIELDS,
    build_metadata_facts,
    render_metadata_facts,
)


def test_item_registry_covers_every_v_once() -> None:
    assert set(ITEM_METADATA_FIELDS) == {f"v{index}" for index in range(1, 25)}


def test_money_method_and_date_remain_distinct() -> None:
    meta = {
        "적용계약법": "지방계약법",
        "낙찰방법": "협상에의한계약",
        "입찰추정가격": 123456789,
        "공고게시일자": "20260203",
        "긴급공고여부": "N",
    }
    facts = build_metadata_facts(meta, ["v23"])
    rendered = render_metadata_facts(facts)
    assert "입찰추정가격 입력: 123,456,789원" in rendered
    assert "공고 게시일 입력: 2026-02-03" in rendered
    assert "긴급공고 여부 입력: 아니오" in rendered
    assert "낙찰방식 입력: 협상에의한계약" in rendered
    assert "배정예산금액" not in rendered
    assert "20260203" not in rendered


def test_null_is_unknown_not_negative() -> None:
    facts = build_metadata_facts({"낙찰방법": None}, ["v22"])
    assert len(facts) == 1
    assert facts[0].available is False
    assert "확인되지 않음" in render_metadata_facts(facts)


def test_region_internal_tokens_are_translated_without_inventing_district() -> None:
    value = "[등록지역:r1|단위=기초|광역=경기도], [등록지역:r2|단위=기초|광역=경기도]"
    meta = {field: None for field in ITEM_METADATA_FIELDS["v5"]}
    meta["제한지역코드목록"] = value
    rendered = render_metadata_facts(build_metadata_facts(meta, ["v5"]))
    assert rendered.count("경기도 관할 기초지역") == 2
    assert "세부 시군구 미제공" in rendered
    assert "등록지역:r" not in rendered


def test_industry_names_codes_and_boolean_connectives_remain_paired() -> None:
    meta = {field: None for field in ITEM_METADATA_FIELDS["v24"]}
    meta["면허업종제한목록"] = "[건축사사무소(4817) 과 설계업(1105)]업종 또는[산업디자인(4444)]"
    rendered = render_metadata_facts(build_metadata_facts(meta, ["v24"]))
    assert "건축사사무소" in rendered
    assert " 과 설계업" in rendered
    assert "또는[산업디자인" in rendered
    assert "건축사사무소 [업종식별번호 4817]" in rendered
    assert "설계업 [업종식별번호 1105]" in rendered
    assert "산업디자인 [업종식별번호 4444]" in rendered
    assert "(4817)" not in rendered


def test_missing_field_and_unknown_flag_fail_closed() -> None:
    with pytest.raises(ValueError, match="missing"):
        build_metadata_facts({}, ["v22"])
    with pytest.raises(ValueError, match="unknown flag"):
        build_metadata_facts({"긴급공고여부": "maybe", **{
            field: None for field in ITEM_METADATA_FIELDS["v23"]
            if field != "긴급공고여부"
        }}, ["v23"])
