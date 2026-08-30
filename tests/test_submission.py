from __future__ import annotations

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
