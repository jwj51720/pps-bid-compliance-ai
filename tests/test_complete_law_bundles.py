from scripts.build_four_profile_group_complete_law_bundles import normalize_official_text
from scripts.build_routed_law_bundles import _chunks


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
