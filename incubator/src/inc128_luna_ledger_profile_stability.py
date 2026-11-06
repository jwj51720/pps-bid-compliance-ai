#!/usr/bin/env python3
"""Profile-stratified, offline stability audit of the fixed INC-125 policy."""

from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path

import inc125_aggregate_full_dev as aggregate
import inc001_simple_joint24 as common


ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "incubator/runs/inc125_luna_full_dev_official_ledger"


def profile(meta: dict[str, object]) -> str:
    if meta.get("적용계약법") == "국가계약법":
        return "national"
    if meta.get("계약방법") == "수의계약":
        return "local_small"
    if meta.get("낙찰방법") == "협상에의한계약":
        return "local_negotiated"
    return "local_general"


def main() -> None:
    with gzip.open(ROOT / "data/raw/open/dev.jsonl.gz", "rt", encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle if line]
    labels = {row["id"]: row for row in common.read_csv(ROOT / "data/raw/open/dev_labels.csv")}
    direct = {row["id"]: row["labels"] for row in aggregate.read_rows(aggregate.DIRECT) if row.get("success")}
    hybrid_rows = [json.loads(line) for line in (RUN / "full_dev_predictions.jsonl").read_text(encoding="utf-8").splitlines() if line]
    hybrid = {row["id"]: row["labels"] for row in hybrid_rows}
    groups: dict[str, list[str]] = {}
    for record in records:
        groups.setdefault(profile(record["meta"]), []).append(record["id"])
    result = {"experiment_id": "inc128_luna_ledger_profile_stability", "method": "offline profile-stratified score of a policy fixed before full-dev aggregation", "profiles": {}}
    for name, ids in sorted(groups.items()):
        direct_score, direct_items = aggregate.score({record_id: direct[record_id] for record_id in ids}, labels)
        hybrid_score, hybrid_items = aggregate.score({record_id: hybrid[record_id] for record_id in ids}, labels)
        result["profiles"][name] = {
            "records": len(ids), "direct_card_macro_f1": direct_score,
            "ledger_hybrid_macro_f1": hybrid_score, "delta": hybrid_score - direct_score,
            "direct_positive_cells": sum(int(labels[record_id][item]) for record_id in ids for item in common.ITEMS),
            "per_item": [{"item": before["item"], "direct_f1": before["f1"], "hybrid_f1": after["f1"]} for before, after in zip(direct_items, hybrid_items)],
        }
    common.write_json(RUN / "profile_stability.json", result)
    print(json.dumps({name: {key: row[key] for key in ("records", "direct_card_macro_f1", "ledger_hybrid_macro_f1", "delta", "direct_positive_cells")} for name, row in result["profiles"].items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
