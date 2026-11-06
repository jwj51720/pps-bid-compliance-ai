#!/usr/bin/env python3
"""Freeze the label-blind remainder for INC-125's full-dev ledger confirmation."""

from __future__ import annotations

import gzip
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/raw/open/dev.jsonl.gz"
DERIVED = ROOT / "incubator/data/derived"
PREVIOUS = (
    DERIVED / "inc118_legal_source_stratified32_manifest.jsonl",
    DERIVED / "inc118_legal_source_holdout32_manifest.jsonl",
    DERIVED / "inc118_legal_source_third32_manifest.jsonl",
)
OUTPUT = DERIVED / "inc125_luna_ledger_remaining105_manifest.jsonl"


def main() -> None:
    previous_ids = {
        json.loads(line)["id"]
        for path in PREVIOUS
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    }
    with gzip.open(DATA, "rt", encoding="utf-8") as handle:
        all_ids = [json.loads(line)["id"] for line in handle]
    remaining = [record_id for record_id in all_ids if record_id not in previous_ids]
    if len(all_ids) != 200 or len(previous_ids) != 96 or len(remaining) != 104:
        raise RuntimeError(
            f"expected 200 total / 96 prior / 104 remaining, got "
            f"{len(all_ids)} / {len(previous_ids)} / {len(remaining)}"
        )
    # PPS-DEV-125 is one of the previous 96 but its ledger request was blocked
    # by the provider safety filter.  It is deliberately excluded: INC-125's
    # fixed transport fallback uses its existing direct-card response instead.
    rows = [
        {
            "id": record_id,
            "selection": "all dev records not in the three pre-frozen INC-118 cohorts; labels not read",
        }
        for record_id in remaining
    ]
    OUTPUT.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(OUTPUT), "count": len(rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
