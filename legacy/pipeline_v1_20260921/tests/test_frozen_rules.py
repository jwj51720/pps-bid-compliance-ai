from src.frozen_rules import apply_exp123_frozen_rules


def _record() -> dict:
    return {
        "meta": {
            "입찰추정가격": "100000000",
            "업무구분": "용역",
            "배정예산금액": "100000000",
            "적용계약법": "지방계약법",
            "공동도급구성방식": "공동이행",
        },
        "docs": [{
            "text": (
                "입찰참가자격은 최근 실적이 있는 업체이어야 하며 300,000,000원 이상입니다\n"
                "계약참여 지분율은 3% 이상으로 합니다"
            )
        }],
    }


def test_exp123_frozen_rules_replace_only_its_three_items() -> None:
    base = {f"v{index}": {"위반여부": 0, "근거문구": None} for index in range(1, 25)}
    base["v1"] = {"위반여부": 1, "근거문구": "기존 근거"}
    result = apply_exp123_frozen_rules(_record(), base)
    assert result["v1"] == base["v1"]
    assert result["v2"]["위반여부"] == 1
    assert result["v3"]["위반여부"] == 1
    assert result["v21"]["위반여부"] == 1
