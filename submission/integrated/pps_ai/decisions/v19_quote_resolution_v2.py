"""Positive-only exact evidence resolution for stored v19 observations."""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from .v19_requirements import (
    KIND_VALUES,
    ROLE_VALUES,
    TRI_VALUES,
    reduce_v19_observations,
)
from ..views.v19_requirements import V19RequirementCandidate, candidate_index


REQUIRED_FIELDS = {
    "requirement_role",
    "document_kind",
    "external_issuer_explicit",
    "bidder_must_obtain_or_hold",
    "bidder_must_submit",
    "obtain_before_bid_deadline",
    "submit_with_bid_or_proposal",
    "submit_after_bid_or_contract",
    "quoted_text",
}


def resolve_exact_quote(source: str, quote: str) -> tuple[str | None, str]:
    """Return an unchanged source span using exact or unique whitespace-only mapping."""
    if quote in source:
        return quote, "BYTE_EXACT"
    normalized_quote = "".join(character for character in quote if not character.isspace())
    if not normalized_quote:
        return None, "EMPTY_AFTER_WHITESPACE"
    normalized_source_chars = []
    source_positions = []
    for position, character in enumerate(source):
        if character.isspace():
            continue
        normalized_source_chars.append(character)
        source_positions.append(position)
    normalized_source = "".join(normalized_source_chars)
    starts = []
    cursor = 0
    while True:
        found = normalized_source.find(normalized_quote, cursor)
        if found < 0:
            break
        starts.append(found)
        cursor = found + 1
    if len(starts) != 1:
        return None, "NO_MATCH" if not starts else "AMBIGUOUS_MATCH"
    start = source_positions[starts[0]]
    final_normalized = starts[0] + len(normalized_quote) - 1
    end = source_positions[final_normalized] + 1
    resolved = source[start:end]
    if not 1 <= len(resolved) <= 500:
        return None, "RESOLVED_LENGTH"
    return resolved, "WHITESPACE_UNIQUE"


def parse_v19_observations_relaxed_quote(
    response: Mapping[str, Any],
    candidates: Sequence[V19RequirementCandidate],
) -> tuple[list[dict[str, Any]] | None, str | None]:
    """Validate semantic fields while deferring source resolution to positives."""
    if response.get("finish_reason") != "stop" or response.get("invalid") is True:
        return None, "invalid_transport_response"
    try:
        parsed = json.loads(str(response.get("content", "")))
    except (TypeError, ValueError):
        return None, "invalid_json"
    if not isinstance(parsed, dict) or set(parsed) != {"observations"}:
        return None, "invalid_top_level"
    observations = parsed["observations"]
    sources = candidate_index(candidates)
    if not isinstance(observations, dict) or set(observations) != set(sources):
        return None, "candidate_key_mismatch"
    rows = []
    for source_id in sources:
        value = observations[source_id]
        if not isinstance(value, dict) or set(value) != REQUIRED_FIELDS:
            return None, "observation_shape"
        if value["requirement_role"] not in ROLE_VALUES:
            return None, "requirement_role"
        if value["document_kind"] not in KIND_VALUES:
            return None, "document_kind"
        for key in REQUIRED_FIELDS - {
            "requirement_role", "document_kind", "quoted_text",
        }:
            if value[key] not in TRI_VALUES:
                return None, key
        quote = value["quoted_text"]
        if not isinstance(quote, str) or not 1 <= len(quote) <= 500:
            return None, "quoted_text_shape"
        rows.append({"source_id": source_id, **value})
    return rows, None


def reduce_v19_with_quote_resolution(
    candidates: Sequence[V19RequirementCandidate],
    observations: Sequence[Mapping[str, Any]],
) -> tuple[int | None, str, dict[str, Any]]:
    """Apply unchanged semantics, then require source resolution only for positives."""
    value, _, diagnostic = reduce_v19_observations(candidates, observations)
    sources = candidate_index(candidates)
    resolution = []
    resolved_positives = []
    for row in diagnostic["observations"]:
        source = sources[str(row["source_id"])]
        resolved, method = resolve_exact_quote(source.text, str(row["quoted_text"]))
        resolution.append({
            "source_id": row["source_id"],
            "positive_predicate": row["positive_predicate"],
            "method": method,
            "resolved": resolved is not None,
        })
        if row["positive_predicate"] and resolved is not None:
            resolved_positives.append((source, resolved))
    diagnostic["quote_resolution"] = resolution
    if value == 0:
        return 0, "", diagnostic
    if not resolved_positives:
        diagnostic.update({
            "valid": True,
            "fallback": True,
            "decision": "UNRESOLVED_POSITIVE_EVIDENCE",
        })
        return None, "", diagnostic
    source, evidence = min(
        resolved_positives,
        key=lambda item: (item[0].document_order, item[0].start, item[0].source_id),
    )
    diagnostic.update({
        "decision": "POSITIVE_PROOF",
        "evidence_source_id": source.source_id,
    })
    return 1, evidence, diagnostic
