#!/usr/bin/env python3
"""Evaluate a logically constrained v11 specialist merge without an LLM call.

The specialist may only replace the joint v11 prediction.  An explicit exact
code *non-match* in the organizer competition-product CSV vetoes a specialist
positive, because the v11 card itself says a non-competitive product is 0.
Missing codes and unknown matches never trigger the veto.
"""
from __future__ import annotations

import csv
import gzip
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/open"
PRODUCTS = ROOT / "incubator/data/derived/historical_exp014/competition_products_v1.json"
HIGH = ROOT / "incubator/runs/inc088_openai_luna_high_full_dev_card/responses.jsonl"
SPECIALIST = ROOT / "incubator/runs/inc097_absence_family_specialist_dev200/checkpoint.jsonl"
OUT = ROOT / "incubator/runs/inc099_v11_specialist_exact_code_veto"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def f1(pred: dict[str, int], gold: dict[str, int]) -> dict[str, int | float]:
    tp = sum(pred[k] == 1 and gold[k] == 1 for k in gold)
    fp = sum(pred[k] == 1 and gold[k] == 0 for k in gold)
    fn = sum(pred[k] == 0 and gold[k] == 1 for k in gold)
    return {"tp": tp, "fp": fp, "fn": fn, "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0}


def product_status(meta: dict[str, Any], products: dict[str, Any]) -> str:
    codes = re.findall(r"\d{10}", str(meta.get("세부품명번호목록") or ""))
    if not codes:
        return "unknown_no_exact_code"
    if any(code in products for code in codes):
        return "matched"
    return "not_matched"


def main() -> None:
    with gzip.open(RAW / "dev.jsonl.gz", "rt", encoding="utf-8") as handle:
        notices = [json.loads(line) for line in handle if line]
    gold_rows = {row["id"]: row for row in csv.DictReader((RAW / "dev_labels.csv").open(encoding="utf-8"))}
    high = {row["id"]: row["labels"] for row in read_jsonl(HIGH)}
    specialist = {row["id"]: row for row in read_jsonl(SPECIALIST) if row.get("success")}
    products = json.loads(PRODUCTS.read_text(encoding="utf-8"))["products"]
    base = {n["id"]: int(high[n["id"]]["v11"]) for n in notices}
    merged = dict(base)
    changes: list[dict[str, Any]] = []
    for notice in notices:
        notice_id = notice["id"]
        row = specialist.get(notice_id)
        if row is None:
            continue  # Preserve joint prediction for failed specialist calls.
        specialist_value = int(row["labels"]["v11"])
        status = product_status(notice["meta"], products)
        value = 0 if specialist_value == 1 and status == "not_matched" else specialist_value
        merged[notice_id] = value
        if value != base[notice_id] or value != specialist_value:
            changes.append({
                "id": notice_id,
                "gold": int(gold_rows[notice_id]["v11"]),
                "joint_high": base[notice_id],
                "specialist": specialist_value,
                "exact_code_status": status,
                "merged": value,
                "clause": notice["meta"].get("조항호내용"),
            })
    gold = {notice_id: int(row["v11"]) for notice_id, row in gold_rows.items()}
    OUT.mkdir(parents=True, exist_ok=True)
    report = {
        "hypothesis": "Exact organizer code non-match safely vetoes an otherwise-positive v11 specialist output.",
        "scope": "dev-only diagnostic; not a promoted policy",
        "fallback_for_specialist_failure": "joint high v11",
        "joint_high": f1(base, gold),
        "merged": f1(merged, gold),
        "specialist_successes": len(specialist),
        "changed_or_vetoed_cases": len(changes),
    }
    (OUT / "changes.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in changes) + "\n", encoding="utf-8")
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
