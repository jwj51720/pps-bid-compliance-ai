"""Zero-call replay that removes only the S001 v3 specialist owner."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Mapping

from .config import CleanExperimentConfig
from .evaluate import evaluate_rows
from .evidence.validation import clean_final_rows
from .export import write_submission_csv
from .ingest import load_notice_records
from .preflight import compare_manifests
from .runtime.openrouter import atomic_json


def read_submission(path: Path) -> dict[str, dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows: dict[str, dict[str, Any]] = {}
        for source in csv.DictReader(handle):
            row: dict[str, Any] = {"id": source["id"]}
            row.update({f"v{i}": int(source[f"v{i}"]) for i in range(1, 25)})
            row.update({f"e{i}": source[f"e{i}"] for i in range(1, 25)})
            rows[str(row["id"])] = row
    return rows


def replace_v3_only(
    integrated: Mapping[str, Mapping[str, Any]],
    reference: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    if set(integrated) != set(reference):
        raise ValueError("integrated/reference ID coverage differs")
    output = {notice_id: dict(row) for notice_id, row in integrated.items()}
    changes: list[dict[str, Any]] = []
    for notice_id in sorted(output):
        for field in ("v3", "e3"):
            before = output[notice_id][field]
            after = reference[notice_id][field]
            output[notice_id][field] = after
            if before != after:
                changes.append({"id": notice_id, "field": field,
                                "before": before, "after": after})
    return output, changes


def run_v3_revert(config: CleanExperimentConfig) -> dict[str, Any]:
    root = config.path.parents[2]
    manifest = compare_manifests(config.path, root)
    if manifest["status"] != "PASS":
        raise ValueError("manifest policy diff failed")
    integrated_path = root / "outputs/clean-exp-s001-integrated-v3-v19-v1/submission.csv"
    reference_path = root / "outputs/clean-reference-l41-openrouter-dev200-v1/submission.csv"
    integrated = read_submission(integrated_path)
    reference = read_submission(reference_path)
    candidate, changes = replace_v3_only(integrated, reference)
    records = load_notice_records(config.input_path)
    cleaned, evidence = clean_final_rows(
        [dict(record.raw) for record in records], candidate,
    )
    metrics = evaluate_rows(cleaned, config.labels_path, {
        "fast20": config.fast_panel_path,
        "holdout20": config.holdout_panel_path,
    })
    config.output_dir.mkdir(parents=True, exist_ok=True)
    write_submission_csv(config.output_dir / "submission.csv", cleaned)
    atomic_json(config.output_dir / "metrics.json", metrics)
    atomic_json(config.output_dir / "manifest.snapshot.json", config.raw)
    expected = 0.8151465658238104 - (
        0.9411764705882353 - 0.36363636363636365
    ) / 24
    actual = float(metrics["dev200"]["macro_positive_f1"])
    forbidden = [row for row in changes if row["field"] not in {"v3", "e3"}]
    report = {
        "status": "PASS" if abs(actual - expected) < 1e-12 and not forbidden else "FAIL",
        "mode": "zero-call-stored-row-v3-owner-revert",
        "records": len(cleaned), "calls": 0,
        "changed_cells": len(changes), "changes": changes,
        "forbidden_changes": forbidden,
        "expected_macro": expected, "actual_macro": actual,
        "logical_initial_calls_dev200": {"before": 661, "after": 600, "removed": 61},
        "population_projected_removed_v3_calls_for_1853": 1853 * 0.2042,
        "evidence": evidence, "metrics": metrics, "manifest_diff": manifest,
        "limitation": "adaptive-dev stored-row counterfactual; no public or fresh model evidence",
    }
    atomic_json(config.output_dir / "run_report.json", report)
    return report
