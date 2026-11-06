#!/usr/bin/env python3
"""Profile official datasets and labels into an inspectable JSON artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data import label_distribution, load_csv, profile_records
from src.config import load_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        help="use the configured data root, input, and labels paths",
    )
    parser.add_argument("--data-root", default="data/raw/open")
    parser.add_argument("--output", default="outputs/data_profile.json")
    args = parser.parse_args()
    config = load_config(args.config) if args.config else None
    root = config.data.root if config else Path(args.data_root)
    dev_path = config.data.input_path if config else root / "dev.jsonl.gz"
    labels_path = config.data.labels_path if config else root / "dev_labels.csv"
    if labels_path is None:
        raise ValueError("profiling requires a configured labels path")
    profile = {
        "datasets": {
            "train_unlabeled": profile_records(root / "train_unlabeled.jsonl.gz"),
            "dev": profile_records(dev_path),
            "test_sample": profile_records(root / "data/test.jsonl.gz"),
        },
        "dev_label_distribution": label_distribution(load_csv(labels_path)),
        "configured_paths": {
            "config": str(config.path) if config else None,
            "data_root": str(root),
            "dev": str(dev_path),
            "labels": str(labels_path),
            "item_table": str(config.data.item_table_path) if config else None,
        },
    }
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
