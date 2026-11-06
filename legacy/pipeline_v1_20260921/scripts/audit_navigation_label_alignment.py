#!/usr/bin/env python3
"""Separate source-navigation coverage from final positive-label recall."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_prediction_postprocess import model_judgment_from_saved
from src.config import load_config
from src.schema import ITEMS


def _normalized_span(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", value)).strip()


def navigation_excerpts(prediction: dict[str, Any]) -> list[str]:
    inventory = prediction.get("staged_run", {}).get("inventory", {}).get(
        "by_category"
    )
    if not isinstance(inventory, dict):
        raise ValueError(f"{prediction.get('id')}: saved fact inventory is missing")
    excerpts: list[str] = []
    for values in inventory.values():
        if not isinstance(values, list):
            raise ValueError(f"{prediction.get('id')}: invalid inventory category")
        for value in values:
            if (
                not isinstance(value, list)
                or len(value) != 2
                or not all(isinstance(part, str) for part in value)
            ):
                raise ValueError(f"{prediction.get('id')}: invalid inventory excerpt")
            excerpts.append(value[1])
    return excerpts


def navigation_contains_gold(evidence: str, excerpts: list[str]) -> bool:
    gold = _normalized_span(evidence)
    if not gold:
        return False
    for excerpt in excerpts:
        candidate = _normalized_span(excerpt)
        if candidate and (gold in candidate or candidate in gold):
            return True
    return False


def audit(
    predictions: list[dict[str, Any]],
    labels: list[dict[str, str]],
    absence_detection_strategy: str,
) -> dict[str, Any]:
    prediction_by_id = {row["id"]: row for row in predictions}
    label_ids = [row["id"] for row in labels]
    if len(prediction_by_id) != len(predictions):
        raise ValueError("duplicate prediction IDs")
    if set(prediction_by_id) != set(label_ids) or len(set(label_ids)) != len(labels):
        raise ValueError("prediction and label IDs must join exactly")

    per_item: list[dict[str, Any]] = []
    for item in ITEMS:
        number = item[1:]
        cells: list[dict[str, Any]] = []
        for label in labels:
            if label[item] != "1":
                continue
            prediction = prediction_by_id[label["id"]]
            model = model_judgment_from_saved(
                prediction, absence_detection_strategy
            )
            evidence = label[f"e{number}"]
            nav_hit = (
                navigation_contains_gold(evidence, navigation_excerpts(prediction))
                if evidence else None
            )
            cells.append(
                {
                    "id": label["id"],
                    "gold_evidence_present": bool(evidence),
                    "navigation_hit": nav_hit,
                    "model_label": int(model[item]["위반여부"]),
                    "final_label": int(prediction["judgment"][item]["위반여부"]),
                }
            )
        nonblank = [cell for cell in cells if cell["gold_evidence_present"]]
        blank = [cell for cell in cells if not cell["gold_evidence_present"]]
        per_item.append(
            {
                "item": item,
                "gold_positive": len(cells),
                "nonblank_gold_evidence": len(nonblank),
                "blank_gold_evidence": len(blank),
                "navigation_hit": sum(cell["navigation_hit"] is True for cell in nonblank),
                "navigation_miss": sum(cell["navigation_hit"] is False for cell in nonblank),
                "model_tp_navigation_hit": sum(
                    cell["navigation_hit"] is True and cell["model_label"] == 1
                    for cell in nonblank
                ),
                "model_fn_navigation_hit": sum(
                    cell["navigation_hit"] is True and cell["model_label"] == 0
                    for cell in nonblank
                ),
                "final_tp_navigation_hit": sum(
                    cell["navigation_hit"] is True and cell["final_label"] == 1
                    for cell in nonblank
                ),
                "final_fn_navigation_hit": sum(
                    cell["navigation_hit"] is True and cell["final_label"] == 0
                    for cell in nonblank
                ),
                "final_tp_navigation_miss": sum(
                    cell["navigation_hit"] is False and cell["final_label"] == 1
                    for cell in nonblank
                ),
                "final_fn_navigation_miss": sum(
                    cell["navigation_hit"] is False and cell["final_label"] == 0
                    for cell in nonblank
                ),
                "blank_final_tp": sum(cell["final_label"] == 1 for cell in blank),
                "blank_final_fn": sum(cell["final_label"] == 0 for cell in blank),
                "cells": cells,
            }
        )

    total_keys = (
        "gold_positive", "nonblank_gold_evidence", "blank_gold_evidence",
        "navigation_hit", "navigation_miss", "model_tp_navigation_hit",
        "model_fn_navigation_hit", "final_tp_navigation_hit",
        "final_fn_navigation_hit", "final_tp_navigation_miss",
        "final_fn_navigation_miss", "blank_final_tp", "blank_final_fn",
    )
    totals = {
        key: sum(int(row[key]) for row in per_item)
        for key in total_keys
    }
    totals["navigation_recall_on_nonblank_gold"] = (
        totals["navigation_hit"] / totals["nonblank_gold_evidence"]
        if totals["nonblank_gold_evidence"] else 0.0
    )
    return {
        "method": (
            "whitespace-normalized bidirectional containment between organizer "
            "gold evidence and saved source-only inventory excerpts"
        ),
        "record_count": len(predictions),
        "totals": totals,
        "per_item": per_item,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    config = load_config(args.config)
    predictions = [
        json.loads(line)
        for line in Path(args.predictions).read_text(encoding="utf-8").splitlines()
        if line
    ]
    with Path(args.labels).open(encoding="utf-8", newline="") as handle:
        labels = list(csv.DictReader(handle))
    result = audit(predictions, labels, config.absence_detection_strategy)
    result["config"] = str(Path(args.config))
    result["predictions"] = args.predictions
    result["labels"] = args.labels
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({**result, "per_item": "written to output"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
