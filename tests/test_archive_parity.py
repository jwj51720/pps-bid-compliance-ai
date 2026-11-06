from __future__ import annotations

from src.pps_ai.archive_parity import StoredResponseRunner, _cell_differences, _fingerprint


class Counter:
    def count(self, messages):
        return len(messages)


def test_stored_runner_replays_recovery_then_last_response() -> None:
    messages = [{"role": "user", "content": "x"}]
    schema = {"type": "object"}
    key = _fingerprint(messages, schema)
    runner = StoredResponseRunner(Counter(), {key: [{"content": "bad"}, {"content": "ok"}]})
    assert runner.chat([messages], schema)[0]["content"] == "bad"
    assert runner.chat([messages], schema)[0]["content"] == "ok"
    assert runner.chat([messages], schema)[0]["content"] == "ok"
    assert runner.requests == 3


def test_cell_differences_checks_verdict_and_evidence() -> None:
    left = {"id": "N1"}
    right = {"id": "N1"}
    for index in range(1, 25):
        left[f"v{index}"] = right[f"v{index}"] = 0
        left[f"e{index}"] = right[f"e{index}"] = ""
    right["v3"] = 1
    right["e3"] = "quote"
    differences = _cell_differences([left], [right])
    assert [(item["field"], item["actual"]) for item in differences] == [
        ("v3", "1"), ("e3", "quote"),
    ]
