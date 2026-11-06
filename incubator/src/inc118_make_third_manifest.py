#!/usr/bin/env python3
"""Freeze INC-118's third label-blind, profile-balanced cohort."""
from __future__ import annotations

import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/open/dev.jsonl.gz"
DERIVED = ROOT / "incubator/data/derived"
PREVIOUS = (
    DERIVED / "inc118_legal_source_stratified32_manifest.jsonl",
    DERIVED / "inc118_legal_source_holdout32_manifest.jsonl",
)
OUTPUT = DERIVED / "inc118_legal_source_third32_manifest.jsonl"


def profile(meta: dict[str, object]) -> str:
    if meta.get("적용계약법") == "국가계약법":
        return "national"
    if meta.get("계약방법") == "수의계약":
        return "local_small"
    if meta.get("낙찰방법") == "협상에의한계약":
        return "local_negotiated"
    return "local_general"


def main() -> None:
    excluded = {
        json.loads(line)["id"]
        for path in PREVIOUS
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    }
    groups: dict[str, list[str]] = defaultdict(list)
    with gzip.open(RAW, "rt", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if record["id"] not in excluded:
                groups[profile(record["meta"])].append(record["id"])
    rows = []
    for group in sorted(groups):
        selected = sorted(groups[group], key=lambda notice_id: hashlib.sha256(
            f"inc118-legal-third:{group}:{notice_id}".encode()
        ).hexdigest())[:8]
        rows.extend({
            "id": notice_id,
            "profile": group,
            "selection": "excluded first 64; sha256(inc118-legal-third:profile:id), first 8; labels not read",
        } for notice_id in selected)
    if len(rows) != 32 or len({row["id"] for row in rows}) != 32:
        raise RuntimeError("expected 32 unique records")
    OUTPUT.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "count": len(rows), "ids": [row["id"] for row in rows]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
