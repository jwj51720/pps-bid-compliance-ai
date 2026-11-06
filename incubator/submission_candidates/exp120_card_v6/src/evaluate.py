"""Local classification and evidence metrics for labeled dev submissions."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from src.data import full_document_text
from src.schema import ABSENCE_ITEMS, ITEMS, SUBMISSION_COLUMNS


def _ratio(numerator: int | float, denominator: int | float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _classification_counts(gold: list[int], predicted: list[int]) -> tuple[int, int, int]:
    true_positive = sum(g == 1 and p == 1 for g, p in zip(gold, predicted))
    false_positive = sum(g == 0 and p == 1 for g, p in zip(gold, predicted))
    false_negative = sum(g == 1 and p == 0 for g, p in zip(gold, predicted))
    return true_positive, false_positive, false_negative


def _classification_metrics(gold: list[int], predicted: list[int]) -> dict[str, float | int]:
    true_positive, false_positive, false_negative = _classification_counts(gold, predicted)
    precision = _ratio(true_positive, true_positive + false_positive)
    recall = _ratio(true_positive, true_positive + false_negative)
    f1 = _ratio(2 * precision * recall, precision + recall)
    return {
        "gold_positive": sum(gold),
        "predicted_positive": sum(predicted),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _all_spans(text: str, substring: str) -> list[tuple[int, int]]:
    if not substring:
        return []
    spans: list[tuple[int, int]] = []
    start = 0
    while True:
        index = text.find(substring, start)
        if index < 0:
            return spans
        spans.append((index, index + len(substring)))
        start = index + 1


def evidence_overlap(source: str, gold: str, predicted: str) -> tuple[float, float, float]:
    gold_spans = _all_spans(source, gold)
    predicted_spans = _all_spans(source, predicted)
    if not gold_spans or not predicted_spans:
        return 0.0, 0.0, 0.0
    best = (0.0, 0.0, 0.0)
    for gold_start, gold_end in gold_spans:
        for predicted_start, predicted_end in predicted_spans:
            overlap = max(0, min(gold_end, predicted_end) - max(gold_start, predicted_start))
            precision = _ratio(overlap, predicted_end - predicted_start)
            recall = _ratio(overlap, gold_end - gold_start)
            f1 = _ratio(2 * precision * recall, precision + recall)
            if f1 > best[2]:
                best = (precision, recall, f1)
    return best


def _read_submission(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != SUBMISSION_COLUMNS:
            raise ValueError(f"invalid submission columns: {path}")
        return list(reader)


def evaluate_submission(
    prediction_path: str | Path,
    label_path: str | Path,
    records: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    predicted_rows = _read_submission(prediction_path)
    gold_rows = _read_submission(label_path)
    predicted_by_id = {row["id"]: row for row in predicted_rows}
    gold_by_id = {row["id"]: row for row in gold_rows}
    record_by_id = {record["id"]: record for record in records}
    expected_ids = set(record_by_id)
    if set(predicted_by_id) != expected_ids or not expected_ids <= set(gold_by_id):
        raise ValueError("predictions must match input IDs and labels must cover every input ID")

    per_item: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    validity_values: list[float] = []
    span_precision_values: list[float] = []
    span_recall_values: list[float] = []
    span_f1_values: list[float] = []
    exact_values: list[float] = []
    joint_values: list[float] = []

    ordered_ids = [record["id"] for record in records]
    for index, item in enumerate(ITEMS, 1):
        gold_values = [int(gold_by_id[record_id][item]) for record_id in ordered_ids]
        predicted_values = [int(predicted_by_id[record_id][item]) for record_id in ordered_ids]
        item_metrics = {"item": item, **_classification_metrics(gold_values, predicted_values)}
        item_validity: list[float] = []
        item_span_f1: list[float] = []

        for record_id, gold_v, predicted_v in zip(ordered_ids, gold_values, predicted_values):
            gold_e = gold_by_id[record_id][f"e{index}"]
            predicted_e = predicted_by_id[record_id][f"e{index}"]
            source = full_document_text(record_by_id[record_id])
            evidence_valid = bool(predicted_e) and predicted_e in source
            if predicted_v == 1 and item not in ABSENCE_ITEMS:
                validity = float(evidence_valid)
                validity_values.append(validity)
                item_validity.append(validity)

            span_precision = span_recall = span_f1 = 0.0
            evidence_case = gold_v == 1 and item not in ABSENCE_ITEMS and bool(gold_e)
            if evidence_case:
                span_precision, span_recall, span_f1 = evidence_overlap(source, gold_e, predicted_e)
                span_precision_values.append(span_precision)
                span_recall_values.append(span_recall)
                span_f1_values.append(span_f1)
                exact_values.append(float(gold_e == predicted_e))
                joint_values.append(span_f1 if predicted_v == 1 else 0.0)
                item_span_f1.append(span_f1)

            if gold_v != predicted_v or (evidence_case and span_f1 < 1.0):
                errors.append(
                    {
                        "id": record_id,
                        "item": item,
                        "gold_v": gold_v,
                        "pred_v": predicted_v,
                        "gold_e": gold_e,
                        "pred_e": predicted_e,
                        "evidence_valid": evidence_valid,
                        "evidence_span_f1": span_f1,
                    }
                )

        item_metrics["evidence_validity"] = (
            sum(item_validity) / len(item_validity) if item_validity else None
        )
        item_metrics["evidence_span_f1"] = (
            sum(item_span_f1) / len(item_span_f1) if item_span_f1 else None
        )
        per_item.append(item_metrics)

    macro_f1 = sum(float(row["f1"]) for row in per_item) / len(per_item)
    metrics = {
        "leaderboard_metric": {"macro_f1": macro_f1},
        "evidence": {
            "validity": sum(validity_values) / len(validity_values) if validity_values else None,
            "validity_cases": len(validity_values),
            "span_precision": sum(span_precision_values) / len(span_precision_values)
            if span_precision_values
            else None,
            "span_recall": sum(span_recall_values) / len(span_recall_values)
            if span_recall_values
            else None,
            "span_f1": sum(span_f1_values) / len(span_f1_values) if span_f1_values else None,
            "span_cases": len(span_f1_values),
            "exact_match": sum(exact_values) / len(exact_values) if exact_values else None,
        },
        "joint_positive_quality": sum(joint_values) / len(joint_values) if joint_values else None,
    }
    return metrics, per_item, errors


def write_rows(path: str | Path, rows: list[dict[str, Any]]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        destination.write_text("", encoding="utf-8")
        return
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
