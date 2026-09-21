#!/usr/bin/env python3
"""Export source-complete offline review packets; never infer legal labels."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data import competition_product_fact, load_competition_product_index
from src.data import load_csv, load_records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--items", nargs="+", choices=[f"v{i}" for i in range(1, 25)],
                        default=["v11", "v13", "v16", "v17", "v18"])
    args = parser.parse_args()
    items = tuple(args.items)
    records = list(load_records(ROOT / "data/raw/open/dev.jsonl.gz"))
    labels = {row["id"]: row for row in load_csv(ROOT / "data/raw/open/dev_labels.csv")}
    products = load_competition_product_index(ROOT / "data/derived/competition_products_v1.json")
    panels = {
        name: set(json.loads((ROOT / f"configs/{filename}").read_text())["ids"])
        for name, filename in (
            ("fast", "dev_fast_panel_v1.json"),
            ("holdout", "dev_prompt_holdout_v1.json"),
        )
    }
    args.output.mkdir(parents=True, exist_ok=True)
    rows = []
    for record in records:
        positives = [item for item in items if int(labels[record["id"]][item]) == 1]
        if not positives:
            continue
        fact = competition_product_fact(record, products)
        packet = args.output / f'{record["id"]}.md'
        sections = [
            f'# {record["id"]} — offline source review',
            "Gold is a diagnostic selection only; do not derive card conditions from it.",
            "## Organizer metadata (audit only, not a model prompt)",
            "```json\n" + json.dumps(record["meta"], ensure_ascii=False, indent=2) + "\n```",
            "## Exact-code lookup (not an applicability judgment)",
            "```json\n" + json.dumps(fact, ensure_ascii=False, indent=2) + "\n```",
        ]
        for document in record["docs"]:
            sections.extend([
                f'## {document["doc_id"]} / {document["type"]}', document["text"]
            ])
        packet.write_text("\n\n".join(sections) + "\n", encoding="utf-8")
        rows.append({
            "id": record["id"], "positive_items": positives,
            "panels": [name for name, ids in panels.items() if record["id"] in ids],
            "lookup_status": fact["status"], "matched_products": fact["matched_products"],
            "document_types": [doc["type"] for doc in record["docs"]],
            "source_packet": str(packet),
            "packet_sha256": hashlib.sha256(packet.read_bytes()).hexdigest(),
        })
    report = {
        "method": "offline gold-selected source audit; no model call or label inference",
        "items": items, "records": rows,
        "per_item": {
            item: {
                "positive_count": sum(item in row["positive_items"] for row in rows),
                "lookup_status_counts": dict(Counter(
                    row["lookup_status"] for row in rows if item in row["positive_items"]
                )),
                "panel_positive_counts": {
                    name: sum(item in row["positive_items"] and name in row["panels"] for row in rows)
                    for name in panels
                },
            } for item in items
        },
    }
    path = args.output / "report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["per_item"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
