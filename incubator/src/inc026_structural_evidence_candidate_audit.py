#!/usr/bin/env python3
"""No-API intact-paragraph candidate coverage audit for INC-026."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common
from inc009_candidate_window_audit import CUES


def structural_blocks(text: str) -> list[tuple[int, int, str]]:
    result: list[tuple[int, int, str]] = []
    start = 0
    for match in re.finditer(r"\n\s*\n+", text):
        end = match.end()
        if text[start:end].strip():
            result.append((start, end, text[start:end]))
        start = end
    if text[start:].strip():
        result.append((start, len(text), text[start:]))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="incubator/configs/inc026_structural_evidence_candidate_audit.json")
    args = parser.parse_args()
    root = common.repo_root()
    cfg = json.loads((root / args.config).read_text(encoding="utf-8"))
    data = root / cfg["data_root"]
    records = common.read_jsonl_gz(data / "dev.jsonl.gz")
    labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}
    report: dict[str, Any] = {"experiment_id": cfg["experiment_id"], "method": "intact blank-paragraph/table-row source blocks; baseline INC-009 cues; no API and no candidate cap", "per_item": []}
    manifest: list[dict[str, Any]] = []
    for item_index, item in enumerate(common.ITEMS, 1):
        gold_pos = evidence_cases = empty_evidence = covered = attribution_fail = neg = neg_candidate = candidate_notices = candidate_blocks = 0
        for record in records:
            candidates: list[dict[str, Any]] = []
            for doc in record["docs"]:
                for start, end, text in structural_blocks(doc["text"]):
                    patterns = [pattern for pattern in CUES[item] if re.search(pattern, text, flags=re.IGNORECASE)]
                    if patterns:
                        candidates.append({"doc_id": doc["doc_id"], "doc_type": doc["type"], "start": start, "end": end, "patterns": patterns})
            is_positive = labels[record["id"]][item] == "1"
            if is_positive and item not in common.ABSENCE_ITEMS:
                gold_pos += 1
                evidence = labels[record["id"]][f"e{item_index}"]
                if not evidence:
                    empty_evidence += 1
                    continue
                evidence_cases += 1
                locations = [(doc, doc["text"].find(evidence)) for doc in record["docs"] if evidence]
                locations = [(doc, offset) for doc, offset in locations if offset >= 0]
                if not locations:
                    attribution_fail += 1
                else:
                    doc, offset = locations[0]
                    covered += any(c["doc_id"] == doc["doc_id"] and c["start"] <= offset and offset + len(evidence) <= c["end"] for c in candidates)
            if not is_positive:
                neg += 1
                neg_candidate += bool(candidates)
            candidate_notices += bool(candidates)
            candidate_blocks += len(candidates)
            manifest.append({"id": record["id"], "item": item, "candidate_count": len(candidates), "candidates": candidates})
        report["per_item"].append({"item": item, "nonabsence_gold_positive": gold_pos, "gold_positive_with_nonempty_evidence": evidence_cases, "gold_positive_with_empty_evidence": empty_evidence, "complete_evidence_coverage": covered / evidence_cases if evidence_cases else None, "attribution_failures": attribution_fail, "negative_candidate_rate": neg_candidate / neg if neg else None, "mean_candidate_blocks_per_notice": candidate_blocks / len(records), "candidate_notice_rate": candidate_notices / len(records)})
    out = root / "incubator/runs" / cfg["experiment_id"]
    out.mkdir(parents=True, exist_ok=True)
    common.write_json(out / "config.json", cfg)
    common.write_json(out / "report.json", report)
    common.write_jsonl(out / "candidate_manifest.jsonl", manifest)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
