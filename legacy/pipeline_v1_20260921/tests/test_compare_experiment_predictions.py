from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts.compare_experiment_predictions import compare
from src.schema import ITEMS, SUBMISSION_COLUMNS


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUBMISSION_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _row(record_id: str, **labels: int) -> dict[str, object]:
    row: dict[str, object] = {"id": record_id}
    for index, item in enumerate(ITEMS, 1):
        row[item] = labels.get(item, 0)
        row[f"e{index}"] = ""
    return row


def _write_output(path: Path, row: dict[str, object], f1: dict[str, float]) -> None:
    path.mkdir()
    _write_csv(path / "submission.csv", [row])
    (path / "run_meta.json").write_text(
        json.dumps({
            "input_sha256": "input", "labels_sha256": "labels",
            "input_count": 1, "fast_panel_ids_path": "panel.json",
        }),
        encoding="utf-8",
    )
    macro = sum(f1.get(item, 0.0) for item in ITEMS) / len(ITEMS)
    (path / "metrics.json").write_text(
        json.dumps({"leaderboard_metric": {"macro_f1": macro}}),
        encoding="utf-8",
    )
    with (path / "per_item_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = [
            "item", "true_positive", "false_positive", "false_negative",
            "precision", "recall", "f1",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in ITEMS:
            score = f1.get(item, 0.0)
            writer.writerow({
                "item": item, "true_positive": int(score > 0),
                "false_positive": 0, "false_negative": int(score == 0),
                "precision": score, "recall": score, "f1": score,
            })


def test_compare_separates_focus_and_off_target_drift(tmp_path: Path) -> None:
    base = tmp_path / "base"
    candidate = tmp_path / "candidate"
    labels = tmp_path / "labels.csv"
    _write_output(base, _row("R1"), {})
    _write_output(candidate, _row("R1", v6=1, v23=1), {"v6": 1.0})
    _write_csv(labels, [_row("R1", v6=1)])

    result = compare(base, candidate, labels, ("v6",))

    assert result["focus_changes"] == {
        "changed": 1, "corrected": 1, "regressed": 0,
        "changed_but_still_wrong": 0,
    }
    assert result["off_target_changes"] == {
        "changed": 1, "corrected": 0, "regressed": 1,
        "changed_but_still_wrong": 0,
    }
