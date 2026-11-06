#!/usr/bin/env python3
"""Compute a diagnostic per-item upper bound from saved current-era dev200 runs."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any


ITEMS = tuple(f"v{i}" for i in range(1, 25))


def _experiment_number(name: str) -> int | None:
    match = re.search(r"exp-(\d+)", name)
    return int(match.group(1)) if match else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs-root", type=Path, default=Path("outputs"))
    parser.add_argument("--minimum-experiment", type=int, default=200)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    best: dict[str, dict[str, Any] | None] = {item: None for item in ITEMS}
    included_runs: list[dict[str, Any]] = []
    for meta_path in sorted(args.outputs_root.glob("*/run_meta.json")):
        run_dir = meta_path.parent
        experiment_number = _experiment_number(run_dir.name)
        if experiment_number is None or experiment_number < args.minimum_experiment:
            continue
        if "-merged" in run_dir.name or run_dir.name.endswith("-mock"):
            continue
        metrics_path = run_dir / "per_item_metrics.csv"
        if not metrics_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if meta.get("input_count") != 200:
            continue
        if "gemma-4-26b" not in str(meta.get("model", "")):
            continue
        included_runs.append(
            {
                "run_dir": str(run_dir),
                "experiment_id": meta.get("experiment_id"),
                "macro_positive_f1": meta.get("macro_f1"),
            }
        )
        with metrics_path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                item = row["item"]
                candidate = {
                    "f1": float(row["f1"]),
                    "true_positive": int(row["true_positive"]),
                    "false_positive": int(row["false_positive"]),
                    "false_negative": int(row["false_negative"]),
                    "run_dir": str(run_dir),
                }
                if best[item] is None or candidate["f1"] > best[item]["f1"]:
                    best[item] = candidate

    if any(value is None for value in best.values()):
        raise ValueError("not every v item has an eligible saved dev200 result")
    chosen = {item: best[item] for item in ITEMS}
    upper_bound = sum(value["f1"] for value in chosen.values()) / len(ITEMS)
    payload = {
        "method": (
            "post-hoc per-item maximum over saved non-mock, non-merged Gemma dev200 "
            "runs; diagnostic only, not a runnable policy or promotion result"
        ),
        "minimum_experiment": args.minimum_experiment,
        "included_run_count": len(included_runs),
        "included_runs": included_runs,
        "oracle_macro_positive_f1": upper_bound,
        "per_item_best": chosen,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
