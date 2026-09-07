#!/usr/bin/env python3
"""Audit whether INC-088 errors had observable gold support, without model calls.

For an ordinary positive item, the organizer's gold evidence is the strongest
available audit signal: if it resolves against the supplied documents, an FN is
not caused by a missing input.  Absence items deliberately have blank evidence;
they are separately reported as whole-document applicability/absence decisions.
"""
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
RUN = ROOT / "incubator/runs/inc088_openai_luna_high_full_dev_card"
OUT = ROOT / "incubator/runs/inc116_inc088_observability_audit"
ABSENCE_ITEMS = {"v10", "v11", "v16", "v18", "v20"}
ITEMS = [f"v{i}" for i in range(1, 25)]


def normalized(text: str) -> str:
    return "".join(text.split()).replace("[", "").replace("]", "")


def main() -> None:
    gold = {row["id"]: row for row in csv.DictReader((RAW / "dev_labels.csv").open(encoding="utf-8"))}
    documents: dict[str, list[dict[str, str]]] = {}
    with gzip.open(RAW / "dev.jsonl.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            documents[record["id"]] = record["docs"]
    predictions = {}
    for line in (RUN / "responses.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["success"]:
            predictions[row["id"]] = row["labels"]

    atlas = [json.loads(line) for line in (RUN / "high_error_atlas.jsonl").read_text(encoding="utf-8").splitlines()]
    completeness = {row["id"]: row["input_completeness"] for row in atlas}
    records = []
    summary = defaultdict(Counter)
    for notice_id, pred in predictions.items():
        for item in ITEMS:
            actual, guessed = int(gold[notice_id][item]), int(pred[item])
            if actual == guessed:
                continue
            kind = "FN" if actual else "FP"
            group = summary[item]
            group[kind] += 1
            complete = completeness.get(notice_id, {}).get("완전관측")
            group[f"{kind}_complete_input"] += int(complete is True)
            evidence = gold[notice_id][f"e{item[1:]}"]
            if kind == "FN" and item not in ABSENCE_ITEMS:
                _, resolver_status = resolve_quote(evidence, documents[notice_id])
                status = f"gold_evidence_{resolver_status}"
                group[status] += 1
            elif kind == "FN":
                status = "absence_applicability_or_whole_document_reasoning"
                group[status] += 1
            else:
                status = "negative_requires_semantic_counterfactual_review"
                group[status] += 1
            records.append({
                "id": notice_id, "item": item, "error": kind,
                "input_complete": complete, "observability": status,
                "gold_evidence_present": bool(evidence),
            })
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "records.jsonl").write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in records) + "\n", encoding="utf-8")
    report = {
        "scope": "INC-088 full dev200 teacher errors; no model calls",
        "ordinary_positive_fn_interpretation": "gold evidence resolving in supplied documents proves a usable source fact was present; it does not prove why the model ignored or misapplied it.",
        "absence_fn_interpretation": "blank evidence is required by the competition; full input permits an absence/applicability judgment but cannot be mechanically proven by a quote.",
        "per_item": {item: dict(summary[item]) for item in ITEMS if summary[item]},
        "total_errors": len(records),
    }
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
