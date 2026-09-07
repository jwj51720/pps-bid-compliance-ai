#!/usr/bin/env python3
"""Produce a label-blindly reproducible error atlas for the INC-084 teacher."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "incubator/runs/inc084_openai_luna_full_dev_card"
DATA = ROOT / "data/raw/open"
ITEMS = tuple(f"v{number}" for number in range(1, 25))
SEED = "inc086-luna-error-atlas-v1"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    records = {row["id"]: row for row in read_jsonl_gz(DATA / "dev.jsonl.gz")}
    gold = {row["id"]: row for row in csv.DictReader((DATA / "dev_labels.csv").open(encoding="utf-8"))}
    predictions = {row["id"]: row["labels"] for row in read_jsonl(RUN / "responses.jsonl")}
    cards = json.loads((ROOT / "incubator/reference/dev_history/decision_cards_v6.json").read_text(encoding="utf-8"))["cards"]
    errors: list[dict[str, Any]] = []
    summary: dict[str, Counter[str]] = defaultdict(Counter)
    for record_id, prediction in predictions.items():
        record = records[record_id]
        for item in ITEMS:
            actual, expected = prediction[item], int(gold[record_id][item])
            if actual == expected:
                continue
            error_type = "false_positive" if actual else "false_negative"
            key = f"{record['meta'].get('업무구분')} | {record['meta'].get('계약방법')}"
            summary[item][error_type] += 1
            errors.append({
                "id": record_id, "item": item, "item_name": cards[item]["item_name"],
                "error_type": error_type, "teacher_label": actual, "dev_label": expected,
                "observable_stratum": key, "document_types": [document["type"] for document in record["docs"]],
                "source_characters": sum(len(document["text"]) for document in record["docs"]),
                "rank": hashlib.sha256(f"{SEED}:{item}:{error_type}:{record_id}".encode()).hexdigest(),
            })
    # For expensive label-aware qualitative auditing, use at most four examples
    # of each fixed item/error direction. It is a diagnosis sample, never a
    # prompt-tuning set or source of inference rules.
    selected: list[dict[str, Any]] = []
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for error in errors:
        grouped[(error["item"], error["error_type"])].append(error)
    for key, rows in sorted(grouped.items()):
        selected.extend(sorted(rows, key=lambda row: row["rank"])[:4])
    report = {
        "experiment": "inc086_luna_error_atlas",
        "teacher_run": "inc084_openai_luna_full_dev_card",
        "purpose": "diagnose whether direct-teacher errors arise from missed source facts or incorrect legal-condition application",
        "restriction": "dev labels are used only after prediction to select diagnostic examples; no label-specific rule or merge may be derived for inference",
        "total_errors": len(errors),
        "per_item": {item: dict(summary[item]) for item in ITEMS},
        "audit_sample_size": len(selected),
        "sample_selection": "up to four deterministic examples for each item × FP/FN direction",
    }
    (RUN / "error_atlas.jsonl").write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in errors) + "\n", encoding="utf-8")
    (RUN / "error_audit_manifest.jsonl").write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in selected) + "\n", encoding="utf-8")
    (RUN / "error_atlas_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


def read_jsonl_gz(path: Path) -> list[dict[str, Any]]:
    import gzip
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line]


if __name__ == "__main__":
    main()
