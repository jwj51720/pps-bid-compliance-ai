from __future__ import annotations

from src.evaluate import evaluate_submission, evidence_overlap
from src.pipeline import judgment_to_row
from src.schema import ITEMS
from src.submission import write_submission


def _record() -> dict:
    return {
        "id": "PPS-DEV",
        "docs": [{"doc_id": "D0", "type": "공고문", "text": "앞 서울특별시 업체로 제한 뒤"}],
        "meta": {},
        "dropped_doc_counts": {},
        "input_completeness": {"fully_observed": True},
        "anon_applied": True,
        "assembly_policy_version": "test",
    }


def _row(evidence: str) -> dict:
    judgment = {item: {"위반여부": 0, "근거문구": ""} for item in ITEMS}
    judgment["v1"] = {"위반여부": 1, "근거문구": evidence}
    return judgment_to_row("PPS-DEV", judgment)


def test_evidence_overlap_penalizes_short_span() -> None:
    precision, recall, f1 = evidence_overlap(
        "서울특별시 업체로 제한",
        "서울특별시 업체로 제한",
        "서울특별시",
    )
    assert precision == 1.0
    assert 0 < recall < 1
    assert recall < f1 < 1


def test_evaluate_perfect_prediction(tmp_path) -> None:
    prediction = tmp_path / "prediction.csv"
    labels = tmp_path / "labels.csv"
    row = _row("서울특별시 업체로 제한")
    write_submission([row], prediction)
    write_submission([row], labels)
    metrics, per_item, errors = evaluate_submission(prediction, labels, [_record()])
    assert metrics["leaderboard_metric"]["macro_f1"] == 1 / 24
    assert metrics["evidence"]["validity"] == 1.0
    assert metrics["evidence"]["span_f1"] == 1.0
    assert per_item[0]["f1"] == 1.0
    assert not errors


def test_evaluate_allows_label_superset_for_limited_run(tmp_path) -> None:
    prediction = tmp_path / "prediction.csv"
    labels = tmp_path / "labels.csv"
    row = _row("서울특별시 업체로 제한")
    extra = dict(row)
    extra["id"] = "PPS-OTHER"
    write_submission([row], prediction)
    write_submission([row, extra], labels)
    metrics, _, _ = evaluate_submission(prediction, labels, [_record()])
    assert metrics["leaderboard_metric"]["macro_f1"] == 1 / 24
