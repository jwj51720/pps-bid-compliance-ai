from scripts.build_four_profile_group_complete_law_bundles import normalize_official_text
from scripts.build_routed_law_bundles import ITEM_KEYS, _chunks


def test_normalization_preserves_v23_period_conditions() -> None:
    text = normalize_official_text(_chunks()["local_award_ch7_s3"].text)

    assert "추정가격 10억원 이상인 경우 40일" in text
    assert "추정가격 10억원 미만 1억원 이상인 경우 20일" in text
    assert "추정가격 1억원 미만인 경우 10일" in text
    assert "긴급을 요하거나 재공고입찰인 경우" in text


def test_normalization_preserves_sw_amount_table() -> None:
    text = normalize_official_text(_chunks()["sw_guideline_appendix_1"].text)

    assert "80억원 이상" in text
    assert "40억원 이상" in text
    assert "20억원 이상" in text


def test_v11_and_v13_audit_sources_include_their_material_exceptions() -> None:
    chunks = _chunks()

    assert "sme_decree_7" in ITEM_KEYS["national"]["v11"]
    assert "sme_decree_7" in ITEM_KEYS["local"]["v11"]
    assert "sme_law_7조의2" in ITEM_KEYS["national"]["v13"]
    assert "sme_law_7조의2" in ITEM_KEYS["local"]["v13"]
    assert "특정한 기술ㆍ용역이 필요한 경우" in chunks["sme_decree_7"].text
    assert "셋 이상의 소기업 또는 소상공인이 조합과 함께" in chunks["sme_law_7조의2"].text


def test_full_card_audit_routes_threshold_and_direct_production_sources() -> None:
    chunks = _chunks()

    assert "national_rule_24" in chunks
    assert "sme_decree_10" in chunks
    for profile in ("national", "local"):
        assert "price_notice" in ITEM_KEYS[profile]["v2"]
        for item in ("v5", "v6", "v7"):
            assert "price_notice" in ITEM_KEYS[profile][item]
        for item in ("v10", "v12"):
            assert "sme_decree_10" in ITEM_KEYS[profile][item]
        for item in ("v14", "v15", "v16", "v17", "v18"):
            assert "price_notice" in ITEM_KEYS[profile][item]

    assert "전문공사는 제외한다" in chunks["national_rule_24"].text
    assert "추정가격 1천만원" in chunks["sme_decree_10"].text
