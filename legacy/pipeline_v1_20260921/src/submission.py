"""Submission CSV construction and competition-format validation."""

from __future__ import annotations

import csv
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.data import full_document_text
from src.pipeline import Prediction, judgment_to_row
from src.schema import ABSENCE_ITEMS, EVIDENCE_MAX_CHARS, ITEMS, SUBMISSION_COLUMNS


@dataclass(frozen=True)
class ValidationResult:
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.errors


def prediction_rows(predictions: list[Prediction]) -> list[dict[str, Any]]:
    return [judgment_to_row(prediction.record_id, prediction.judgment) for prediction in predictions]


def write_submission(rows: list[dict[str, Any]], path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUBMISSION_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def validate_submission(
    path: str | Path,
    records: list[dict[str, Any]],
) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != SUBMISSION_COLUMNS:
            return ValidationResult(("submission columns or order do not match the 49-column schema",), ())
        rows = list(reader)
    expected_ids = [record["id"] for record in records]
    actual_ids = [row["id"] for row in rows]
    if len(rows) != len(records):
        errors.append(f"row count {len(rows)} does not match input count {len(records)}")
    if actual_ids != expected_ids:
        errors.append("submission IDs or row order do not match the input")
    if len(actual_ids) != len(set(actual_ids)):
        errors.append("submission contains duplicate IDs")

    records_by_id = {record["id"]: record for record in records}
    for row in rows:
        record = records_by_id.get(row["id"])
        source = full_document_text(record) if record else ""
        for index, item in enumerate(ITEMS, 1):
            raw_violation = row[item]
            if raw_violation not in {"0", "1"}:
                errors.append(f"{row['id']} {item}: value must be 0 or 1")
                continue
            evidence = row[f"e{index}"]
            if unicodedata.normalize("NFC", evidence) != evidence:
                errors.append(f"{row['id']} e{index}: evidence is not NFC")
            if len(evidence) > EVIDENCE_MAX_CHARS:
                errors.append(f"{row['id']} e{index}: evidence exceeds 500 characters")
            if evidence.startswith(("=", "+", "@")):
                errors.append(f"{row['id']} e{index}: unsafe CSV formula prefix")
            if (raw_violation == "0" or item in ABSENCE_ITEMS) and evidence:
                errors.append(f"{row['id']} e{index}: evidence must be blank")
            if evidence and evidence not in source:
                errors.append(f"{row['id']} e{index}: evidence is not an exact source substring")
            if raw_violation == "1" and item not in ABSENCE_ITEMS and not evidence:
                warnings.append(f"{row['id']} e{index}: positive prediction has no valid evidence")
    return ValidationResult(tuple(errors), tuple(warnings))
