#!/usr/bin/env python3
"""No-call source observability audit for INC-119 official-ledger errors."""
from __future__ import annotations

import csv
import gzip
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "incubator/src"))
from evidence_resolver import resolve_quote

RAW = ROOT / "data/raw/open"
RUN = ROOT / "incubator/runs/inc119_gemma_legal_transfer16"
ABSENCE = {"v10", "v11", "v16", "v18", "v20"}


def main() -> None:
    manifest = [json.loads(line)["id"] for line in (ROOT / "incubator/data/derived/inc119_gemma_legal_transfer16_manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    checkpoint = [json.loads(line) for line in (RUN / "checkpoint.jsonl").read_text(encoding="utf-8").splitlines()]
    official = {row["id"]: row["labels"] for row in checkpoint if row.get("success") and row["arm"] == "official_ledger"}
    gold = {row["id"]: row for row in csv.DictReader((RAW / "dev_labels.csv").open(encoding="utf-8"))}
    docs = {}
    with gzip.open(RAW / "dev.jsonl.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["id"] in manifest:
                docs[row["id"]] = row["docs"]
    errors, summary = [], defaultdict(Counter)
    for notice_id in manifest:
        for index in range(1, 25):
            item = f"v{index}"
            actual, predicted = int(gold[notice_id][item]), int(official[notice_id][item])
            if actual == predicted:
                continue
            kind = "FN" if actual else "FP"
            evidence = gold[notice_id][f"e{index}"]
            if kind == "FN" and item in ABSENCE:
                mode = "absence_or_applicability_not_quote_provable"
            elif kind == "FN" and evidence:
                _, status = resolve_quote(evidence, docs[notice_id])
                mode = f"source_evidence_{status}"
            elif kind == "FN":
                mode = "positive_without_gold_quote_requires_compositional_review"
            else:
                mode = "false_positive_requires_applicability_counterfactual_review"
            summary[item][f"{kind}:{mode}"] += 1
            errors.append({"id": notice_id, "item": item, "error": kind, "mode": mode, "gold_evidence": evidence})
    output = {"error_count": len(errors), "summary": {item: dict(value) for item, value in summary.items()}, "errors": errors}
    (RUN / "official_error_observability.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"error_count": len(errors), "summary": output["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
