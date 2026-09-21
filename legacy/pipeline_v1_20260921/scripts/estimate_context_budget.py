#!/usr/bin/env python3
"""Estimate whether full notice documents fit the 32,768-token model limit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.context_budget import estimate_context_budget
from src.data import load_records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", default="data/raw/open/dev.jsonl.gz")
    parser.add_argument(
        "--predictions", default="outputs/exp-001-first-submission/predictions.jsonl"
    )
    parser.add_argument("--item-table", default="data/raw/open/data/항목표.json")
    parser.add_argument("--current-document-chars", type=int, default=4000)
    parser.add_argument("--max-model-len", type=int, default=32768)
    parser.add_argument("--output-reserve-tokens", type=int, default=2500)
    parser.add_argument("--output", default="outputs/exp-001-context-budget/estimate.json")
    args = parser.parse_args()

    predictions = [
        json.loads(line)
        for line in Path(args.predictions).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    result = estimate_context_budget(
        records=load_records(args.records),
        predictions=predictions,
        item_table_path=args.item_table,
        current_document_chars=args.current_document_chars,
        max_model_len=args.max_model_len,
        output_reserve_tokens=args.output_reserve_tokens,
    )
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
