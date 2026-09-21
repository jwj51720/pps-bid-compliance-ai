from scripts.build_routed_law_bundles import _chunks


def test_v23_uses_chapter_seven_negotiated_contract_section() -> None:
    """The repeated '제3절' heading must not select chapter 10 by accident."""
    text = _chunks()["local_award_ch7_s3"].text

    assert "제안서 제출마감일의 전일부터 기산" in text
    assert "추정가격 10억원 이상인 경우 40일" in text
    assert "추정가격 10억원 미만 1억원 이상인 경우 20일" in text
    assert "추정가격 1억원 미만인 경우 10일" in text
    assert "품질 등 기준으로 구매" not in text
