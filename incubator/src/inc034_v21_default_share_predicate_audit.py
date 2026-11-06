#!/usr/bin/env python3
"""Source-preserving diagnostic for the fixed v21 legal default predicate."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common


ROOT = Path(__file__).resolve().parents[2]
MIN_SHARE = re.compile(r"(?:최소\s*)?(?:계약참여\s*)?(?:지분율|참여지분율|출자비율)[^\n]{0,50}?(\d+(?:\.\d+)?)\s*%")


def classify(record: dict[str, Any]) -> dict[str, Any]:
    law = record["meta"].get("적용계약법")
    form = str(record["meta"].get("공동도급구성방식") or "")
    candidates = []
    for document in record["docs"]:
        offset = 0
        for line in document["text"].splitlines(keepends=True):
            source_line = line.rstrip("\r\n")
            match = MIN_SHARE.search(source_line)
            if match:
                candidates.append({"doc_id": document["doc_id"], "doc_type": document["type"], "start": offset, "end": offset + len(source_line), "source_line": source_line, "minimum_share_percent": float(match.group(1))})
            offset += len(line)
    explicit_separate = "분담이행" in form or any("분담이행" in item["source_line"] for item in candidates)
    threshold = 10.0 if law == "국가계약법" else 5.0 if law == "지방계약법" else None
    eligible = [item for item in candidates if not explicit_separate]
    positive = bool(threshold is not None and any(item["minimum_share_percent"] < threshold for item in eligible))
    reason = "positive_default_below_threshold" if positive else "excluded_separate_performance" if explicit_separate else "no_explicit_minimum_share" if not candidates else "at_or_above_default_or_unknown_law"
    evidence = next((item["source_line"] for item in eligible if threshold is not None and item["minimum_share_percent"] < threshold), "")
    return {"id": record["id"], "law": law, "metadata_joint_form": form or None, "threshold_percent": threshold, "candidates": candidates, "prediction_diagnostic_only": int(positive), "evidence": evidence, "reason": reason}


def main() -> None:
    data = ROOT / "data/raw/open"; output = ROOT / "incubator/runs/inc034_v21_default_share_predicate_audit"; output.mkdir(parents=True, exist_ok=True)
    records = common.read_jsonl_gz(data / "dev.jsonl.gz"); labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}
    rows = [classify(record) for record in records]; tp = fp = fn = valid = positive = 0
    for row in rows:
        gold = int(labels[row["id"]]["v21"]); pred = row["prediction_diagnostic_only"]
        tp += gold and pred; fp += not gold and pred; fn += gold and not pred
        if pred:
            positive += 1
            source = "\n".join(doc["text"] for doc in next(record for record in records if record["id"] == row["id"])["docs"])
            valid += bool(row["evidence"] in source)
    report = {"experiment_id": "inc034_v21_default_share_predicate_audit", "method": "fixed legal-default diagnostic; not a policy prediction", "tp": tp, "fp": fp, "fn": fn, "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0, "evidence_validity": valid / positive if positive else None, "reason_counts": dict(Counter(row["reason"] for row in rows)), "excluded_gold_positive_ids": [row["id"] for row in rows if labels[row["id"]]["v21"] == "1" and row["reason"] == "excluded_separate_performance"], "source_sha256": {"dev": common.sha256_file(data / "dev.jsonl.gz"), "labels": common.sha256_file(data / "dev_labels.csv")}}
    common.write_jsonl(output / "manifest.jsonl", rows); common.write_json(output / "report.json", report); print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
