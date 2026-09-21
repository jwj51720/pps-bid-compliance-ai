from scripts.build_input_truthful_cards_v1 import REPLACEMENTS, build


def test_input_truthful_card_derivative_replaces_only_declared_cards() -> None:
    payload = build()
    assert payload["artifact"] == "decision_cards_v6_input_truthful_v1"
    assert payload["input_truthful_replacements"] == sorted(REPLACEMENTS)
    for item, text in REPLACEMENTS.items():
        assert payload["cards"][item]["prompt_text"] == text
        assert "제공된 경쟁제품 조회" not in text
        assert "제공된 조회상" not in text
