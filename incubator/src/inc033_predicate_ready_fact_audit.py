#!/usr/bin/env python3
"""No-API source fact audit for four numeric/temporal legal predicate shapes."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common


ROOT = Path(__file__).resolve().parents[2]
TARGETS = ("v3", "v19", "v21", "v23")
AMOUNT = re.compile(r"(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(?:억|만원|원)")
PERCENT = re.compile(r"\d+(?:\.\d+)?\s*%")
DATE_TIME = re.compile(r"(?:20\d{2}[./년\-]\s*\d{1,2}[./월\-]\s*\d{1,2}|\d{1,2}\s*[:시]\s*\d{2})")
RULES = {
    "v3": (re.compile(r"실적"), AMOUNT),
    "v19": (re.compile(r"(?:공급)?확약서"), re.compile(r"입찰|투찰|계약|제출")),
    "v21": (re.compile(r"공동(?:수급|계약|이행|도급)?"), PERCENT),
    "v23": (re.compile(r"현장\s*설명(?:회)?"), DATE_TIME),
}


def blocks(text: str) -> list[tuple[int, str]]:
    """Return nonempty source paragraph blocks, preserving exact content."""
    result = []
    for match in re.finditer(r"(?s)(?:(?<=\n\n)|\A)(.*?)(?=\n\n|\Z)", text):
        value = match.group(1)
        if value.strip():
            result.append((match.start(1), value))
    return result


def facts(record: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    out = {item: [] for item in TARGETS}
    for document in record["docs"]:
        for start, block in blocks(document["text"]):
            for item, (first, second) in RULES.items():
                if first.search(block) and second.search(block):
                    out[item].append({"doc_id": document["doc_id"], "doc_type": document["type"], "start": start, "end": start + len(block), "source_block": block, "matched": [first.search(block).group(), second.search(block).group()]})
    return out


def main() -> None:
    data = ROOT / "data/raw/open"; output = ROOT / "incubator/runs/inc033_predicate_ready_fact_audit"; output.mkdir(parents=True, exist_ok=True)
    records = common.read_jsonl_gz(data / "dev.jsonl.gz"); labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}
    manifest = []; totals = {item: {"positive": 0, "negative": 0, "candidate_positive": 0, "candidate_negative": 0, "source_blocks": Counter()} for item in TARGETS}
    for record in records:
        extracted = facts(record); manifest.append({"id": record["id"], "metadata_regime": {key: record["meta"].get(key) for key in ("적용계약법", "계약방법", "낙찰방법", "입찰추정가격", "배정예산금액", "공동도급구성방식")}, "facts": extracted})
        for item in TARGETS:
            bucket = "positive" if labels[record["id"]][item] == "1" else "negative"; totals[item][bucket] += 1
            totals[item][f"candidate_{bucket}"] += bool(extracted[item])
            totals[item]["source_blocks"].update(fact["doc_type"] for fact in extracted[item])
    report = {"experiment_id": "inc033_predicate_ready_fact_audit", "method": "full source paragraph fact candidates; no label prediction", "items": {}}
    for item, value in totals.items():
        report["items"][item] = {"positive_count": value["positive"], "negative_count": value["negative"], "positive_candidate_recall": value["candidate_positive"] / value["positive"] if value["positive"] else None, "negative_candidate_rate": value["candidate_negative"] / value["negative"] if value["negative"] else None, "source_block_counts": dict(value["source_blocks"])}
    report["source_sha256"] = {"dev": common.sha256_file(data / "dev.jsonl.gz"), "labels": common.sha256_file(data / "dev_labels.csv")}
    common.write_jsonl(output / "manifest.jsonl", manifest); common.write_json(output / "report.json", report); print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
