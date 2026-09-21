from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from src.pps_ai.assembly import FINAL_OWNERS, validate_owner_matrix
from src.pps_ai.config import load_experiment_config
from src.pps_ai.domain import NoticeDocument, SourceSpan
from src.pps_ai.evidence import clean_final_rows
from src.pps_ai.runtime.openrouter import OpenRouterRuntime
from src.pps_ai.runtime.recovery import response_is_usable, write_attempt


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "experiments/manifests/reference_l41_openrouter_dev200_v1.json"


def test_clean_manifest_is_resolved_and_hash_pinned() -> None:
    config = load_experiment_config(MANIFEST, ROOT)
    assert config.raw["base_config"] is None
    assert config.reference_zip_sha256 == "a06feff77ffbc4a6f2a47cd0e2d322f341f652ca865d1b9cf53919012c8ca216"
    assert config.provider.max_tokens == 1536
    assert config.prompt_budget == 14848


def test_owner_matrix_covers_each_item_once() -> None:
    validate_owner_matrix()
    assert list(sorted(FINAL_OWNERS, key=lambda item: int(item[1:]))) == [f"v{i}" for i in range(1, 25)]


def test_source_span_round_trip() -> None:
    document = NoticeDocument.from_raw("N1", 0, {"doc_id": "D1", "type": "공고문", "text": "가나다라마바사"})
    span = SourceSpan("N1", "D1", "공고문", 0, 1, 4, "나다라", document.sha256)
    span.validate(document)
    with pytest.raises(ValueError, match="exact document substring"):
        SourceSpan("N1", "D1", "공고문", 0, 1, 4, "틀림", document.sha256).validate(document)


def test_evidence_cleaner_never_mutates_labels() -> None:
    record = {"id": "N1", "docs": [{"text": "원문 근거"}]}
    candidate = {"N1": {"id": "N1"}}
    for index in range(1, 25):
        candidate["N1"][f"v{index}"] = int(index in (1, 10))
        candidate["N1"][f"e{index}"] = "없는 근거" if index == 1 else ""
    rows, report = clean_final_rows([record], candidate)
    assert rows[0]["v1"] == 1
    assert rows[0]["e1"] == ""
    assert rows[0]["v10"] == 1
    assert rows[0]["e10"] == ""
    assert report["label_mutations"] == 0


def test_clean_package_has_no_legacy_src_imports() -> None:
    violations = []
    for path in (ROOT / "src/pps_ai").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            if any(name == "legacy" or name.startswith("legacy.") for name in names):
                violations.append(str(path.relative_to(ROOT)))
    assert violations == []


def test_pytest_does_not_collect_legacy_suite() -> None:
    pytest_config = (ROOT / "pytest.ini").read_text(encoding="utf-8")
    assert "testpaths = tests" in pytest_config
    assert "norecursedirs = legacy" in pytest_config


def test_manifest_declares_all_layers() -> None:
    raw = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert set(raw["layers"]) == {
        "ingest", "source_ledger", "facts", "views", "retrieval",
        "decisions", "assembly", "evidence", "export",
    }


def test_openrouter_retries_in_flight_budget_402(monkeypatch: pytest.MonkeyPatch) -> None:
    config = load_experiment_config(MANIFEST, ROOT)

    class Response:
        def __init__(self, status: int) -> None:
            self.status_code = status
            self.ok = status == 200
            self.headers = {"Retry-After": "120"}
            self.text = (
                '{"error":{"metadata":{"reason":"in_flight_budget_exhausted"}}}'
                if status == 402 else ""
            )

        def json(self) -> dict[str, object]:
            return {
                "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
                "model": "test", "usage": {},
            }

    responses = iter([Response(402), Response(200)])
    monkeypatch.setattr("src.pps_ai.runtime.openrouter.requests.post", lambda *args, **kwargs: next(responses))
    monkeypatch.setattr("src.pps_ai.runtime.openrouter.time.sleep", lambda seconds: None)
    runtime = OpenRouterRuntime(config.provider, "not-a-real-key")
    result = runtime.complete({"arm": "B", "messages": [], "schema": {"type": "object", "properties": {}}})
    assert result["attempts"] == 2
    assert result["finish_reason"] == "stop"


def test_openrouter_uses_enforced_completion_limit_field() -> None:
    config = load_experiment_config(MANIFEST, ROOT)
    runtime = OpenRouterRuntime(config.provider, "not-a-real-key")
    payload = runtime.request_payload({
        "arm": "B", "messages": [],
        "schema": {"type": "object", "properties": {}},
    })
    assert payload["max_completion_tokens"] == 1536
    assert "max_tokens" not in payload


def test_response_recovery_rejects_length_and_malformed() -> None:
    assert response_is_usable({
        "finish_reason": "stop", "invalid": False, "content": '{"v24": {}}',
    })
    assert not response_is_usable({
        "finish_reason": "length", "invalid": False, "content": '{"v24":',
    })
    assert not response_is_usable({
        "finish_reason": "stop", "invalid": False, "content": "not-json",
    })


def test_attempt_ledger_is_append_only(tmp_path: Path) -> None:
    response = {"finish_reason": "stop", "invalid": False, "content": "{}"}
    path = write_attempt(tmp_path, "C24", "N1", 1, response)
    assert json.loads(path.read_text(encoding="utf-8")) == response
    with pytest.raises(FileExistsError, match="already exists"):
        write_attempt(tmp_path, "C24", "N1", 1, response)
