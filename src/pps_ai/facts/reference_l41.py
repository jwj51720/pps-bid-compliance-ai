"""Factual observation layer backed by the frozen L41 FactBuilder."""

from __future__ import annotations

from typing import Any, Mapping


class ReferenceFactLayer:
    module_id = "reference-l41-facts-v1"
    schema_version = "F1-F6"

    def __init__(self, builder: Any) -> None:
        self.builder = builder

    def extract(self, record: Mapping[str, Any]) -> dict[str, Any]:
        packet = self.builder.build(record)
        if packet.get("id") != record.get("id"):
            raise ValueError("fact packet identity differs")
        facts = packet.get("facts")
        if not isinstance(facts, dict) or set(facts) != {f"F{i}" for i in range(1, 7)}:
            raise ValueError("reference fact packet schema differs")
        return packet
