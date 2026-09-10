#!/usr/bin/env python3
"""Audit conservative applicability exclusions before any model call.

The gate definition is label-blind.  Labels are optional and used only after
the fact to measure whether a proposed exclusion would have suppressed any
known positive.  A non-zero count is a hard stop, not an invitation to tune a
threshold or add an item-specific exception.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.applicability import GATE_PROVENANCE, safe_inactive_items
from src.data import load_competition_product_index, load_records
from src.schema import ITEMS


def _load_labels(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["id"]: row for row in csv.DictReader(handle)}


def audit(
    records: list[dict[str, Any]], products: dict[str, dict[str, str]],
    labels: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    per_item = {item: {"inactive_count": 0, "reasons": Counter(), "gold_positive_gated": []} for item in ITEMS}
    per_notice_counts: Counter[int] = Counter()
    for record in records:
        inactive = safe_inactive_items(record, products)
        per_notice_counts[len(inactive)] += 1
        for item, reason in inactive.items():
            row = per_item[item]
            row["inactive_count"] += 1
            row["reasons"][reason] += 1
            if labels is not None and labels[record["id"]][item] == "1":
                row["gold_positive_gated"].append(record["id"])
    item_rows = []
    for item in ITEMS:
        row = per_item[item]
        item_rows.append({
            "item": item,
            "inactive_count": row["inactive_count"],
            "reasons": dict(sorted(row["reasons"].items())),
            "gold_positive_gated": row["gold_positive_gated"],
        })
    gated_positive_count = sum(len(row["gold_positive_gated"]) for row in item_rows)
    return {
        "method": "organizer metadata / exact CSV only; no prompt, model, or label-derived gate",
        "gate_provenance": GATE_PROVENANCE,
        "record_count": len(records),
        "per_notice_inactive_item_distribution": dict(sorted(per_notice_counts.items())),
        "mean_inactive_items_per_notice": round(
            sum(count * frequency for count, frequency in per_notice_counts.items()) / len(records), 4
        ) if records else 0.0,
        "items": item_rows,
        "gold_coverage_checked": labels is not None,
        "gold_positive_gated_count": gated_positive_count if labels is not None else None,
        "pass": labels is None or gated_positive_count == 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/raw/open/dev.jsonl.gz")
    parser.add_argument("--products", default="data/derived/competition_products_v1.json")
    parser.add_argument("--labels", default="data/raw/open/dev_labels.csv")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    labels_path = Path(args.labels) if args.labels else None
    report = audit(
        load_records(args.input),
        load_competition_product_index(args.products),
        _load_labels(labels_path) if labels_path else None,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
