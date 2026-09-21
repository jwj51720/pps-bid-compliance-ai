"""Bounded source-view layer backed by the frozen L41 section extractor."""

from __future__ import annotations

from typing import Any, Mapping


class ReferenceSourceViewLayer:
    module_id = "reference-l41-semantic-sections-v2"

    def __init__(self, section_module: Any) -> None:
        self.section_module = section_module

    def build(self, record: Mapping[str, Any]) -> dict[str, Any]:
        view = self.section_module.build_section_index(dict(record))
        if view.get("id") != record.get("id"):
            raise ValueError("source view identity differs")
        supplied = {
            (str(doc["doc_id"]), str(doc["type"]))
            for doc in record.get("docs") or []
        }
        candidates = [
            candidate
            for section in view["sections"].values()
            for candidate in section["candidates"]
        ]
        bad = [
            candidate for candidate in candidates
            if (str(candidate["doc_id"]), str(candidate["type"])) not in supplied
        ]
        if bad:
            raise ValueError("source view contains a foreign document candidate")
        return view
