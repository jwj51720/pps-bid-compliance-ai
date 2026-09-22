"""Label-blind audit of item-scoped native organizer metadata rendering."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai.facts.metadata import (
    FIELD_LABELS,
    ITEM_METADATA_FIELDS,
    build_metadata_facts,
    render_metadata_facts,
)
from src.pps_ai.ingest.jsonl import load_notice_records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    records = load_notice_records(args.input)
    items = tuple(f"v{index}" for index in range(1, 25))
    if set(items) != set(ITEM_METADATA_FIELDS):
        raise ValueError("metadata contract does not cover exactly 24 v items")
    available: Counter[str] = Counter()
    unavailable: Counter[str] = Counter()
    item_complete: Counter[str] = Counter()
    flag_list_mismatch: Counter[str] = Counter()
    for record in records:
        if not set(FIELD_LABELS).issubset(record.metadata):
            raise ValueError(f"{record.notice_id}: organizer metadata field missing")
        all_facts = build_metadata_facts(record.metadata, items)
        rendered = render_metadata_facts(all_facts)
        if "등록지역:r" in rendered or "\"세부품명번호목록\"" in rendered:
            raise ValueError(f"{record.notice_id}: internal metadata token leaked")
        for fact in all_facts:
            (available if fact.available else unavailable)[fact.source_field] += 1
        for item in items:
            facts = build_metadata_facts(record.metadata, (item,))
            if all(fact.available for fact in facts):
                item_complete[item] += 1
        for flag, list_field in (
            ("지역제한여부", "제한지역코드목록"),
            ("업종제한여부", "면허업종제한목록"),
        ):
            if record.metadata[flag] == "Y" and not record.metadata[list_field]:
                flag_list_mismatch[f"{flag}_yes_without_list"] += 1
            if record.metadata[flag] == "N" and record.metadata[list_field]:
                flag_list_mismatch[f"{flag}_no_with_list"] += 1

    report = {
        "input": str(args.input),
        "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "records": len(records),
        "mapped_items": len(items),
        "mapped_metadata_fields": len(FIELD_LABELS),
        "available_by_field": dict(sorted(available.items())),
        "unavailable_by_field": dict(sorted(unavailable.items())),
        "notices_with_all_mapped_fields_available_by_item": dict(sorted(item_complete.items())),
        "flag_list_mismatch": dict(sorted(flag_list_mismatch.items())),
        "legal_or_label_decisions_made": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
