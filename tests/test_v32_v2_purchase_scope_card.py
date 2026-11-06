"""The v32 candidate changes only the v2 prompt contract."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_v32_v2_purchase_scope_card import V2_PROMPT


ROOT = Path(__file__).resolve().parents[1]


def test_v32_changes_only_v2_prompt_text() -> None:
    base = json.loads((ROOT / "data/derived/decision_cards_v31_v4_organizer_definition_resolution.json").read_text(encoding="utf-8"))
    candidate = json.loads((ROOT / "data/derived/decision_cards_v32_v2_purchase_scope.json").read_text(encoding="utf-8"))
    assert set(base) == set(candidate)
    assert candidate["cards"]["v2"]["prompt_text"] == V2_PROMPT
    assert candidate["cards"]["v2"]["prompt_text"] != base["cards"]["v2"]["prompt_text"]
    assert "구매/공급" in V2_PROMPT
    for item in base["cards"]:
        if item != "v2":
            assert candidate["cards"][item] == base["cards"][item]
    old_v2 = {key: value for key, value in base["cards"]["v2"].items() if key != "prompt_text"}
    new_v2 = {key: value for key, value in candidate["cards"]["v2"].items() if key != "prompt_text"}
    assert old_v2 == new_v2
    assert all(candidate[key] == base[key] for key in ("schema_version", "source_item_table", "source_item_table_sha256"))
