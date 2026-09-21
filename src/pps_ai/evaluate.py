"""Positive-class macro-F1 evaluation for full and named panels."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable


def _ids(path: Path) -> set[str]:
    return set(json.loads(path.read_text(encoding="utf-8"))["ids"])


def evaluate_rows(
    rows: Iterable[dict[str, Any]], labels_path: Path, panels: dict[str, Path],
) -> dict[str, Any]:
    predictions = {str(row["id"]): row for row in rows}
    with labels_path.open(encoding="utf-8", newline="") as handle:
        labels = {row["id"]: row for row in csv.DictReader(handle)}
    if set(predictions) != set(labels):
        raise ValueError("prediction/label ID coverage differs")
    cohorts = {"dev200": set(labels), **{name: _ids(path) for name, path in panels.items()}}
    results: dict[str, Any] = {}
    for name, ids in cohorts.items():
        if not ids <= set(labels):
            raise ValueError(f"{name}: panel contains unknown IDs")
        per_item: dict[str, Any] = {}
        for index in range(1, 25):
            item = f"v{index}"
            tp = fp = fn = 0
            for notice_id in ids:
                actual = int(labels[notice_id][item])
                predicted = int(predictions[notice_id][item])
                tp += int(actual == 1 and predicted == 1)
                fp += int(actual == 0 and predicted == 1)
                fn += int(actual == 1 and predicted == 0)
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
            per_item[item] = {
                "tp": tp, "fp": fp, "fn": fn,
                "precision": precision, "recall": recall, "f1": f1,
            }
        results[name] = {
            "records": len(ids),
            "macro_positive_f1": sum(value["f1"] for value in per_item.values()) / 24,
            "per_item": per_item,
        }
    return results
