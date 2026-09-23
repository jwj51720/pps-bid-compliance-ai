from __future__ import annotations

from src.pps_ai.base_repeat_panel import compare_prediction_rows


def _row(notice_id: str, *, v1: int, e1: str = "") -> dict[str, object]:
    row: dict[str, object] = {"id": notice_id}
    for index in range(1, 25):
        row[f"v{index}"] = v1 if index == 1 else 0
    for index in range(1, 25):
        row[f"e{index}"] = e1 if index == 1 else ""
    return row


def test_compare_prediction_rows_separates_accuracy_and_evidence_changes() -> None:
    before = {
        "N1": _row("N1", v1=0, e1="before"),
        "N2": _row("N2", v1=1),
    }
    after = {
        "N1": _row("N1", v1=1, e1="after"),
        "N2": _row("N2", v1=0),
    }
    labels = {
        "N1": {f"v{index}": int(index == 1) for index in range(1, 25)},
        "N2": {f"v{index}": int(index == 1) for index in range(1, 25)},
    }
    report = compare_prediction_rows(before, after, labels)
    assert report["label_changed_cells"] == 2
    assert report["evidence_changed_cells"] == 1
    assert report["direction_counts"] == {
        "correct_to_wrong": 1,
        "wrong_to_correct": 1,
        "wrong_to_different_wrong": 0,
    }


def test_compare_prediction_rows_rejects_misaligned_ids() -> None:
    before = {"N1": _row("N1", v1=0)}
    after = {"N2": _row("N2", v1=0)}
    labels = {"N1": {f"v{index}": 0 for index in range(1, 25)}}
    try:
        compare_prediction_rows(before, after, labels)
    except ValueError as error:
        assert "coverage differs" in str(error)
    else:
        raise AssertionError("misaligned IDs must fail")
