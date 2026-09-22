from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
PACKAGER_PATH = ROOT / "scripts/package_l41_hardened_submission.py"


def _load_packager():
    spec = importlib.util.spec_from_file_location("l41_packager_test", PACKAGER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_generated_script(tmp_path: Path):
    packager = _load_packager()
    path = tmp_path / "script.py"
    path.write_text(packager.build_script(), encoding="utf-8")
    spec = importlib.util.spec_from_file_location("l41_generated_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_generated_submission_has_runtime_hardening_only() -> None:
    packager = _load_packager()
    reference = packager.load_reference_script()
    candidate = packager.build_script()
    assert candidate != reference
    assert "l41-derived-runtime-hardened-v1" in candidate
    assert "def retry_invalid_responses(" in candidate
    assert "def response_is_structurally_valid(" in candidate
    assert "def _chat_isolated(" in candidate
    assert "temperature=0, seed=SEED, max_tokens=MAX_TOKENS" in candidate


def test_invalid_only_retry_recovers_and_preserves_valid_response(tmp_path: Path) -> None:
    module = _load_generated_script(tmp_path)
    schema = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
    tasks = {
        (arm, rid): {"arm": arm, "id": rid, "messages": [{"role": "user", "content": rid}], "schema": schema}
        for arm in module.pipeline.ARMS for rid in ("A", "B")
    }
    valid = {"content": "{}", "finish_reason": "stop", "usage": {}}
    responses = {key: dict(valid) for key in tasks}
    original = responses["r10", "A"]
    responses["C24", "B"] = {"content": "{", "finish_reason": "length", "usage": {}}

    class Runner:
        def chat(self, batch, _schema):
            return [{"content": "{}", "finish_reason": "stop", "usage": {}} for _ in batch]

    recovered, report = module.retry_invalid_responses(tasks, responses, Runner(), 128)
    assert report["targets"] == ["C24/B"]
    assert report["recovered"] == ["C24/B"]
    assert report["unresolved"] == []
    assert recovered["r10", "A"] is original


def test_batch_exception_is_bisected_without_reordering(tmp_path: Path) -> None:
    module = _load_generated_script(tmp_path)
    schema = {"type": "object"}

    class Runner:
        def count_tokens(self, _messages):
            return 1

        def chat(self, batch, _schema):
            if len(batch) > 1:
                raise RuntimeError("synthetic batch failure")
            value = batch[0][0]["content"]
            return [{"content": json.dumps({"value": value}), "finish_reason": "stop", "usage": {}}]

    measured = module.ReportingRunner(Runner(), {arm: schema for arm in module.pipeline.ARMS})
    batch = [
        [{"role": "user", "content": value}]
        for value in ("a", "b", "c")
    ]
    outputs = measured.chat(batch, schema)
    assert [json.loads(value["content"])["value"] for value in outputs] == ["a", "b", "c"]
    assert measured.stats["r10"]["backend_errors"] >= 1
    assert measured.stats["r10"]["isolated_single_failures"] == 0


def test_no_valid_arm_is_reported_but_does_not_abort(tmp_path: Path) -> None:
    module = _load_generated_script(tmp_path)
    invalid = {"content": "{", "finish_reason": "length", "invalid": False, "usage": {}}
    responses = {(arm, "A"): dict(invalid) for arm in module.pipeline.ARMS}
    assert module.normal_coverage(["A"], responses) == ["A"]


def test_run_level_error_still_writes_complete_emergency_csv(tmp_path: Path) -> None:
    module = _load_generated_script(tmp_path)
    output = tmp_path / "submission.csv"
    report = tmp_path / "report.json"
    record = {
        "id": "NOTICE-1",
        "docs": [{"doc_id": "D0", "type": "공고문", "text": "본문"}],
        "meta": {},
    }
    input_path = tmp_path / "test.jsonl.gz"
    import gzip

    with gzip.open(input_path, "wt", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    args = SimpleNamespace(
        input=str(input_path), output=str(output), report=str(report), limit=None,
    )
    result = module.emergency_submission(args, RuntimeError("synthetic failure"))
    assert result["status"] == "DEGRADED_PASS"
    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert lines[0].split(",") == [
        "id", *[f"v{i}" for i in range(1, 25)], *[f"e{i}" for i in range(1, 25)]
    ]
    assert lines[1].startswith("NOTICE-1," + ",".join(["0"] * 24))


def test_server_mode_requires_all_four_organizer_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_generated_script(tmp_path)
    for name in ("PPS_DATA_DIR", "PPS_OUTPUT_DIR", "PPS_MODEL_DIR", "PPS_EMBED_DIR"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(SystemExit):
        module.arguments([])
