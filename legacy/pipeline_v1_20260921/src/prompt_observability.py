"""Offline audit of whether a gold-positive fact reached the prompt context.

Gold labels and evidence are used only after context construction to measure
observability.  Nothing in this module is eligible for model input, routing,
or post-processing.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from src.evidence_audit import locate_evidence
from src.prompt import build_official_baseline_context
from src.schema import ABSENCE_ITEMS

ITEMS = tuple(f"v{index}" for index in range(1, 25))


def audit_prompt_observability(
    records: list[dict[str, Any]],
    labels: dict[str, dict[str, str]],
    context_chars: int,
) -> dict[str, Any]:
    """Measure source/evidence observability in the actual baseline context."""
    per_item = {item: Counter() for item in ITEMS}
    rows: list[dict[str, Any]] = []
    for record in records:
        label = labels[record["id"]]
        context = build_official_baseline_context(record, context_chars)
        truncated = "[절단]" in context
        omitted = "[미수록 문서]" in context
        for index, item in enumerate(ITEMS, 1):
            if int(label[item]) != 1:
                continue
            metrics = per_item[item]
            metrics["positive"] += 1
            row: dict[str, Any] = {
                "id": record["id"],
                "item": item,
                "is_absence": item in ABSENCE_ITEMS,
                "context_truncated": truncated,
                "context_has_omitted_documents": omitted,
                "document_types": [document["type"] for document in record["docs"]],
            }
            if item in ABSENCE_ITEMS:
                row["observability"] = "absence_requires_full_scope" if omitted else "absence_scope_complete"
                metrics[row["observability"]] += 1
            else:
                evidence = label[f"e{index}"].strip()
                if not evidence:
                    row["observability"] = "positive_without_gold_evidence"
                    metrics[row["observability"]] += 1
                else:
                    location = locate_evidence(record, evidence)
                    if location is None:
                        row["observability"] = "gold_evidence_unresolved"
                        metrics[row["observability"]] += 1
                    else:
                        visible = location.source_text in context
                        row.update({
                            "observability": "source_visible" if visible else "source_outside_4k",
                            "source_document_type": location.document_type,
                            "source_document_id": location.doc_id,
                            "match_mode": location.match_mode,
                            "gold_evidence": location.source_text,
                        })
                        metrics[row["observability"]] += 1
            rows.append(row)

    totals = Counter()
    for metrics in per_item.values():
        totals.update(metrics)
    return {
        "scope": {
            "record_count": len(records),
            "context_chars": context_chars,
            "policy": "organizer baseline context construction",
            "label_usage": "evaluation only; never model input",
        },
        "overall": dict(totals),
        "per_item": {item: dict(metrics) for item, metrics in per_item.items()},
        "rows": rows,
    }
