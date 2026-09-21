from scripts.audit_final_input_value_delivery import _metadata_lines


def test_metadata_lines_preserve_values_and_humanize_only_codes() -> None:
    record = {
        "meta": {
            "적용계약법": "지방계약법",
            "입찰추정가격": 123456789,
            "세부품명번호목록": "잡석[1111169701]",
            "면허업종제한목록": "[학술.연구용역(1169)]",
            "긴급공고여부": None,
        }
    }

    lines = _metadata_lines(record)

    assert lines["적용계약법"] == "- 적용계약법: 지방계약법"
    assert lines["입찰추정가격"] == "- 입찰추정가격: 123456789"
    assert lines["세부품명번호목록"] == "- 세부품명번호목록: 잡석"
    assert lines["면허업종제한목록"] == "- 면허업종제한목록: [학술.연구용역]"
    assert lines["긴급공고여부"] == "- 긴급공고여부: 미기재"
