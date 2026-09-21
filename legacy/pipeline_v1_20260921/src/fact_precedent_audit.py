"""Pure helpers for the evaluation-only source-fact precedent audit."""

from __future__ import annotations

import re
from typing import Iterable


def source_fragments(text: str, max_chars: int = 900, overlap_chars: int = 180) -> list[str]:
    """Split source text reproducibly, retaining every character in order.

    Paragraphs are retained whole where possible. An oversized paragraph is
    covered by overlapping fixed-size fragments, so evidence crossing a line
    break is not silently discarded.
    """
    if max_chars <= 0 or overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("require max_chars > overlap_chars >= 0")
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        return [text] if text else []
    fragments: list[str] = []
    buffer = ""
    for paragraph in paragraphs:
        candidate = paragraph if not buffer else buffer + "\n\n" + paragraph
        if len(candidate) <= max_chars:
            buffer = candidate
            continue
        if buffer:
            fragments.append(buffer)
            buffer = ""
        if len(paragraph) <= max_chars:
            buffer = paragraph
            continue
        step = max_chars - overlap_chars
        for start in range(0, len(paragraph), step):
            fragment = paragraph[start:start + max_chars]
            if fragment:
                fragments.append(fragment)
            if start + max_chars >= len(paragraph):
                break
    if buffer:
        fragments.append(buffer)
    return fragments


def cosine(left: Iterable[float], right: Iterable[float]) -> float:
    """Return cosine similarity without a numerical-model dependency."""
    left_values = list(left)
    right_values = list(right)
    if len(left_values) != len(right_values):
        raise ValueError("embedding dimensions differ")
    product = sum(a * b for a, b in zip(left_values, right_values))
    left_norm = sum(value * value for value in left_values) ** 0.5
    right_norm = sum(value * value for value in right_values) ** 0.5
    return product / (left_norm * right_norm) if left_norm and right_norm else 0.0


def rank_auc(positive_scores: Iterable[float], negative_scores: Iterable[float]) -> float | None:
    """Return pairwise AUC; ties receive half credit and empty arms return None."""
    positives = list(positive_scores)
    negatives = list(negative_scores)
    if not positives or not negatives:
        return None
    wins = 0.0
    for positive in positives:
        for negative in negatives:
            if positive > negative:
                wins += 1.0
            elif positive == negative:
                wins += 0.5
    return wins / (len(positives) * len(negatives))
