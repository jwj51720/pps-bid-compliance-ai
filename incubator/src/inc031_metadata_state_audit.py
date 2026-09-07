#!/usr/bin/env python3
"""Audit exact organizer metadata states without constructing predictions."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common


ROOT = Path(__file__).resolve().parents[2]
FIELDS = (
    "적용계약법", "업무구분", "계약방법", "낙찰방법", "지역제한여부",
    "제한지역코드목록", "업종제한여부", "면허업종제한목록", "공동도급구성방식",
    "조항호내용", "정보화사업여부",
)
FAMILIES = {
    "procurement_regime": ("적용계약법", "업무구분", "계약방법", "낙찰방법"),
    "restriction_flags": ("지역제한여부", "제한지역코드목록", "업종제한여부", "면허업종제한목록"),
    "joint_contract": ("공동도급구성방식",),
    "organizer_clause": ("조항호내용",),
}


def state(record: dict[str, Any], fields: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    return tuple((field, str(record["meta"].get(field))) for field in fields)


def summarize(records: list[dict[str, Any]], labels: dict[str, dict[str, str]], fields: tuple[str, ...], item: str) -> dict[str, Any]:
    counts: dict[tuple[tuple[str, str], ...], Counter[str]] = defaultdict(Counter)
    for record in records:
        counts[state(record, fields)][labels[record["id"]][item]] += 1
    positive = sum(value["1"] for value in counts.values())
    covered_by_pure_positive = sum(value["1"] for value in counts.values() if value["1"] and not value["0"])
    mixed = sum(value["1"] for value in counts.values() if value["1"] and value["0"])
    entries = [{"state": dict(key), "positive": value["1"], "negative": value["0"], "class": "mixed" if value["1"] and value["0"] else "positive_only" if value["1"] else "negative_only"} for key, value in sorted(counts.items())]
    return {"distinct_states": len(counts), "gold_positive": positive, "positive_coverage_in_dev_exclusive_states": covered_by_pure_positive / positive if positive else None, "positive_count_in_mixed_states": mixed, "states": entries}


def main() -> None:
    data = ROOT / "data/raw/open"; output = ROOT / "incubator/runs/inc031_metadata_state_audit"; output.mkdir(parents=True, exist_ok=True)
    records = common.read_jsonl_gz(data / "dev.jsonl.gz"); labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}
    report: dict[str, Any] = {"experiment_id": "inc031_metadata_state_audit", "method": "exact organizer metadata-state audit; no prediction or learned grouping", "fields": FIELDS, "families": {}}
    for family, fields in FAMILIES.items():
        report["families"][family] = {item: summarize(records, labels, fields, item) for item in common.ITEMS}
    report["source_sha256"] = {"dev": common.sha256_file(data / "dev.jsonl.gz"), "labels": common.sha256_file(data / "dev_labels.csv")}
    common.write_json(output / "report.json", report)
    print(json.dumps({"output": str(output / "report.json"), "families": list(FAMILIES)}, ensure_ascii=False))


if __name__ == "__main__": main()
