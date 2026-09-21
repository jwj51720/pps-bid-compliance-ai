"""Audit stored label attrition; never apply inferred labels to predictions."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

ITEMS = tuple(f"v{i}" for i in range(1, 25))


def label(value):
    if isinstance(value, dict):
        value = value.get("위반여부")
    return value if type(value) is int and value in (0, 1) else None


def raw_judgment(record):
    # Multi-pass concatenations must not be mistaken for the complete raw judgment.
    if len(record.get("pass_judgments", [])) != 1 or record.get("staged_run"):
        return None
    try:
        body = json.loads(record["raw_response"])
    except (ValueError, TypeError):
        return None
    if isinstance(body, dict) and "판정" in body:
        body = body["판정"]
    if not isinstance(body, dict) or not all(label(body.get(item)) is not None for item in ITEMS):
        return None
    return body


def audit(directory, gold):
    rows = [json.loads(line) for line in (directory / "predictions.jsonl").read_text().splitlines()]
    report = {"records": len(rows), "raw_comparable_records": 0, "raw_noncomparable_ids": [],
              "parse_error_ids": [], "length_ids": [], "raw_to_model_label_changes": [],
              "model_to_final_label_changes": [], "errors_on_parse_records": Counter(),
              "errors_on_clean_records": Counter(), "per_item_final_errors": {}}
    for record in rows:
        rid = record["id"]
        parsed = not record.get("parse_errors")
        if not parsed:
            report["parse_error_ids"].append(rid)
        if record.get("finish_reason") == "length":
            report["length_ids"].append(rid)
        raw = raw_judgment(record)
        if raw is None:
            report["raw_noncomparable_ids"].append(rid)
        else:
            report["raw_comparable_records"] += 1
        model = record.get("decision_provenance", {}).get("model_judgment")
        for item in ITEMS:
            truth = int(gold[rid][item])
            final = label(record["judgment"][item])
            if final != truth:
                error = "FN" if truth else "FP"
                target = "errors_on_clean_records" if parsed else "errors_on_parse_records"
                report[target][error] += 1
                report["per_item_final_errors"].setdefault(item, []).append(
                    {"id": rid, "error": error, "parse_error": not parsed})
            if model is None:
                continue
            modeled = label(model[item])
            if raw is not None and label(raw[item]) != modeled:
                report["raw_to_model_label_changes"].append(
                    {"id": rid, "item": item, "raw": label(raw[item]),
                     "model": modeled, "gold": truth})
            if modeled != final:
                report["model_to_final_label_changes"].append(
                    {"id": rid, "item": item, "model": modeled,
                     "final": final, "gold": truth})
    report["method"] = "Offline diagnostic only. Raw comparison excludes ambiguous/multi-pass/staged records."
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, action="append", required=True)
    parser.add_argument("--labels", type=Path, default=Path("data/raw/open/dev_labels.csv"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.labels.open() as stream:
        gold = {row["id"]: row for row in csv.DictReader(stream)}
    reports = {str(directory): audit(directory, gold) for directory in args.run_dir}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n")
    for name, report in reports.items():
        print(name, json.dumps({key: report[key] for key in ["records", "raw_comparable_records",
              "parse_error_ids", "length_ids", "errors_on_parse_records", "errors_on_clean_records"]}))
        print("raw_to_model", report["raw_to_model_label_changes"])
        print("model_to_final_count", len(report["model_to_final_label_changes"]))


if __name__ == "__main__":
    main()
