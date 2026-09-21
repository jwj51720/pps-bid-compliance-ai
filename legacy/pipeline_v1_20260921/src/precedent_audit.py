"""Offline lexical observability helpers for a prospective precedent bank.

The functions in this module deliberately accept gold evidence only as an
*audit query*.  They must never be used to choose an inference-time retrieval
query, a self-labeling pool, or a final prediction.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from typing import Iterable


TOKEN_PATTERN = re.compile(r"[가-힣A-Za-z0-9][가-힣A-Za-z0-9·ㆍ_-]{1,}")


def tokenize(value: str) -> list[str]:
    """Return NFC-normalized lexical tokens without language-model inference."""
    normalized = unicodedata.normalize("NFC", value).lower()
    return TOKEN_PATTERN.findall(normalized)


def bm25_term_score(
    term_frequency: int,
    document_frequency: int,
    document_count: int,
    document_length: int,
    average_document_length: float,
    *,
    k1: float = 1.2,
    b: float = 0.75,
) -> float:
    """Compute one standard BM25 contribution for an observed query token."""
    if not term_frequency or not document_frequency or not document_count:
        return 0.0
    idf = math.log(1.0 + (document_count - document_frequency + 0.5) /
                   (document_frequency + 0.5))
    denominator = term_frequency + k1 * (
        1.0 - b + b * document_length / max(average_document_length, 1.0)
    )
    return idf * term_frequency * (k1 + 1.0) / denominator


def profile_compatibility(
    left: dict[str, object],
    right: dict[str, object],
    fields: Iterable[str],
) -> dict[str, object]:
    """Compare only present metadata values, leaving missing values neutral."""
    compared: list[str] = []
    matches: list[str] = []
    for field in fields:
        left_value = left.get(field)
        right_value = right.get(field)
        if left_value in (None, "", "미입력") or right_value in (None, "", "미입력"):
            continue
        compared.append(field)
        if left_value == right_value:
            matches.append(field)
    return {
        "compared_fields": compared,
        "matched_fields": matches,
        "rate": round(len(matches) / len(compared), 6) if compared else None,
    }
