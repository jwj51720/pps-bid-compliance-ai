from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "submission/integrated/script.py"


def _load_script():
    package_root = str(SCRIPT.parent)
    if package_root not in sys.path:
        sys.path.insert(0, package_root)
    spec = importlib.util.spec_from_file_location("_pps_integrated_submission", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _task(name: str) -> dict:
    return {
        "messages": [{"role": "user", "content": name}],
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["value"],
            "properties": {"value": {"type": "integer", "enum": [0, 1]}},
        },
    }


def test_invalid_task_gets_exactly_two_retries_without_recalling_valid_task() -> None:
    module = _load_script()

    class Backend:
        max_tokens = 1536
        load_seconds = 0.0

        def __init__(self) -> None:
            self.calls = {"good": 0, "bad": 0}

        def count_tokens(self, messages):
            return 1

        def chat(self, batch, schema):
            values = []
            for messages in batch:
                name = messages[0]["content"]
                self.calls[name] += 1
                valid = name == "good" or self.calls[name] == 3
                values.append({
                    "content": json.dumps({"value": 0}) if valid else "",
                    "finish_reason": "stop" if valid else "length",
                    "invalid": not valid,
                    "usage": {},
                })
            return values

    backend = Backend()
    runner = module.ReportingRunner(backend)
    tasks = {"T/good": _task("good"), "T/bad": _task("bad")}
    responses, report = module.infer_tasks(
        tasks,
        runner,
        128,
        lambda key, task, response: module.integration.valid_base_response(task, response),
    )
    assert backend.calls == {"good": 1, "bad": 3}
    assert report == {"attempts": 2, "unresolved": []}
    assert responses["T/good"]["finish_reason"] == "stop"
    assert responses["T/bad"]["finish_reason"] == "stop"


def test_batch_exception_isolates_single_failure() -> None:
    module = _load_script()

    class Backend:
        max_tokens = 1536
        load_seconds = 0.0

        def count_tokens(self, messages):
            return 1

        def chat(self, batch, schema):
            names = [messages[0]["content"] for messages in batch]
            if "bad" in names:
                raise RuntimeError("isolated failure")
            return [{
                "content": json.dumps({"value": 0}),
                "finish_reason": "stop",
                "invalid": False,
                "usage": {},
            } for _ in batch]

    runner = module.ReportingRunner(Backend())
    tasks = {"T/good": _task("good"), "T/bad": _task("bad")}
    responses, report = module.infer_tasks(
        tasks,
        runner,
        128,
        lambda key, task, response: module.integration.valid_base_response(task, response),
    )
    assert responses["T/good"]["finish_reason"] == "stop"
    assert responses["T/bad"]["invalid"] is True
    assert report["attempts"] == 2
    assert report["unresolved"] == ["T/bad"]
    assert runner.stats["T"]["isolated_single_failures"] == 3


def test_archive_contains_no_experiment_attribution_text() -> None:
    source = SCRIPT.read_text(encoding="utf-8").lower()
    forbidden = ("provenance", "frozen l41", "l41_candidate", "l41-derived", "동료", "레퍼런스")
    assert all(value not in source for value in forbidden)
