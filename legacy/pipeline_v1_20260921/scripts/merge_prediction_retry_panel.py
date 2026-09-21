#!/usr/bin/env python3
"""Overlay a versioned retry panel onto a full run and recompute artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data import load_record_id_panel, load_records
from src.evaluate import evaluate_submission, write_rows
from src.pipeline import judgment_to_row
from src.submission import validate_submission, write_submission


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _unique_by_id(rows: list[dict[str, Any]], name: str) -> dict[str, dict[str, Any]]:
    result = {str(row["id"]): row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"{name} contains duplicate IDs")
    return result


def merge_predictions(
    base: list[dict[str, Any]],
    retry: list[dict[str, Any]],
    expected_retry_ids: list[str],
) -> list[dict[str, Any]]:
    base_by_id = _unique_by_id(base, "base predictions")
    retry_by_id = _unique_by_id(retry, "retry predictions")
    if set(retry_by_id) != set(expected_retry_ids):
        raise ValueError("retry predictions do not exactly match the versioned panel")
    if not set(retry_by_id) <= set(base_by_id):
        raise ValueError("retry panel contains IDs absent from the full base run")
    return [retry_by_id.get(str(row["id"]), row) for row in base]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-predictions", required=True)
    parser.add_argument("--retry-predictions", required=True)
    parser.add_argument("--retry-ids", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    base_path = Path(args.base_predictions)
    retry_path = Path(args.retry_predictions)
    retry_ids_path = Path(args.retry_ids)
    input_path = Path(args.input)
    labels_path = Path(args.labels)
    output_dir = Path(args.output_dir)
    if output_dir.exists():
        raise ValueError(f"refusing to overwrite existing output directory: {output_dir}")

    expected_retry_ids = load_record_id_panel(retry_ids_path)
    merged = merge_predictions(
        _read_jsonl(base_path),
        _read_jsonl(retry_path),
        expected_retry_ids,
    )
    records = load_records(input_path)
    merged_by_id = _unique_by_id(merged, "merged predictions")
    input_ids = [record["id"] for record in records]
    if set(merged_by_id) != set(input_ids):
        raise ValueError("merged predictions do not exactly match full input IDs")
    # Concurrent experiment checkpoints are completion-ordered. Canonicalize
    # the repaired artifact to organizer input order before CSV validation.
    merged = [merged_by_id[record_id] for record_id in input_ids]

    output_dir.mkdir(parents=True)
    predictions_path = output_dir / "predictions.jsonl"
    predictions_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in merged),
        encoding="utf-8",
    )
    submission_path = output_dir / "submission.csv"
    write_submission(
        [judgment_to_row(row["id"], row["judgment"]) for row in merged],
        submission_path,
    )
    validation = validate_submission(submission_path, records)
    (output_dir / "validation.json").write_text(
        json.dumps(
            {
                "passed": validation.passed,
                "errors": list(validation.errors),
                "warnings": list(validation.warnings),
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    if not validation.passed:
        raise ValueError(f"merged submission validation failed: {validation.errors}")

    metrics, per_item, errors = evaluate_submission(
        submission_path, labels_path, records
    )
    result_metrics = {
        "experiment_id": "exp-200-corrected-input-source-first-dev200-repaired",
        **metrics,
    }
    (output_dir / "metrics.json").write_text(
        json.dumps(result_metrics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_rows(output_dir / "per_item_metrics.csv", per_item)
    write_rows(output_dir / "errors.csv", errors)
    manifest = {
        "method": "exact-ID overlay of versioned recovery panel; no label-based row selection",
        "base_predictions": str(base_path),
        "base_predictions_sha256": _sha256(base_path),
        "retry_predictions": str(retry_path),
        "retry_predictions_sha256": _sha256(retry_path),
        "retry_ids": str(retry_ids_path),
        "retry_ids_sha256": _sha256(retry_ids_path),
        "replaced_count": len(expected_retry_ids),
        "replaced_ids": expected_retry_ids,
        "input_sha256": _sha256(input_path),
        "labels_sha256": _sha256(labels_path),
    }
    (output_dir / "merge_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    base_run_meta_path = base_path.parent / "run_meta.json"
    if base_run_meta_path.exists():
        base_run_meta = json.loads(base_run_meta_path.read_text(encoding="utf-8"))
        repaired_run_meta = {
            **base_run_meta,
            "experiment_id": result_metrics["experiment_id"],
            "repair_overlay": manifest,
            "macro_f1": metrics["leaderboard_metric"]["macro_f1"],
            "validation_warning_count": len(validation.warnings),
        }
        (output_dir / "run_meta.json").write_text(
            json.dumps(repaired_run_meta, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps({**result_metrics, "validation_warnings": len(validation.warnings)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
