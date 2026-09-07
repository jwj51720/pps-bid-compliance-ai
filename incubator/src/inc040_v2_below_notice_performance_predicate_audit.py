#!/usr/bin/env python3
"""Law-fixed v2 performance-restriction diagnostic; no model calls."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common
from inc036_v3_performance_ratio_predicate_audit import amounts


ROOT = Path(__file__).resolve().parents[2]
NOTICE_AMOUNT_WON = 230_000_000
LOWER_BOUND = re.compile(r"(?:이상|초과)")
QUALIFICATION = re.compile(r"(?:실적이\s*있는\s*자|실적이\s*있는\s*업체|이상인\s*업체|보유한\s*업체|실적이\s*있어야)")


def eligible_work_type(value: Any) -> bool:
    return "공사" not in str(value)


def classify(record: dict[str, Any]) -> dict[str, Any]:
    meta = record["meta"]
    estimate = meta.get("입찰추정가격")
    estimate = int(estimate) if estimate not in (None, "", "None") else None
    candidates = []
    for document in record["docs"]:
        offset = 0
        for raw_line in document["text"].splitlines(keepends=True):
            line = raw_line.rstrip("\r\n")
            if "실적" in line and LOWER_BOUND.search(line) and amounts(line) and QUALIFICATION.search(line):
                candidates.append({"doc_id": document["doc_id"], "doc_type": document["type"], "start": offset, "end": offset + len(line), "source_line": line, "amounts_won": amounts(line)})
            offset += len(raw_line)
    below_notice = estimate is not None and estimate < NOTICE_AMOUNT_WON
    allowed_type = eligible_work_type(meta.get("업무구분"))
    positive = bool(below_notice and allowed_type and candidates)
    reason = "positive_below_notice_performance_restriction" if positive else "missing_estimate" if estimate is None else "construction_out_of_scope" if not allowed_type else "at_or_above_notice_amount" if not below_notice else "no_explicit_bidder_performance_condition"
    return {"id": record["id"], "estimate_won": estimate, "work_type": meta.get("업무구분"), "notice_amount_won": NOTICE_AMOUNT_WON, "candidates": candidates, "prediction_diagnostic_only": int(positive), "evidence": candidates[0]["source_line"] if positive else "", "reason": reason}


def main() -> None:
    data = ROOT / "data/raw/open"
    output = ROOT / "incubator/runs/inc040_v2_below_notice_performance_predicate_audit"
    output.mkdir(parents=True, exist_ok=True)
    records = common.read_jsonl_gz(data / "dev.jsonl.gz")
    labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}
    rows = [classify(record) for record in records]
    tp = fp = fn = valid = positives = 0
    source = {record["id"]: "\n".join(doc["text"] for doc in record["docs"]) for record in records}
    for row in rows:
        gold, pred = int(labels[row["id"]]["v2"]), row["prediction_diagnostic_only"]
        tp += gold and pred; fp += not gold and pred; fn += gold and not pred
        if pred:
            positives += 1
            valid += bool(row["evidence"] in source[row["id"]])
    report = {"experiment_id": "inc040_v2_below_notice_performance_predicate_audit", "method": "law-fixed notice amount plus explicit bidder performance source role", "notice_amount_won": NOTICE_AMOUNT_WON, "tp": tp, "fp": fp, "fn": fn, "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0, "evidence_validity": valid / positives if positives else None, "reason_counts": dict(Counter(row["reason"] for row in rows))}
    common.write_jsonl(output / "manifest.jsonl", rows)
    common.write_json(output / "report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
