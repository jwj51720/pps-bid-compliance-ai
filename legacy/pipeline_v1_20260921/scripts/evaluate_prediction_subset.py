#!/usr/bin/env python3
"""Evaluate the leading local subset from a completed prediction checkpoint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data import load_records
from src.evaluate import evaluate_submission, write_rows
from src.submission import validate_submission, write_submission


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", default="data/raw/open/dev.jsonl.gz")
    parser.add_argument("--labels", default="data/raw/open/dev_labels.csv")
    parser.add_argument(
        "--predictions", default="outputs/exp-001-first-submission/predictions.jsonl"
    )
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--ids-file", help="JSON string list, or object with an ids list")
    parser.add_argument("--output-dir", default="outputs/exp-001-context20-4000-reference")
    args = parser.parse_args()
    if args.limit < 1:
        raise ValueError("--limit must be positive")

    records = load_records(args.records)
    if args.ids_file:
        selection = json.loads(Path(args.ids_file).read_text(encoding="utf-8"))
        selected_ids = selection.get("ids") if isinstance(selection, dict) else selection
        if not isinstance(selected_ids, list) or not selected_ids or not all(
            isinstance(record_id, str) for record_id in selected_ids
        ):
            raise ValueError("--ids-file must contain a non-empty JSON string list or {ids: [...]}")
        records_by_id = {record["id"]: record for record in records}
        missing_ids = [record_id for record_id in selected_ids if record_id not in records_by_id]
        if missing_ids:
            raise ValueError(f"--ids-file includes absent records: {missing_ids[:10]}")
        records = [records_by_id[record_id] for record_id in selected_ids]
    else:
        records = records[: args.limit]
    predictions = {
        value["id"]: value
        for value in (
            json.loads(line)
            for line in Path(args.predictions).read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    missing = [record["id"] for record in records if record["id"] not in predictions]
    if missing:
        raise ValueError(f"predictions missing records: {missing[:10]}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = [predictions[record["id"]]["row"] for record in records]
    submission_path = output_dir / "submission.csv"
    write_submission(rows, submission_path)
    validation = validate_submission(submission_path, records)
    if not validation.passed:
        raise RuntimeError(f"invalid subset submission: {validation.errors[:5]}")
    metrics, per_item, errors = evaluate_submission(submission_path, args.labels, records)
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_rows(output_dir / "per_item_metrics.csv", per_item)
    write_rows(output_dir / "errors.csv", errors)
    (output_dir / "source.json").write_text(
        json.dumps(
            {
                "prediction_checkpoint": args.predictions,
                "record_count": len(records),
                "record_ids": [record["id"] for record in records],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(output_dir / "metrics.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
