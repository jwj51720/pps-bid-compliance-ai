#!/usr/bin/env python3
"""Offline exact/whitespace-only evidence resolver audit for INC-042."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common


ROOT = Path(__file__).resolve().parents[2]
WS = re.compile(r"\s+")


def normalized_with_spans(text: str) -> tuple[str, list[int]]:
    """Return whitespace-collapsed text and original index for each output char."""
    output: list[str] = []
    origins: list[int] = []
    index = 0
    while index < len(text):
        match = WS.match(text, index)
        if match:
            if output and output[-1] != " ":
                output.append(" ")
                origins.append(index)
            index = match.end()
        else:
            output.append(text[index])
            origins.append(index)
            index += 1
    return "".join(output).strip(), origins


def resolve(quote: str, docs: list[dict[str, Any]]) -> tuple[str, str]:
    if not quote:
        return "", "empty"
    exact = [(doc["text"], doc["text"].find(quote)) for doc in docs if quote in doc["text"]]
    if len(exact) == 1:
        document, start = exact[0]
        return document[start:start + len(quote)], "exact"
    target = WS.sub(" ", quote).strip()
    if not target:
        return "", "empty"
    matches: list[str] = []
    for doc in docs:
        normalized, origins = normalized_with_spans(doc["text"])
        start = normalized.find(target)
        if start >= 0 and normalized.find(target, start + 1) < 0:
            end = start + len(target)
            if end <= len(origins):
                source_start = origins[start]
                source_end = origins[end - 1] + 1
                matches.append(doc["text"][source_start:source_end])
    if len(matches) == 1:
        return matches[0], "whitespace_unique"
    return "", "ambiguous" if matches else "not_found"


def main() -> None:
    data = ROOT / "data/raw/open"
    output = ROOT / "incubator/runs/inc043_evidence_resolution_audit"
    output.mkdir(parents=True, exist_ok=True)
    records = {record["id"]: record for record in common.read_jsonl_gz(data / "dev.jsonl.gz")}
    failed_paths = sorted((ROOT / "incubator/runs/inc042_v2_v4_replicated_law_adjudication/records").glob("*.json"))
    rows = []
    for path in failed_paths:
        entry = json.loads(path.read_text(encoding="utf-8"))
        if entry["success"]:
            continue
        try:
            payload = common.parse_json(entry["raw_response"])
        except Exception:
            rows.append({"id": entry["id"], "arm": entry["arm"], "status": "unparseable_response"})
            continue
        for item in ("v2", "v4"):
            cell = payload.get(item, {})
            if isinstance(cell, dict) and cell.get("위반여부") == 1:
                quote = cell.get("근거문구") if isinstance(cell.get("근거문구"), str) else ""
                resolved, status = resolve(quote, records[entry["id"]]["docs"])
                rows.append({"id": entry["id"], "arm": entry["arm"], "item": item, "quote": quote, "resolution": status, "resolved_evidence": resolved, "resolved_is_source_substring": bool(resolved and any(resolved in doc["text"] for doc in records[entry["id"]]["docs"]))})
    report = {"experiment_id": "inc043_evidence_resolution_audit", "method": "exact then unique whitespace-only source resolution; no binary re-scoring", "quote_count": len(rows), "resolution_counts": dict(Counter(row.get("resolution", row.get("status")) for row in rows)), "all_resolved_are_unchanged_source_substrings": all(not row.get("resolved_evidence") or row["resolved_is_source_substring"] for row in rows)}
    common.write_jsonl(output / "manifest.jsonl", rows)
    common.write_json(output / "report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
