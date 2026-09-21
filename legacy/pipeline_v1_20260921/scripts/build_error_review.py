#!/usr/bin/env python3
"""Export compact source-grounded review packets for prediction disagreements."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data import full_document_text, load_item_table, load_records


def _snippet(source: str, text: str, radius: int = 240) -> str:
    if not text:
        return ""
    start = source.find(text)
    if start < 0:
        return ""
    left = max(0, start - radius)
    right = min(len(source), start + len(text) + radius)
    return source[left:right]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", default="data/raw/open/dev.jsonl.gz")
    parser.add_argument("--labels", default="data/raw/open/dev_labels.csv")
    parser.add_argument("--item-table", default="data/raw/open/data/항목표.json")
    parser.add_argument("--submission", default="outputs/exp-001-context20-full-paid/submission.csv")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument(
        "--output", default="outputs/exp-001-context20-full-paid/error_review.json"
    )
    args = parser.parse_args()

    records = load_records(args.records, limit=args.limit)
    labels = {row["id"]: row for row in csv.DictReader(Path(args.labels).open(encoding="utf-8"))}
    predictions = {
        row["id"]: row
        for row in csv.DictReader(Path(args.submission).open(encoding="utf-8"))
    }
    item_table = load_item_table(args.item_table)
    packets: list[dict[str, Any]] = []
    for record in records:
        record_id = record["id"]
        source = full_document_text(record)
        for index in range(1, 25):
            item = f"v{index}"
            gold = int(labels[record_id][item])
            predicted = int(predictions[record_id][item])
            if gold == predicted:
                continue
            gold_evidence = labels[record_id][f"e{index}"]
            predicted_evidence = predictions[record_id][f"e{index}"]
            packets.append(
                {
                    "id": record_id,
                    "item": item,
                    "item_definition": item_table[item],
                    "gold": gold,
                    "predicted": predicted,
                    "gold_evidence": gold_evidence,
                    "predicted_evidence": predicted_evidence,
                    "gold_evidence_context": _snippet(source, gold_evidence),
                    "predicted_evidence_context": _snippet(source, predicted_evidence),
                    "meta": record["meta"],
                    "dropped_doc_counts": record["dropped_doc_counts"],
                    "documents": [
                        {"doc_id": document["doc_id"], "type": document["type"]}
                        for document in record["docs"]
                    ],
                }
            )
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(packets, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(destination)
    print(f"disagreements={len(packets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
