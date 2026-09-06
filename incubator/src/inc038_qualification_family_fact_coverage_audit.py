#!/usr/bin/env python3
"""Full-source fact-coverage audit for v1--v9; emits no predictions."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common
from inc036_v3_performance_ratio_predicate_audit import amounts


ROOT = Path(__file__).resolve().parents[2]
INSTITUTION = re.compile(r"(?:기관|대학|학교|연구원|연구기관|공공기관)")
QUALIFICATION = re.compile(r"(?:입찰|참가|자격|제한|가능)")
REGIONAL = re.compile(r"(?:본점|영업소|소재지|관할구역|지역제한)")
MODEL = re.compile(r"(?:모델|model|Model|제조사|제작사)")


def source_facts(record: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    facts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for document in record["docs"]:
        offset = 0
        for raw_line in document["text"].splitlines(keepends=True):
            line = raw_line.rstrip("\r\n")
            base = {"doc_id": document["doc_id"], "doc_type": document["type"], "start": offset, "end": offset + len(line), "source_line": line}
            if INSTITUTION.search(line) and QUALIFICATION.search(line):
                facts["institution_qualification"].append(base)
            if "실적" in line and amounts(line):
                facts["performance_amount"].append({**base, "amounts_won": amounts(line)})
            if REGIONAL.search(line):
                facts["regional_qualification"].append(base)
            if document["type"] == "과업지시서" and MODEL.search(line):
                facts["task_model"].append(base)
            offset += len(raw_line)
    return dict(facts)


ITEM_FACTS = {
    "v1": ("institution_qualification",),
    "v2": ("performance_amount",),
    "v4": ("performance_amount", "institution_qualification"),
    "v5": ("regional_qualification",),
    "v6": ("regional_qualification",),
    "v7": ("regional_qualification",),
    "v8": ("performance_amount", "regional_qualification"),
    "v9": ("task_model",),
}


def has_required_facts(facts: dict[str, list[dict[str, Any]]], required: tuple[str, ...]) -> bool:
    return all(facts.get(name) for name in required)


def main() -> None:
    data = ROOT / "data/raw/open"
    output = ROOT / "incubator/runs/inc038_qualification_family_fact_coverage_audit"
    output.mkdir(parents=True, exist_ok=True)
    records = common.read_jsonl_gz(data / "dev.jsonl.gz")
    labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}
    rows = [{"id": record["id"], "facts": source_facts(record)} for record in records]
    by_id = {row["id"]: row for row in rows}
    report_items: dict[str, Any] = {}
    for item, required in ITEM_FACTS.items():
        positive_ids = [record["id"] for record in records if int(labels[record["id"]][item])]
        negative_ids = [record["id"] for record in records if not int(labels[record["id"]][item])]
        covered = [record_id for record_id in positive_ids if has_required_facts(by_id[record_id]["facts"], required)]
        negative_active = [record_id for record_id in negative_ids if has_required_facts(by_id[record_id]["facts"], required)]
        doc_types = Counter(
            fact["doc_type"]
            for row in rows for name in required for fact in row["facts"].get(name, [])
        )
        report_items[item] = {
            "required_fact_classes": list(required),
            "positive_count": len(positive_ids),
            "positive_candidate_recall": len(covered) / len(positive_ids) if positive_ids else None,
            "missed_positive_ids": sorted(set(positive_ids) - set(covered)),
            "negative_count": len(negative_ids),
            "negative_candidate_rate": len(negative_active) / len(negative_ids) if negative_ids else None,
            "source_fact_document_types": dict(doc_types),
        }
    report = {"experiment_id": "inc038_qualification_family_fact_coverage_audit", "method": "full unchanged source-line fact coverage; no labels predicted", "items": report_items}
    common.write_jsonl(output / "manifest.jsonl", rows)
    common.write_json(output / "report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
