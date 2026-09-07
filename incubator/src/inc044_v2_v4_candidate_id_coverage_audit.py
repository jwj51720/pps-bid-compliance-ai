#!/usr/bin/env python3
"""Audit exact source candidate IDs for a v2/v4 evidence-selection contract."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common
from inc036_v3_performance_ratio_predicate_audit import amounts


ROOT = Path(__file__).resolve().parents[2]


def candidates(record: dict[str, Any]) -> list[dict[str, Any]]:
    output = []
    docs = sorted(record["docs"], key=lambda doc: (common.DOCUMENT_ORDER[doc["type"]], doc["doc_id"]))
    for doc_position, document in enumerate(docs, 1):
        offset = 0
        for line_number, raw_line in enumerate(document["text"].splitlines(keepends=True)):
            line = raw_line.rstrip("\r\n")
            if "실적" in line and amounts(line):
                output.append({"candidate_id": f"C{doc_position}-{line_number}", "doc_id": document["doc_id"], "doc_type": document["type"], "start": offset, "end": offset + len(line), "source_line": line, "selectable": len(line) <= 500})
            offset += len(raw_line)
    return output


def main() -> None:
    data = ROOT / "data/raw/open"; output = ROOT / "incubator/runs/inc044_v2_v4_candidate_id_coverage_audit"; output.mkdir(parents=True, exist_ok=True)
    records = common.read_jsonl_gz(data / "dev.jsonl.gz")
    labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}
    rows = [{"id": record["id"], "candidates": candidates(record)} for record in records]
    by_id = {row["id"]: row for row in rows}
    report: dict[str, Any] = {"experiment_id": "inc044_v2_v4_candidate_id_coverage_audit", "method": "full source-line performance amount candidates with deterministic IDs; no predictions", "items": {}}
    for item in ("v2", "v4"):
        positives = [record["id"] for record in records if int(labels[record["id"]][item])]
        negatives = [record["id"] for record in records if not int(labels[record["id"]][item])]
        # Gold evidence is organizer-supplied and only used to verify candidate containment.
        covered = [record_id for record_id in positives if any(candidate["selectable"] and labels[record_id][f"e{item[1:]}"] in candidate["source_line"] for candidate in by_id[record_id]["candidates"])]
        active_negatives = [record_id for record_id in negatives if any(candidate["selectable"] for candidate in by_id[record_id]["candidates"])]
        report["items"][item] = {"positive_count": len(positives), "selectable_gold_evidence_coverage": len(covered) / len(positives) if positives else None, "uncovered_positive_ids": sorted(set(positives) - set(covered)), "negative_candidate_rate": len(active_negatives) / len(negatives) if negatives else None}
    counts = [len(row["candidates"]) for row in rows]
    report["candidate_cardinality"] = {"min": min(counts), "median": sorted(counts)[len(counts) // 2], "max": max(counts), "total": sum(counts), "over_500_unselectable": sum(not candidate["selectable"] for row in rows for candidate in row["candidates"]), "document_types": dict(Counter(candidate["doc_type"] for row in rows for candidate in row["candidates"]))}
    common.write_jsonl(output / "manifest.jsonl", rows); common.write_json(output / "report.json", report); print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
