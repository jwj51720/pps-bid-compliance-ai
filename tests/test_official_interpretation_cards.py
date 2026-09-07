import hashlib
import json

from scripts.build_official_interpretation_cards import BASE, UPDATES, build


def test_official_interpretation_candidate_changes_only_declared_cards():
    base = json.loads(BASE.read_text(encoding="utf-8"))
    candidate = build()
    assert candidate["changed_items"] == ["v13", "v9"]
    assert candidate["base_card_sha256"] == hashlib.sha256(BASE.read_bytes()).hexdigest()
    for item, card in base["cards"].items():
        if item in UPDATES:
            assert candidate["cards"][item]["prompt_text"] == UPDATES[item]
        else:
            assert candidate["cards"][item]["prompt_text"] == card["prompt_text"]
