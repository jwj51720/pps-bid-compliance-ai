"""Adapter that preserves the hash-pinned reference's v5-v7 source predicates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class RegionalSourceHits:
    v5: tuple[str, ...]
    v6: tuple[str, ...]
    v7: tuple[str, ...]
    small_quote_exception: bool

    @property
    def counts(self) -> dict[str, int]:
        return {"v5": len(self.v5), "v6": len(self.v6), "v7": len(self.v7)}

    @property
    def by_item(self) -> dict[str, tuple[str, ...]]:
        return {"v5": self.v5, "v6": self.v6, "v7": self.v7}


def collect_regional_source_hits(
    record: Mapping[str, Any],
    reference_final_logic: Mapping[str, Any],
) -> RegionalSourceHits:
    """Remove amount filtering only; keep every other source predicate unchanged."""
    required = {"strict_region_hits", "v6_gate", "v7_gate"}
    if not required <= set(reference_final_logic):
        raise ValueError("hash-pinned reference lacks regional source predicates")
    v6_gate = reference_final_logic["v6_gate"]
    v7_gate = reference_final_logic["v7_gate"]
    v5_hits = tuple(reference_final_logic["strict_region_hits"](record))
    v6_hits = tuple(sorted((
        segment for segment in v6_gate.iter_notice_windows(record)
        if v6_gate.any_term(segment, v6_gate.BUSINESS_LOCATION_TERMS)
        and v6_gate.any_term(segment, v6_gate.PARTICIPANT_TERMS)
        and v6_gate.basic_signal(record, segment)
    ), key=len))
    v7_hits = tuple(sorted((
        segment for segment in v7_gate.iter_notice_windows(record)
        if v7_gate.any_term(segment, v7_gate.BUSINESS_LOCATION_TERMS)
        and v7_gate.any_term(segment, v7_gate.PARTICIPANT_TERMS)
        and len(v7_gate.canonical_provinces(segment)) >= 2
    ), key=len))
    small_quote_exception = bool(v6_gate.is_local_small_quote_exception(record))
    return RegionalSourceHits(
        v5=v5_hits,
        v6=v6_hits,
        v7=v7_hits,
        small_quote_exception=small_quote_exception,
    )
