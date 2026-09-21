#!/usr/bin/env python3
"""Score saved V-only draft stages without making new provider calls."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Callable


ITEMS = tuple(f"v{i}" for i in range(1, 25))


def _read_labels(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {row["id"]: row for row in csv.DictReader(handle)}


def _read_predictions(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _score(
    rows: list[dict[str, Any]],
    labels: dict[str, dict[str, str]],
    extractor: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    per_item: list[dict[str, Any]] = []
    for item in ITEMS:
        true_positive = false_positive = false_negative = 0
        for row in rows:
            record_id = row["id"]
            value = int(extractor(row)[item]["위반여부"])
            gold = int(labels[record_id][item])
            true_positive += int(gold == 1 and value == 1)
            false_positive += int(gold == 0 and value == 1)
            false_negative += int(gold == 1 and value == 0)
        denominator = 2 * true_positive + false_positive + false_negative
        f1 = 2 * true_positive / denominator if denominator else 0.0
        per_item.append(
            {
                "item": item,
                "true_positive": true_positive,
                "false_positive": false_positive,
                "false_negative": false_negative,
                "f1": f1,
            }
        )
    return {
        "macro_positive_f1": sum(item["f1"] for item in per_item) / len(ITEMS),
        "predicted_positive": sum(
            int(extractor(row)[item]["위반여부"])
            for row in rows
            for item in ITEMS
        ),
        "per_item": per_item,
    }


def analyze_run(run_dir: Path, labels: dict[str, dict[str, str]]) -> dict[str, Any]:
    rows = _read_predictions(run_dir / "predictions.jsonl")
    if not rows:
        raise ValueError(f"no predictions: {run_dir}")
    mode = rows[0].get("staged_run", {}).get("mode")
    stages: dict[str, Any] = {}
    if mode == "vonly_draft_full_final_v1":
        stages["draft_1"] = _score(
            rows,
            labels,
            lambda row: row["staged_run"]["vonly_draft"]["judgment"],
        )
    elif mode == "vonly_consensus_full_source_v1":
        draft_count = len(rows[0]["staged_run"]["vonly_drafts"])
        for index in range(draft_count):
            stages[f"draft_{index + 1}"] = _score(
                rows,
                labels,
                lambda row, index=index: row["staged_run"]["vonly_drafts"][index][
                    "judgment"
                ],
            )
    else:
        raise ValueError(f"unsupported staged V-only mode {mode!r}: {run_dir}")
    stages["final"] = _score(rows, labels, lambda row: row["judgment"])
    return {
        "run_dir": str(run_dir),
        "mode": mode,
        "record_count": len(rows),
        "stages": stages,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    labels = _read_labels(args.labels)
    payload = {
        "method": "score saved model-owned V-only drafts; no provider call or label merge",
        "labels": str(args.labels),
        "runs": [analyze_run(run_dir, labels) for run_dir in args.run_dir],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
