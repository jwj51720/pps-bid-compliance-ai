#!/usr/bin/env python3
"""Select a deterministic positive-covering dev sample for route equivalence checks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data import load_csv
from src.schema import ITEMS


def select_ids(
    rows: list[dict[str, str]],
    *,
    target_positive_per_item: int,
    sample_size: int,
) -> list[str]:
    if target_positive_per_item < 1 or sample_size < 1:
        raise ValueError("target and sample size must be positive")
    need = {item: target_positive_per_item for item in ITEMS}
    remaining = list(enumerate(rows))
    selected: list[tuple[int, dict[str, str]]] = []
    while any(value > 0 for value in need.values()):
        index, best = max(
            remaining,
            key=lambda pair: (
                sum(need[item] > 0 and int(pair[1][item]) for item in ITEMS),
                -pair[0],
            ),
        )
        gain = sum(need[item] > 0 and int(best[item]) for item in ITEMS)
        if gain == 0:
            missing = [item for item, value in need.items() if value > 0]
            raise ValueError(f"cannot cover requested positives for: {missing}")
        selected.append((index, best))
        remaining.remove((index, best))
        for item in ITEMS:
            if int(best[item]) and need[item] > 0:
                need[item] -= 1
    if len(selected) > sample_size:
        raise ValueError("positive coverage requires more records than sample size")

    selected_ids = {row["id"] for _, row in selected}
    fillers = sorted(
        (pair for pair in remaining if pair[1]["id"] not in selected_ids),
        key=lambda pair: (sum(int(pair[1][item]) for item in ITEMS), pair[0]),
    )
    selected.extend(fillers[: sample_size - len(selected)])
    return [row["id"] for _, row in selected]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", default="data/raw/open/dev_labels.csv")
    parser.add_argument("--target-positive-per-item", type=int, default=2)
    parser.add_argument("--sample-size", type=int, default=30)
    parser.add_argument(
        "--output", default="outputs/exp-001-free-equivalence/sample_ids.json"
    )
    args = parser.parse_args()
    ids = select_ids(
        load_csv(args.labels),
        target_positive_per_item=args.target_positive_per_item,
        sample_size=args.sample_size,
    )
    payload = {
        "strategy": "greedy positive cover, then lowest-positive-count fillers",
        "target_positive_per_item": args.target_positive_per_item,
        "sample_size": args.sample_size,
        "ids": ids,
    }
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
