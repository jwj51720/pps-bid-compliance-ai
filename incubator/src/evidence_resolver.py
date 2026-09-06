"""Deterministically map model quotes back to unchanged source substrings."""
from __future__ import annotations

import re
from typing import Any


WHITESPACE = re.compile(r"\s+")
# Organizer anonymization annotations occur inside an otherwise source-faithful
# sentence.  They are presentation metadata, not prose.  We may ignore them
# only for matching; the returned evidence always retains them verbatim.
ANON_TAG = re.compile(r"\[(?:지역|기관|기관홈페이지|수요기관|담당자|전화번호|팩스번호)(?::[^\]]*)?\]")


def _canonical_with_origins(text: str, strip_tags: bool) -> tuple[str, list[int]]:
    output: list[str] = []
    origins: list[int] = []
    index = 0
    while index < len(text):
        tag = ANON_TAG.match(text, index) if strip_tags else None
        if tag:
            # A tag embedded as ``word [tag]suffix`` is annotation, not a
            # linguistic space.  Remove its preceding collapsed space too.
            if output and output[-1] == " ":
                output.pop()
                origins.pop()
            index = tag.end()
            continue
        space = WHITESPACE.match(text, index)
        if space:
            if output and output[-1] != " ":
                output.append(" ")
                origins.append(index)
            index = space.end()
            continue
        output.append(text[index])
        origins.append(index)
        index += 1
    while output and output[-1] == " ":
        output.pop(); origins.pop()
    return "".join(output), origins


def resolve_quote(quote: str, docs: list[dict[str, Any]]) -> tuple[str, str]:
    """Resolve exact, whitespace, then unique anonymization-tag-omitted quotes.

    Returns ``(unchanged_source_substring, status)``.  Ambiguous fuzzy matches
    are rejected; no generated text is ever returned as evidence.
    """
    if not quote.strip():
        return "", "empty"
    exact = []
    for doc in docs:
        start = doc["text"].find(quote)
        while start >= 0:
            exact.append((doc["text"], start))
            start = doc["text"].find(quote, start + 1)
    # Evidence requires an unchanged substring, not a document offset.  An
    # identical exact string in multiple source documents is still safe.
    if exact:
        return quote, "exact"
    target, _ = _canonical_with_origins(quote, strip_tags=True)
    if not target:
        return "", "empty"
    candidates: list[str] = []
    statuses: list[str] = []
    for strip_tags, name in ((False, "whitespace_unique"), (True, "anonymization_unique")):
        candidates.clear()
        for doc in docs:
            normalized, origins = _canonical_with_origins(doc["text"], strip_tags=strip_tags)
            start = normalized.find(target)
            if start < 0 or normalized.find(target, start + 1) >= 0:
                continue
            end = start + len(target)
            if end <= len(origins):
                candidates.append(doc["text"][origins[start]:origins[end - 1] + 1])
        if len(candidates) == 1:
            return candidates[0], name
        statuses.append("ambiguous" if candidates else "not_found")
    # Table extraction can insert a neighboring cell between two otherwise
    # verbatim anchors.  Recover only a unique, bounded original window; this
    # preserves every intervening source character rather than synthesizing a
    # cleaned sentence.
    compact = WHITESPACE.sub(" ", quote).strip()
    if len(compact) >= 28:
        left = compact[:18]
        words = compact.split(" ")
        right = " ".join(words[-2:]) if len(words) >= 2 else words[-1]
        if len(right) < 4:
            return "", "not_found"
        windows: list[str] = []
        for doc in docs:
            start = doc["text"].find(left)
            while start >= 0:
                end = doc["text"].find(right, start + len(left))
                if end >= 0 and end + len(right) - start <= 500:
                    windows.append(doc["text"][start:end + len(right)])
                start = doc["text"].find(left, start + 1)
        if len(windows) == 1:
            return windows[0], "ordered_anchor_unique"
    return "", "ambiguous" if "ambiguous" in statuses else "not_found"
