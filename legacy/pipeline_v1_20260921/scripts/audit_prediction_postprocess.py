#!/usr/bin/env python3
"""Expose model-owned versus configured-postprocess labels in saved predictions."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.pipeline import _combine_pass_judgments
from src.schema import ITEMS


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def model_judgment_from_saved(
    row: dict[str, Any], absence_detection_strategy: str
) -> dict[str, dict[str, Any]]:
    provenance = row.get("decision_provenance")
    if isinstance(provenance, dict) and isinstance(provenance.get("model_judgment"), dict):
        return provenance["model_judgment"]
    passes = row.get("pass_judgments")
    if not isinstance(passes, list) or not passes:
        raise ValueError(
            f"{row.get('id')}: no decision provenance or pass judgments; "
            "cannot reconstruct pre-postprocess labels"
        )
    return _combine_pass_judgments(
        passes,
        absence_detection_strategy=absence_detection_strategy,
        items=ITEMS,
    )


def _counts(gold: list[int], predicted: list[int]) -> dict[str, int | float]:
    tp = sum(g == 1 and p == 1 for g, p in zip(gold, predicted))
    fp = sum(g == 0 and p == 1 for g, p in zip(gold, predicted))
    fn = sum(g == 1 and p == 0 for g, p in zip(gold, predicted))
    denominator = 2 * tp + fp + fn
    return {"tp": tp, "fp": fp, "fn": fn, "f1": 2 * tp / denominator if denominator else 0.0}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    config = load_config(args.config)
    predictions = _read_jsonl(Path(args.predictions))
    labels: dict[str, dict[str, str]] = {}
    if config.data.labels_path:
        with config.data.labels_path.open(encoding="utf-8", newline="") as handle:
            labels = {row["id"]: row for row in csv.DictReader(handle)}

    rows = []
    for prediction in predictions:
        model = model_judgment_from_saved(
            prediction, config.absence_detection_strategy
        )
        final = prediction["judgment"]
        changes = [
            {
                "item": item,
                "model": int(model[item]["위반여부"]),
                "final": int(final[item]["위반여부"]),
                "label_changed": (
                    int(model[item]["위반여부"])
                    != int(final[item]["위반여부"])
                ),
                "evidence_changed": (
                    str(model[item].get("근거문구") or "")
                    != str(final[item].get("근거문구") or "")
                ),
            }
            for item in ITEMS
            if int(model[item]["위반여부"]) != int(final[item]["위반여부"])
            or str(model[item].get("근거문구") or "")
            != str(final[item].get("근거문구") or "")
        ]
        rows.append({"id": prediction["id"], "changes": changes, "model": model, "final": final})

    metrics: dict[str, Any] | None = None
    if labels:
        if any(row["id"] not in labels for row in rows):
            raise ValueError("labels do not cover every saved prediction ID")
        per_item = []
        for item in ITEMS:
            gold = [int(labels[row["id"]][item]) for row in rows]
            model_values = [int(row["model"][item]["위반여부"]) for row in rows]
            final_values = [int(row["final"][item]["위반여부"]) for row in rows]
            per_item.append({
                "item": item,
                "model": _counts(gold, model_values),
                "final": _counts(gold, final_values),
            })
        metrics = {
            "model_macro_f1": sum(row["model"]["f1"] for row in per_item) / len(ITEMS),
            "final_macro_f1": sum(row["final"]["f1"] for row in per_item) / len(ITEMS),
            "per_item": per_item,
        }

    result = {
        "config": str(config.path.relative_to(ROOT)),
        "predictions": args.predictions,
        "method": "saved decision provenance or pass-merge reconstruction; no provider calls",
        "configured_postprocess": config.frozen_rule_set,
        "record_count": len(rows),
        "changed_record_count": sum(bool(row["changes"]) for row in rows),
        "changed_item_count": sum(len(row["changes"]) for row in rows),
        "changed_label_cell_count": sum(
            int(change["label_changed"])
            for row in rows for change in row["changes"]
        ),
        "changed_evidence_cell_count": sum(
            int(change["evidence_changed"])
            for row in rows for change in row["changes"]
        ),
        "metrics": metrics,
        "records": [{"id": row["id"], "changes": row["changes"]} for row in rows if row["changes"]],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "records"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
