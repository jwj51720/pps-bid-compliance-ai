"""Threshold-only v5-v7 decisions using independently sourced predicates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ..facts.regional_thresholds import RegionalThresholdFact
from ..views.regional_participation import RegionalParticipationCandidate


@dataclass(frozen=True)
class RegionalThresholdVerdict:
    applied: bool
    labels: Mapping[str, int]
    reason: str


def apply_regional_threshold(
    fact: RegionalThresholdFact,
    estimated_price: object,
    source_hit_counts: Mapping[str, int],
    small_quote_exception: bool,
    base_labels: Mapping[str, int],
) -> RegionalThresholdVerdict:
    """Only the amount gate changes; source hits and exceptions come from owners.

    v5 is inclusive of the threshold; v6 and v7 apply strictly below it.
    Unknown institution/service facts preserve the prior labels without inventing
    an amount.  This helper does not decide source semantics or extract evidence.
    """
    items = ("v5", "v6", "v7")
    if set(source_hit_counts) != set(items) or set(base_labels) != set(items):
        raise ValueError("regional threshold inputs must contain exactly v5-v7")
    if any(type(value) is not int or value < 0 for value in source_hit_counts.values()):
        raise ValueError("source-hit counts must be nonnegative integers")
    if any(type(value) is not int or value not in (0, 1) for value in base_labels.values()):
        raise ValueError("base labels must be binary integers")
    if type(small_quote_exception) is not bool:
        raise ValueError("small-quote exception must be boolean")
    if fact.state != "CONFIRMED" or fact.threshold_won is None:
        return RegionalThresholdVerdict(False, dict(base_labels), "threshold_unconfirmed")
    if type(estimated_price) is not int or estimated_price < 0:
        return RegionalThresholdVerdict(False, dict(base_labels), "estimated_price_unavailable")
    threshold = fact.threshold_won
    return RegionalThresholdVerdict(
        True,
        {
            "v5": int(
                estimated_price >= threshold and source_hit_counts["v5"] > 0
            ),
            "v6": int(
                estimated_price < threshold
                and source_hit_counts["v6"] > 0
                and not small_quote_exception
            ),
            "v7": int(
                estimated_price < threshold
                and source_hit_counts["v7"] > 0
                and not small_quote_exception
            ),
        },
        "organizer_threshold_applied",
    )


def guard_new_regional_positives(
    verdict: RegionalThresholdVerdict,
    base_labels: Mapping[str, int],
    participation_candidates: tuple[RegionalParticipationCandidate, ...],
) -> RegionalThresholdVerdict:
    """Require bidder-location provenance only for newly introduced positives.

    An existing positive is not removed solely because the new source view fails
    to detect its clause.  A new v6 positive additionally needs the basic-region
    marker in the very same participation clause; metadata region alone is not
    evidence of an unlawful narrower qualification.
    """
    if not verdict.applied:
        return verdict
    labels = dict(verdict.labels)
    if labels["v5"] == 1 and base_labels["v5"] == 0:
        labels["v5"] = int(bool(participation_candidates))
    if labels["v6"] == 1 and base_labels["v6"] == 0:
        labels["v6"] = int(any(
            candidate.basic_region for candidate in participation_candidates
        ))
    return RegionalThresholdVerdict(
        True, labels, "organizer_threshold_with_new_positive_source_guard",
    )
