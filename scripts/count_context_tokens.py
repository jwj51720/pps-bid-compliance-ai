#!/usr/bin/env python3
"""Count final Gemma chat-template tokens for every notice without inference."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data import load_item_table, load_records
from src.prompt import build_messages, build_system_prompt

DEFAULT_TOKENIZER = "google/gemma-4-26B-A4B-it"


def _count_messages(tokenizer, messages: list[dict[str, str]]) -> int:
    encoded = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
    )
    # Gemma 4's current Transformers implementation returns a BatchEncoding
    # (whose length is its two mapping keys), not a bare token-ID list.
    token_ids = encoded["input_ids"] if isinstance(encoded, Mapping) else encoded
    return len(token_ids)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", default="data/raw/open/dev.jsonl.gz")
    parser.add_argument("--item-table", default="data/raw/open/data/항목표.json")
    parser.add_argument("--tokenizer", help="local model directory or Hugging Face model ID")
    parser.add_argument("--max-model-len", type=int, default=32768)
    parser.add_argument("--output-reserve-tokens", type=int, default=2500)
    parser.add_argument("--output", default="outputs/exp-003-token-counts/full_context.json")
    args = parser.parse_args()
    if not 0 < args.output_reserve_tokens < args.max_model_len:
        raise ValueError("output reserve must be positive and smaller than max model length")

    try:
        from transformers import AutoTokenizer
    except ImportError as exc:
        raise RuntimeError("install requirements.txt to use direct tokenizer counting") from exc

    tokenizer_source = args.tokenizer or os.environ.get("PPS_MODEL_DIR") or DEFAULT_TOKENIZER
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_source)
    item_table = load_item_table(args.item_table)
    system_prompt = build_system_prompt(item_table)
    prompt_budget = args.max_model_len - args.output_reserve_tokens
    rows = []
    for record in load_records(args.records):
        messages = build_messages(record, system_prompt, max_document_chars=None)
        prompt_tokens = _count_messages(tokenizer, messages)
        rows.append(
            {
                "id": record["id"],
                "prompt_tokens": prompt_tokens,
                "fits_prompt_budget": prompt_tokens <= prompt_budget,
                "overflow_tokens": max(0, prompt_tokens - prompt_budget),
            }
        )
    rows.sort(key=lambda row: (-row["prompt_tokens"], row["id"]))
    result = {
        "method": "Gemma tokenizer.apply_chat_template on final system/user messages",
        "tokenizer": str(tokenizer_source),
        "max_model_len": args.max_model_len,
        "output_reserve_tokens": args.output_reserve_tokens,
        "prompt_budget_tokens": prompt_budget,
        "record_count": len(rows),
        "fit_count": sum(row["fits_prompt_budget"] for row in rows),
        "overflow_count": sum(not row["fits_prompt_budget"] for row in rows),
        "overflow_ids": [row["id"] for row in rows if not row["fits_prompt_budget"]],
        "rows": rows,
    }
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
