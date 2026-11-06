#!/usr/bin/env python3
"""Audit v2/v4 law-shaped source roles without predicting either label."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common
from inc036_v3_performance_ratio_predicate_audit import QUALIFICATION_TERMS, amounts


ROOT = Path(__file__).resolve().parents[2]
LOWER_BOUND = re.compile(r"(?:이상|초과)")
INSTITUTION = re.compile(r"(?:기관|학교|대학|병원|정부|지자체|공기업|공단|수요기관)")
RELATION = re.compile(r"(?:발주|납품|수요기관|대상)")


def facts(record: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for document in record["docs"]:
        offset = 0
        for raw_line in document["text"].splitlines(keepends=True):
            line = raw_line.rstrip("\r\n")
            parsed = amounts(line)
            qualification = "실적" in line and bool(LOWER_BOUND.search(line)) and bool(parsed) and any(term in line for term in QUALIFICATION_TERMS)
            if qualification:
                found.append({
                    "doc_id": document["doc_id"], "doc_type": document["type"],
                    "start": offset, "end": offset + len(line), "source_line": line,
                    "amounts_won": parsed,
                    "specific_performance_fact": bool(INSTITUTION.search(line) or RELATION.search(line)),
                })
            offset += len(raw_line)
    return found


def activation(rows: dict[str, dict[str, Any]], ids: list[str], predicate: Any) -> float:
    return sum(bool(predicate(rows[record_id])) for record_id in ids) / len(ids) if ids else 0.0


def main() -> None:
    data = ROOT / "data/raw/open"
    output = ROOT / "incubator/runs/inc039_v2_v4_performance_role_audit"
    output.mkdir(parents=True, exist_ok=True)
    records = common.read_jsonl_gz(data / "dev.jsonl.gz")
    labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}
    rows = {
        record["id"]: {
            "id": record["id"], "estimate_won": record["meta"].get("입찰추정가격"),
            "law": record["meta"].get("적용계약법"), "work_type": record["meta"].get("업무구분"),
            "facts": facts(record),
        }
        for record in records
    }
    report: dict[str, Any] = {"experiment_id": "inc039_v2_v4_performance_role_audit", "method": "complete source-line performance roles and raw-price facts; no predictions", "items": {}}
    for item in ("v2", "v4"):
        positives = [record["id"] for record in records if int(labels[record["id"]][item])]
        negatives = [record["id"] for record in records if not int(labels[record["id"]][item])]
        report["items"][item] = {
            "positive_count": len(positives),
            "qualification_fact_recall": activation(rows, positives, lambda row: row["facts"]),
            "specific_performance_fact_recall": activation(rows, positives, lambda row: any(fact["specific_performance_fact"] for fact in row["facts"])),
            "qualification_negative_rate": activation(rows, negatives, lambda row: row["facts"]),
            "specific_performance_negative_rate": activation(rows, negatives, lambda row: any(fact["specific_performance_fact"] for fact in row["facts"])),
            "positive_ids": positives,
            "positive_estimate_won": {record_id: rows[record_id]["estimate_won"] for record_id in positives},
        }
    report["gold_overlap"] = {
        "v2_and_v4": sorted(record["id"] for record in records if int(labels[record["id"]]["v2"]) and int(labels[record["id"]]["v4"])),
        "v2_only": sorted(record["id"] for record in records if int(labels[record["id"]]["v2"]) and not int(labels[record["id"]]["v4"])),
        "v4_only": sorted(record["id"] for record in records if int(labels[record["id"]]["v4"]) and not int(labels[record["id"]]["v2"])),
    }
    common.write_jsonl(output / "manifest.jsonl", list(rows.values()))
    common.write_json(output / "report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
