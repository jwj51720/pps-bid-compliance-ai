"""Label-blind audit of native organizer product-code facts."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai.facts.product_codes import build_product_facts, load_product_index
from src.pps_ai.ingest.jsonl import load_notice_records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--products", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    records = load_notice_records(args.input)
    index = load_product_index(args.products)
    types: Counter[str] = Counter()
    notice_count_with_codes = 0
    exact_rows = 0
    unmatched_rows = 0
    special_note_rows = 0
    supplied_name_differences = 0
    for record in records:
        for document in record.documents:
            types[document.document_type] += 1
        facts = build_product_facts(record.metadata, index)
        notice_count_with_codes += bool(facts)
        for fact in facts:
            if fact.csv_name is None:
                unmatched_rows += 1
            else:
                exact_rows += 1
                special_note_rows += bool(fact.special_note)
                supplied_name_differences += fact.supplied_name != fact.csv_name

    report = {
        "input": str(args.input),
        "product_index": str(args.products),
        "records": len(records),
        "document_counts_by_type": dict(sorted(types.items())),
        "notices_with_codes": notice_count_with_codes,
        "notices_without_codes": len(records) - notice_count_with_codes,
        "exact_matched_code_rows": exact_rows,
        "unmatched_code_rows": unmatched_rows,
        "matched_rows_with_special_note": special_note_rows,
        "supplied_name_differs_from_csv_name": supplied_name_differences,
        "product_applicability_labels_assigned": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
