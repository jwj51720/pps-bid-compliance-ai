"""Audit organizer gold evidence against supplied sources, without inferring labels."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data import load_records
from src.schema import ABSENCE_ITEMS, ITEMS


def audit(records, gold, panels):
    result = {"method": "Gold-evidence source observability, not legal-label validity or recall ceiling.",
              "per_item": {}, "cases": []}
    for item in ITEMS:
        counts = Counter()
        panel_counts = {name: Counter() for name in panels}
        for record in records:
            rid = record["id"]
            if int(gold[rid][item]) != 1:
                continue
            evidence = gold[rid]["e" + item[1:]]
            if item in ABSENCE_ITEMS:
                status = "absence_evidence_exempt"
            elif not evidence.strip():
                status = "blank_nonabsence_evidence"
            else:
                docs = record["docs"]
                matches = [doc["doc_id"] for doc in docs if evidence in doc["text"]]
                nfc_matches = [doc["doc_id"] for doc in docs
                    if unicodedata.normalize("NFC", evidence) in
                    unicodedata.normalize("NFC", doc["text"])]
                status = "exact_source_span" if matches else "nfc_only_span" if nfc_matches else "no_exact_span"
            counts[status] += 1
            for name, ids in panels.items():
                if rid in ids:
                    panel_counts[name][status] += 1
            case = {"id": rid, "item": item, "status": status,
                    "evidence_characters": len(evidence),
                    "document_types": [doc["type"] for doc in record["docs"]]}
            if evidence.strip() and item not in ABSENCE_ITEMS:
                case["exact_doc_ids"] = matches
                case["nfc_doc_ids"] = nfc_matches
            result["cases"].append(case)
        result["per_item"][item] = {"positive_count": sum(counts.values()),
                                   "status_counts": counts, "panels": panel_counts}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = load_records("data/raw/open/dev.jsonl.gz")
    with Path("data/raw/open/dev_labels.csv").open() as stream:
        gold = {row["id"]: row for row in csv.DictReader(stream)}
    panels = {name: set(json.loads(Path(path).read_text())["ids"]) for name, path in [
        ("fast", "configs/dev_fast_panel_v1.json"),
        ("holdout", "configs/dev_prompt_holdout_v1.json")]}
    report = audit(records, gold, panels)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report["per_item"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
