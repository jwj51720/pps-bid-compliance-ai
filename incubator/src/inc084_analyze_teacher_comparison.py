#!/usr/bin/env python3
"""Compare the completed Luna teacher run with the historical EXP109 control."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ITEMS = tuple(f"v{number}" for number in range(1, 25))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def f1(tp: int, fp: int, fn: int) -> float:
    return 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0


def main() -> None:
    data = ROOT / "data/raw/open"
    teacher_run = ROOT / "incubator/runs/inc084_openai_luna_full_dev_card"
    gold_rows = list(csv.DictReader((data / "dev_labels.csv").open(encoding="utf-8")))
    gold = {row["id"]: {item: int(row[item]) for item in ITEMS} for row in gold_rows}
    luna = {row["id"]: row["labels"] for row in read_jsonl(teacher_run / "responses.jsonl")}
    historical = {
        row["id"]: {item: int(row["row"][item]) for item in ITEMS}
        for row in read_jsonl(ROOT / "incubator/reference/dev_history/exp109/predictions.jsonl")
    }
    if set(gold) != set(luna) or set(gold) != set(historical):
        raise ValueError("prediction and gold IDs must match exactly")

    per_item: list[dict[str, Any]] = []
    totals = {"luna_only": [0, 0], "exp109_only": [0, 0], "both_positive": [0, 0], "both_negative": [0, 0]}
    for item in ITEMS:
        counts = {name: [0, 0, 0] for name in ("luna", "exp109")}
        for notice_id, truth in gold.items():
            gold_value = truth[item]
            for name, prediction in (("luna", luna[notice_id][item]), ("exp109", historical[notice_id][item])):
                counts[name][0] += int(prediction == gold_value == 1)
                counts[name][1] += int(prediction == 1 and gold_value == 0)
                counts[name][2] += int(prediction == 0 and gold_value == 1)
            if luna[notice_id][item] == 1 and historical[notice_id][item] == 0:
                totals["luna_only"][gold_value] += 1
            elif luna[notice_id][item] == 0 and historical[notice_id][item] == 1:
                totals["exp109_only"][gold_value] += 1
            elif luna[notice_id][item] == historical[notice_id][item] == 1:
                totals["both_positive"][gold_value] += 1
            else:
                totals["both_negative"][gold_value] += 1
        per_item.append({
            "item": item,
            "luna_f1": f1(*counts["luna"]),
            "exp109_f1": f1(*counts["exp109"]),
            "delta": f1(*counts["luna"]) - f1(*counts["exp109"]),
            "luna_tp": counts["luna"][0], "luna_fp": counts["luna"][1], "luna_fn": counts["luna"][2],
            "exp109_tp": counts["exp109"][0], "exp109_fp": counts["exp109"][1], "exp109_fn": counts["exp109"][2],
        })
    with (teacher_run / "comparison_exp109_per_item.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(per_item[0])); writer.writeheader(); writer.writerows(per_item)
    summary = {
        "comparison_rule": "For each disagreement, count gold 0/1; no merge is selected or proposed.",
        "macro_f1": {
            "luna": sum(row["luna_f1"] for row in per_item) / len(per_item),
            "exp109": sum(row["exp109_f1"] for row in per_item) / len(per_item),
        },
        "disagreement_gold_counts": {
            name: {"gold_0": values[0], "gold_1": values[1]} for name, values in totals.items()
        },
        "improved_items": [row["item"] for row in per_item if row["delta"] > 0],
        "degraded_items": [row["item"] for row in per_item if row["delta"] < 0],
    }
    (teacher_run / "comparison_exp109_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
