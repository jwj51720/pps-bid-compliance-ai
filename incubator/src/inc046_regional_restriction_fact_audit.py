#!/usr/bin/env python3
"""Full-source fact audit for v5--v8; no label predictions."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common
from inc036_v3_performance_ratio_predicate_audit import amounts


ROOT = Path(__file__).resolve().parents[2]
REGION_ANCHOR = re.compile(r"(?:본점|주된\s*영업소|소재지|관할구역|지역제한)")
REGION_TOKEN = re.compile(r"(?:특별시|광역시|특별자치시|특별자치도|[가-힣]+(?:시|군|구|도))")


def facts(record: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    output: dict[str, list[dict[str, Any]]] = {"regional": [], "performance_amount": []}
    for document in record["docs"]:
        offset = 0
        for raw_line in document["text"].splitlines(keepends=True):
            line = raw_line.rstrip("\r\n")
            base = {"doc_id": document["doc_id"], "doc_type": document["type"], "start": offset, "end": offset + len(line), "source_line": line}
            if REGION_ANCHOR.search(line) and REGION_TOKEN.search(line): output["regional"].append({**base, "region_tokens": REGION_TOKEN.findall(line)})
            if "실적" in line and amounts(line): output["performance_amount"].append({**base, "amounts_won": amounts(line)})
            offset += len(raw_line)
    return output


REQUIRED = {"v5": ("regional",), "v6": ("regional",), "v7": ("regional",), "v8": ("regional", "performance_amount")}


def main() -> None:
    data = ROOT / "data/raw/open"; output = ROOT / "incubator/runs/inc046_regional_restriction_fact_audit"; output.mkdir(parents=True, exist_ok=True)
    records = common.read_jsonl_gz(data / "dev.jsonl.gz"); labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}
    rows = [{"id": record["id"], "metadata": {key: record["meta"].get(key) for key in ("적용계약법", "입찰추정가격", "제한지역코드목록", "지역제한여부", "계약방법")}, "facts": facts(record)} for record in records]; by_id = {row["id"]: row for row in rows}
    items = {}
    for item, required in REQUIRED.items():
        pos = [record["id"] for record in records if int(labels[record["id"]][item])]; neg = [record["id"] for record in records if not int(labels[record["id"]][item])]
        active = lambda record_id: all(by_id[record_id]["facts"][fact] for fact in required)
        covered = [record_id for record_id in pos if active(record_id)]; negatives = [record_id for record_id in neg if active(record_id)]
        items[item] = {"required_fact_classes": list(required), "positive_count": len(pos), "positive_candidate_recall": len(covered) / len(pos) if pos else None, "uncovered_positive_ids": sorted(set(pos) - set(covered)), "negative_candidate_rate": len(negatives) / len(neg) if neg else None, "positive_metadata_missing_counts": {key: sum(by_id[record_id]["metadata"].get(key) in (None, "", "미입력") for record_id in pos) for key in ("적용계약법", "입찰추정가격", "제한지역코드목록", "지역제한여부", "계약방법")}}
    report = {"experiment_id": "inc046_regional_restriction_fact_audit", "method": "full source-line region/performance facts plus raw applicability metadata; no predictions", "items": items, "region_document_types": dict(Counter(fact["doc_type"] for row in rows for fact in row["facts"]["regional"]))}
    common.write_jsonl(output / "manifest.jsonl", rows); common.write_json(output / "report.json", report); print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
