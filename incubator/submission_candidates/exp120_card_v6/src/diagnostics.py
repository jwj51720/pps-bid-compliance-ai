"""Reproducible diagnostics for a completed labeled experiment."""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from typing import Any

from src.data import full_document_text
from src.pipeline import parse_judgment
from src.prompt import build_document_context
from src.schema import ABSENCE_ITEMS, ITEMS


def _f1(gold: list[int], predicted: list[int]) -> float:
    true_positive = sum(g == p == 1 for g, p in zip(gold, predicted))
    false_positive = sum(g == 0 and p == 1 for g, p in zip(gold, predicted))
    false_negative = sum(g == 1 and p == 0 for g, p in zip(gold, predicted))
    denominator = 2 * true_positive + false_positive + false_negative
    return 2 * true_positive / denominator if denominator else 0.0


def diagnose_experiment(
    records: list[dict[str, Any]],
    labels: list[dict[str, str]],
    predictions: list[dict[str, Any]],
    *,
    max_document_chars: int,
    max_completion_tokens: int,
) -> dict[str, Any]:
    """Measure input coverage, output completion, and dominant error modes."""

    records_by_id = {record["id"]: record for record in records}
    labels_by_id = {row["id"]: row for row in labels}
    predictions_by_id = {row["id"]: row for row in predictions}
    expected_ids = set(records_by_id)
    if set(labels_by_id) != expected_ids or set(predictions_by_id) != expected_ids:
        raise ValueError("records, labels, and predictions must contain the same IDs")

    fully_in_budget = 0
    visible_evidence = Counter()
    coverage_by_item: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for record_id, record in records_by_id.items():
        context = build_document_context(record, max_document_chars)
        fully_in_budget += int(all(doc["text"] in context for doc in record["docs"]))
        for index, item in enumerate(ITEMS, 1):
            evidence = labels_by_id[record_id][f"e{index}"]
            if int(labels_by_id[record_id][item]) != 1 or item in ABSENCE_ITEMS or not evidence:
                continue
            in_source = evidence in full_document_text(record)
            in_context = evidence in context
            visible_evidence["total"] += 1
            visible_evidence["in_source"] += int(in_source)
            visible_evidence["in_context"] += int(in_context)
            visible_evidence["true_positive"] += int(
                in_context and predictions_by_id[record_id]["row"][item] == 1
            )
            coverage_by_item[item]["total"] += 1
            coverage_by_item[item]["in_context"] += int(in_context)

    completion_tokens: list[float] = []
    positive_with_valid_evidence = Counter()
    positive_without_valid_evidence = Counter()
    missing_evidence_by_item: Counter[str] = Counter()
    for prediction in predictions:
        completion_tokens.append(float(prediction.get("usage", {}).get("completion_tokens", 0) or 0))
        parsed = parse_judgment(prediction["raw_response"])
        gold = labels_by_id[prediction["id"]]
        for index, item in enumerate(ITEMS, 1):
            if parsed[item]["위반여부"] != 1 or item in ABSENCE_ITEMS:
                continue
            valid = bool(prediction["row"][f"e{index}"])
            bucket = positive_with_valid_evidence if valid else positive_without_valid_evidence
            bucket["count"] += 1
            bucket["true_positive"] += int(gold[item])
            if not valid:
                missing_evidence_by_item[item] += 1

    per_item: list[dict[str, Any]] = []
    for item in ITEMS:
        gold_values = [int(labels_by_id[record["id"]][item]) for record in records]
        predicted_values = [int(predictions_by_id[record["id"]]["row"][item]) for record in records]
        true_positive = sum(g == p == 1 for g, p in zip(gold_values, predicted_values))
        false_positive = sum(g == 0 and p == 1 for g, p in zip(gold_values, predicted_values))
        false_negative = sum(g == 1 and p == 0 for g, p in zip(gold_values, predicted_values))
        per_item.append(
            {
                "item": item,
                "gold_positive": sum(gold_values),
                "predicted_positive": sum(predicted_values),
                "true_positive": true_positive,
                "false_positive": false_positive,
                "false_negative": false_negative,
                "f1": _f1(gold_values, predicted_values),
            }
        )

    def precision(counter: Counter[str]) -> float | None:
        return counter["true_positive"] / counter["count"] if counter["count"] else None

    return {
        "population": {"records": len(records), "items_per_record": len(ITEMS)},
        "input": {
            "max_document_chars": max_document_chars,
            "records_fully_in_budget": fully_in_budget,
            "records_fully_in_budget_rate": fully_in_budget / len(records),
            "gold_evidence_cases": visible_evidence["total"],
            "gold_evidence_in_source": visible_evidence["in_source"],
            "gold_evidence_in_context": visible_evidence["in_context"],
            "gold_evidence_in_context_rate": visible_evidence["in_context"]
            / visible_evidence["total"],
            "visible_gold_evidence_recall": visible_evidence["true_positive"]
            / visible_evidence["in_context"],
            "evidence_coverage_by_item": {
                item: dict(counts) for item, counts in sorted(coverage_by_item.items())
            },
        },
        "output": {
            "complete_predictions": len(predictions),
            "max_completion_tokens": max(completion_tokens, default=0),
            "mean_completion_tokens": statistics.fmean(completion_tokens)
            if completion_tokens
            else 0.0,
            "completion_token_limit": max_completion_tokens,
            "max_completion_limit_share": max(completion_tokens, default=0)
            / max_completion_tokens,
        },
        "evidence_signal": {
            "valid": {**positive_with_valid_evidence, "precision": precision(positive_with_valid_evidence)},
            "missing": {
                **positive_without_valid_evidence,
                "precision": precision(positive_without_valid_evidence),
            },
            "missing_by_item": dict(missing_evidence_by_item),
        },
        "per_item": per_item,
        "macro_f1": sum(row["f1"] for row in per_item) / len(per_item),
    }
