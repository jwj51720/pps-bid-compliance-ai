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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default="data/raw/open")
    parser.add_argument("--output", default="outputs/data_profile.json")
    args = parser.parse_args()
    root = Path(args.data_root)
    profile = {
        "datasets": {
            "train_unlabeled": profile_records(root / "train_unlabeled.jsonl.gz"),
            "dev": profile_records(root / "dev.jsonl.gz"),
            "test_sample": profile_records(root / "data/test.jsonl.gz"),
        },
        "dev_label_distribution": label_distribution(load_csv(root / "dev_labels.csv")),
    }
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
