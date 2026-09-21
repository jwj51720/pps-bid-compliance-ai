#!/usr/bin/env python3
"""Write reproducible diagnostics for a completed labeled experiment."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data import load_csv, load_records
from src.diagnostics import diagnose_experiment


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", default="data/raw/open/dev.jsonl.gz")
    parser.add_argument("--labels", default="data/raw/open/dev_labels.csv")
    parser.add_argument(
        "--predictions", default="outputs/exp-001-first-submission/predictions.jsonl"
    )
    parser.add_argument(
        "--output", default="outputs/exp-001-first-submission/diagnostics.json"
    )
    parser.add_argument("--max-document-chars", type=int, default=4000)
    parser.add_argument("--max-completion-tokens", type=int, default=2500)
    args = parser.parse_args()

    prediction_path = Path(args.predictions)
    predictions = [
        json.loads(line)
        for line in prediction_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    diagnostics = diagnose_experiment(
        load_records(args.records),
        load_csv(args.labels),
        predictions,
        max_document_chars=args.max_document_chars,
        max_completion_tokens=args.max_completion_tokens,
    )
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(diagnostics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
