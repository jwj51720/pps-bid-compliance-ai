#!/usr/bin/env python3
"""Document-independent product identifier fact audit for v9, no predictions."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common


ROOT = Path(__file__).resolve().parents[2]
FIELD = re.compile(r"(?:제조사|모델명|칩셋|chipset)", re.IGNORECASE)
LATIN_DIGIT = re.compile(r"[A-Za-z]+[A-Za-z0-9-]*\d+[A-Za-z0-9-]*")
TECHNICAL_HYPHEN = re.compile(r"\b[A-Z]{2,}-[A-Z]{2,}\b")


def facts(record: dict[str, Any]) -> list[dict[str, Any]]:
    output = []
    for document in record["docs"]:
        offset = 0
        for raw_line in document["text"].splitlines(keepends=True):
            line = raw_line.rstrip("\r\n")
            kinds = []
            if FIELD.search(line): kinds.append("explicit_field")
            if LATIN_DIGIT.search(line): kinds.append("latin_digit")
            if TECHNICAL_HYPHEN.search(line): kinds.append("technical_hyphen")
            if kinds: output.append({"doc_id": document["doc_id"], "doc_type": document["type"], "start": offset, "end": offset + len(line), "source_line": line, "identifier_forms": kinds})
            offset += len(raw_line)
    return output


def main() -> None:
    data = ROOT / "data/raw/open"; output = ROOT / "incubator/runs/inc047_v9_product_identifier_fact_audit"; output.mkdir(parents=True, exist_ok=True)
    records = common.read_jsonl_gz(data / "dev.jsonl.gz"); labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}
    rows = [{"id": record["id"], "facts": facts(record)} for record in records]
    positives = [row["id"] for row in rows if int(labels[row["id"]]["v9"])]; negatives = [row["id"] for row in rows if not int(labels[row["id"]]["v9"])]
    by_id = {row["id"]: row for row in rows}; covered = [record_id for record_id in positives if by_id[record_id]["facts"]]; active_negatives = [record_id for record_id in negatives if by_id[record_id]["facts"]]
    report = {"experiment_id": "inc047_v9_product_identifier_fact_audit", "method": "full source-line typography-level identifier facts; no predictions", "positive_count": len(positives), "positive_candidate_recall": len(covered) / len(positives), "uncovered_positive_ids": sorted(set(positives) - set(covered)), "negative_candidate_rate": len(active_negatives) / len(negatives), "fact_document_types": dict(Counter(fact["doc_type"] for row in rows for fact in row["facts"])), "form_counts": dict(Counter(kind for row in rows for fact in row["facts"] for kind in fact["identifier_forms"]))}
    common.write_jsonl(output / "manifest.jsonl", rows); common.write_json(output / "report.json", report); print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
