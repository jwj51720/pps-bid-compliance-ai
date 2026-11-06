#!/usr/bin/env python3
"""Create an inspectable, no-LLM source-role inventory for absence-item audit.

This does not predict a label.  It exposes every source span that could cause
an absence-item judge to confuse a tender eligibility requirement with a
background or post-award mention.  The role is a deterministic *review cue*,
not a legal conclusion.
"""
from __future__ import annotations

import csv
import gzip
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/open"
HIGH = ROOT / "incubator/runs/inc088_openai_luna_high_full_dev_card/responses.jsonl"
SPECIALIST = ROOT / "incubator/runs/inc097_absence_family_specialist_dev200/checkpoint.jsonl"
OUT = ROOT / "incubator/runs/inc098_absence_source_role_inventory"
ITEMS = ("v10", "v11", "v16", "v18", "v20")

# These are search terms, deliberately not a decision rule.  The review output
# preserves all matching original text, including false alarms.
TRIGGERS = re.compile(
    r"중소기업|중기업|소기업|소상공인|직접생산|판로지원|"
    r"경쟁제품|여성기업|장애인기업|사회적기업|SW|소프트웨어"
)
ELIGIBILITY = re.compile(
    r"입찰참가자격|참가자격|입찰참가|자격을 갖춘|이어야|소지한 업체|"
    r"제출.*(업체|자)|제한경쟁|경쟁입찰"
)
INCIDENTAL = re.compile(
    r"하도급|계약체결 후|낙찰자|낙찰.*제출|계약상대자|"
    r"안내|대출|공공구매론|상생결제|연동계약|문의"
)


def load_jsonl_gz(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def latest_success(path: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("success", True):
            result[row["id"]] = row
    return result


def spans(text: str) -> list[str]:
    # Preserve exact source substrings while creating review-sized units.
    units = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [unit.strip() for unit in units if TRIGGERS.search(unit)]


def review_role(span: str) -> str:
    """Return a lexical review cue; never a compliance decision."""
    if INCIDENTAL.search(span):
        return "incidental_or_post_award_cue"
    if ELIGIBILITY.search(span):
        return "bidder_eligibility_cue"
    return "context_ambiguous_cue"


def main() -> None:
    notices = load_jsonl_gz(RAW / "dev.jsonl.gz")
    gold = {row["id"]: row for row in csv.DictReader((RAW / "dev_labels.csv").open(encoding="utf-8"))}
    high = latest_success(HIGH)
    specialist = latest_success(SPECIALIST)
    OUT.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    by_item: dict[str, Counter[str]] = defaultdict(Counter)

    for notice in notices:
        notice_id = notice["id"]
        source_spans = [
            {"doc_type": doc["type"], "doc_id": doc["doc_id"], "text": span, "review_role": review_role(span)}
            for doc in notice["docs"]
            for span in spans(doc["text"])
        ]
        for item in ITEMS:
            if notice_id not in specialist:
                continue
            y = int(gold[notice_id][item])
            direct = int(high[notice_id]["labels"][item])
            separate = int(specialist[notice_id]["labels"][item])
            # Retain all gold positives and every model change; these are the
            # only cases able to explain an apparent specialist gain/loss.
            if y or direct != separate:
                outcome = "tp" if y and separate else "fn" if y else "fp" if separate else "tn"
                record = {
                    "id": notice_id,
                    "item": item,
                    "gold": y,
                    "joint_high": direct,
                    "specialist": separate,
                    "specialist_outcome": outcome,
                    "applicability_metadata": notice["meta"].get("조항호내용"),
                    "source_span_count": len(source_spans),
                    "source_spans": source_spans,
                }
                records.append(record)
                by_item[item][outcome] += 1
                by_item[item]["spans:" + ",".join(sorted({x["review_role"] for x in source_spans}) or ["none"])] += 1

    (OUT / "records.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in records) + "\n", encoding="utf-8"
    )
    report = {
        "purpose": "No-LLM source-role audit; review_role is a lexical cue, not a label.",
        "included_cases": "all gold-positive cases and all joint-high versus specialist changes",
        "specialist_successes": len(specialist),
        "per_item_case_counts": {item: dict(counts) for item, counts in by_item.items()},
    }
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
