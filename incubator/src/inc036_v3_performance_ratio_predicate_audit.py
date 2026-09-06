#!/usr/bin/env python3
"""Fixed source-line v3 performance-to-budget diagnostic, no model calls."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common


ROOT = Path(__file__).resolve().parents[2]
PERFORMANCE_LINE = re.compile(r"실적")
LOWER_BOUND = re.compile(r"(?:이상|초과)")
QUALIFICATION_TERMS = ("보유", "제출", "있는 업체", "있어야", "입찰참가자격")
COMMA_WON = re.compile(r"(?P<num>\d{1,3}(?:,\d{3})+)\s*원")
KOREAN_WON = re.compile(r"(?P<eok>\d+(?:\.\d+)?)\s*억\s*(?:(?P<cheon>\d+(?:\.\d+)?)\s*천\s*만?)?\s*원?")
CHEON_MAN_WON = re.compile(r"(?P<num>\d+(?:\.\d+)?)\s*천\s*만\s*원")
MAN_WON = re.compile(r"(?P<num>\d+(?:\.\d+)?)\s*만\s*원")


def amounts(line: str) -> list[int]:
    values = []
    for match in COMMA_WON.finditer(line): values.append(int(match.group("num").replace(",", "")))
    for match in KOREAN_WON.finditer(line): values.append(round(float(match.group("eok")) * 100_000_000 + float(match.group("cheon") or 0) * 10_000_000))
    for match in CHEON_MAN_WON.finditer(line): values.append(round(float(match.group("num")) * 10_000_000))
    for match in MAN_WON.finditer(line): values.append(round(float(match.group("num")) * 10_000))
    return sorted(set(values))


def classify(record: dict[str, Any]) -> dict[str, Any]:
    budget = record["meta"].get("배정예산금액")
    budget = int(budget) if budget not in (None, "", "None") else None
    candidates = []
    for document in record["docs"]:
        offset = 0
        for line in document["text"].splitlines(keepends=True):
            source_line = line.rstrip("\r\n"); parsed = amounts(source_line)
            is_qualification = any(term in source_line for term in QUALIFICATION_TERMS)
            if PERFORMANCE_LINE.search(source_line) and LOWER_BOUND.search(source_line) and parsed and is_qualification:
                candidates.append({"doc_id": document["doc_id"], "doc_type": document["type"], "start": offset, "end": offset + len(source_line), "source_line": source_line, "amounts_won": parsed})
            offset += len(line)
    comparable = [item for item in candidates if budget is not None]
    positive_candidates = [item for item in comparable if len(item["amounts_won"]) == 1 and item["amounts_won"][0] >= budget]
    positive = bool(positive_candidates)
    has_ambiguous_amount = any(len(item["amounts_won"]) != 1 for item in candidates)
    reason = "positive_performance_at_or_above_budget" if positive else "missing_budget" if budget is None else "ambiguous_multiple_amounts" if has_ambiguous_amount else "no_explicit_qualification_performance_lower_bound" if not candidates else "performance_below_budget"
    evidence = positive_candidates[0]["source_line"] if positive else ""
    return {"id": record["id"], "budget_won": budget, "candidates": candidates, "prediction_diagnostic_only": int(positive), "evidence": evidence, "reason": reason}


def main() -> None:
    data = ROOT / "data/raw/open"; output = ROOT / "incubator/runs/inc036_v3_performance_ratio_predicate_audit"; output.mkdir(parents=True, exist_ok=True)
    records = common.read_jsonl_gz(data / "dev.jsonl.gz"); labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}; rows = [classify(record) for record in records]
    tp = fp = fn = valid = positives = 0
    sources = {record["id"]: "\n".join(doc["text"] for doc in record["docs"]) for record in records}
    for row in rows:
        gold, pred = int(labels[row["id"]]["v3"]), row["prediction_diagnostic_only"]; tp += gold and pred; fp += not gold and pred; fn += gold and not pred
        if pred: positives += 1; valid += bool(row["evidence"] in sources[row["id"]])
    report = {"experiment_id": "inc036_v3_performance_ratio_predicate_audit", "method": "fixed explicit line-level performance lower-bound versus raw budget diagnostic", "tp": tp, "fp": fp, "fn": fn, "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0, "evidence_validity": valid / positives if positives else None, "reason_counts": dict(Counter(row["reason"] for row in rows)), "multi_amount_candidate_ids": [row["id"] for row in rows if any(len(item["amounts_won"]) > 1 for item in row["candidates"])]}
    common.write_jsonl(output / "manifest.jsonl", rows); common.write_json(output / "report.json", report); print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
