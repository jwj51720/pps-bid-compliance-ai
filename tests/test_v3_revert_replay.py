"""S005 one-owner ablation tests."""

from __future__ import annotations

from src.pps_ai.v3_revert_replay import replace_v3_only


def test_replace_v3_only_preserves_every_other_cell() -> None:
    integrated = {"N": {"id": "N", "v2": 1, "e2": "a", "v3": 1, "e3": "b", "v19": 1}}
    reference = {"N": {"id": "N", "v2": 0, "e2": "x", "v3": 0, "e3": "", "v19": 0}}
    output, changes = replace_v3_only(integrated, reference)
    assert output["N"] == {"id": "N", "v2": 1, "e2": "a", "v3": 0, "e3": "", "v19": 1}
    assert {(row["field"], row["before"], row["after"]) for row in changes} == {
        ("v3", 1, 0), ("e3", "b", ""),
    }
