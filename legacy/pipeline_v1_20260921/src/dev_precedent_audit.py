"""Pure helpers for the leave-one-notice-out dev precedent audit."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from src.evidence_audit import locate_evidence


def source_valid_positive_candidates(
    records: Iterable[dict[str, Any]], labels: dict[str, dict[str, str]]
) -> list[dict[str, str]]:
    """Return only dev positive examples with an exact source evidence span.

    This is a static, organizer-provided demonstration corpus.  A query notice
    must exclude every candidate from itself before any ranking takes place.
    """
    candidates: list[dict[str, str]] = []
    for record in records:
        label = labels[record["id"]]
        for number in range(1, 25):
            item, evidence_key = f"v{number}", f"e{number}"
            if label.get(item) != "1":
                continue
            evidence = label.get(evidence_key, "")
            location = locate_evidence(record, evidence) if evidence else None
            if location is None:
                continue
            candidates.append(
                {
                    "notice_id": record["id"],
                    "item": item,
                    "evidence": evidence,
                    "document_type": location.document_type,
                }
            )
    return candidates


def candidate_indexes_except_notice(
    candidates: Iterable[dict[str, str]], item: str, notice_id: str
) -> list[int]:
    """Index same-item candidates while preventing a self-demonstration leak."""
    return [
        index
        for index, candidate in enumerate(candidates)
        if candidate["item"] == item and candidate["notice_id"] != notice_id
    ]
