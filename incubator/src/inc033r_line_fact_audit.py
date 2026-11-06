#!/usr/bin/env python3
"""Single structural-boundary repair for INC-033: source lines, no windows."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common
from inc033_predicate_ready_fact_audit import RULES, TARGETS


ROOT = Path(__file__).resolve().parents[2]


def lines(text: str) -> list[tuple[int, str]]:
    result, offset = [], 0
    for line in text.splitlines(keepends=True):
        value = line.rstrip("\r\n")
        if value.strip():
            result.append((offset, value))
        offset += len(line)
    return result


def facts(record: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    out = {item: [] for item in TARGETS}
    for document in record["docs"]:
        for start, line in lines(document["text"]):
            for item, (first, second) in RULES.items():
                if first.search(line) and second.search(line):
                    out[item].append({"doc_id": document["doc_id"], "doc_type": document["type"], "start": start, "end": start + len(line), "source_line": line, "matched": [first.search(line).group(), second.search(line).group()]})
    return out


def main() -> None:
    data = ROOT / "data/raw/open"; output = ROOT / "incubator/runs/inc033r_line_fact_audit"; output.mkdir(parents=True, exist_ok=True)
    records = common.read_jsonl_gz(data / "dev.jsonl.gz"); labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}
    manifest = []; totals = {item: Counter() for item in TARGETS}
    for record in records:
        extracted = facts(record); manifest.append({"id": record["id"], "facts": extracted})
        for item in TARGETS:
            bucket = "positive" if labels[record["id"]][item] == "1" else "negative"; totals[item][bucket] += 1; totals[item][f"candidate_{bucket}"] += bool(extracted[item])
    report = {"experiment_id": "inc033r_line_fact_audit", "method": "unchanged nonempty source-line candidates; no prediction", "items": {}}
    for item, value in totals.items(): report["items"][item] = {"positive_count": value["positive"], "negative_count": value["negative"], "positive_candidate_recall": value["candidate_positive"] / value["positive"], "negative_candidate_rate": value["candidate_negative"] / value["negative"]}
    common.write_jsonl(output / "manifest.jsonl", manifest); common.write_json(output / "report.json", report); print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
