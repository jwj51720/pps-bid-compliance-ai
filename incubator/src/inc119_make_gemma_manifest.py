#!/usr/bin/env python3
"""Freeze a fresh, label-blind four-profile Gemma transfer cohort."""
from __future__ import annotations

import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DERIVED = ROOT / "incubator/data/derived"
PREVIOUS = tuple(DERIVED / name for name in (
    "inc118_legal_source_stratified32_manifest.jsonl",
    "inc118_legal_source_holdout32_manifest.jsonl",
    "inc118_legal_source_third32_manifest.jsonl",
))
OUTPUT = DERIVED / "inc119_gemma_legal_transfer16_manifest.jsonl"


def profile(meta: dict[str, object]) -> str:
    if meta.get("적용계약법") == "국가계약법": return "national"
    if meta.get("계약방법") == "수의계약": return "local_small"
    if meta.get("낙찰방법") == "협상에의한계약": return "local_negotiated"
    return "local_general"


def main() -> None:
    excluded = {json.loads(line)["id"] for path in PREVIOUS for line in path.read_text(encoding="utf-8").splitlines() if line}
    groups: dict[str, list[str]] = defaultdict(list)
    with gzip.open(ROOT / "data/raw/open/dev.jsonl.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if record["id"] not in excluded:
                groups[profile(record["meta"])].append(record["id"])
    rows = []
    for group in sorted(groups):
        for notice_id in sorted(groups[group], key=lambda value: hashlib.sha256(f"inc119-gemma-transfer:{group}:{value}".encode()).hexdigest())[:4]:
            rows.append({"id": notice_id, "profile": group, "selection": "excluded all INC-118 cohorts; sha256(inc119-gemma-transfer:profile:id), first 4; labels not read"})
    if len(rows) != 16 or len({row["id"] for row in rows}) != 16: raise RuntimeError("expected 16 unique notices")
    OUTPUT.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    print(json.dumps({"count": len(rows), "ids": [row["id"] for row in rows]}, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
