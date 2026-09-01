from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

from src.pipeline import judgment_to_row
from src.schema import ITEMS
from src.submission import validate_submission, write_submission


def _record() -> dict:
    return {
        "id": "PPS-TEST",
        "docs": [{"doc_id": "D0", "type": "공고문", "text": "원문 근거 문장"}],
        "meta": {},
        "dropped_doc_counts": {},
        "input_completeness": {"fully_observed": True},
        "anon_applied": True,
        "assembly_policy_version": "test",
    }


def _row() -> dict:
    judgment = {item: {"위반여부": 0, "근거문구": ""} for item in ITEMS}
    judgment["v1"] = {"위반여부": 1, "근거문구": "원문 근거"}
    return judgment_to_row("PPS-TEST", judgment)


def test_valid_submission_passes(tmp_path) -> None:
    path = tmp_path / "submission.csv"
    write_submission([_row()], path)
    result = validate_submission(path, [_record()])
    assert result.passed
    assert not result.warnings


def test_non_source_evidence_fails(tmp_path) -> None:
    row = _row()
    row["e1"] = "요약된 근거"
    path = tmp_path / "submission.csv"
    write_submission([row], path)
    result = validate_submission(path, [_record()])
    assert not result.passed
    assert any("exact source substring" in error for error in result.errors)


def test_submission_retries_a_malformed_structured_candidate() -> None:
    script_path = Path(__file__).resolve().parents[1] / "submission" / "script.py"
    spec = importlib.util.spec_from_file_location("submission_script_for_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    valid = json.dumps(
        {item: {"위반여부": 0, "근거문구": None} for item in ITEMS},
        ensure_ascii=False,
    )

    class Client:
        def complete_batch(self, batch, response_schema):
            del response_schema
            return [module.Completion("not JSON", "test", 0.0, {}) for _ in batch]

        def complete(self, messages, response_schema):
            del messages, response_schema
            return module.Completion(valid, "test", 0.0, {})

    outputs, retries = module._complete_group_with_json_retries(
        Client(), [[{"role": "user", "content": "공고"}]], {}
    )

    assert retries == 1
    assert outputs[0].content == valid


def test_submission_mock_client_has_a_full_split_admission_counter() -> None:
    script_path = Path(__file__).resolve().parents[1] / "submission" / "script.py"
    spec = importlib.util.spec_from_file_location("submission_script_mock_counter", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    assert module.MockClient().count_tokens([{"content": "가나다"}]) == 3
