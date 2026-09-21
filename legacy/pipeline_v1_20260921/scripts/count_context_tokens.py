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
from src.context_budget import pack_contexts_to_token_budget
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
    parser.add_argument("--reference", help="fixed official reference text included verbatim in every system prompt")
    parser.add_argument("--dump-inputs", help="write final prompt messages for visual inspection")
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
    reference_text = Path(args.reference).read_text(encoding="utf-8") if args.reference else None
    system_prompt = build_system_prompt(item_table, reference_text=reference_text)
    prompt_budget = args.max_model_len - args.output_reserve_tokens
    rows = []
    input_rows = []
    for record in load_records(args.records):
        messages = build_messages(record, system_prompt, max_document_chars=None)
        prompt_tokens = _count_messages(tokenizer, messages)
        contexts = pack_contexts_to_token_budget(
            record,
            system_prompt,
            lambda candidate: _count_messages(tokenizer, candidate),
            prompt_budget,
        )
        pass_messages = [
            build_messages(record, system_prompt, None, document_context=context)
            for context in contexts
        ]
        pass_prompt_tokens = [_count_messages(tokenizer, value) for value in pass_messages]
        rows.append(
            {
                "id": record["id"],
                "full_prompt_tokens": prompt_tokens,
                "fits_prompt_budget": prompt_tokens <= prompt_budget,
                "overflow_tokens": max(0, prompt_tokens - prompt_budget),
                "pass_count": len(pass_messages),
                "pass_prompt_tokens": pass_prompt_tokens,
            }
        )
        if args.dump_inputs:
            input_rows.extend(
                {
                    "id": record["id"],
                    "pass_index": index,
                    "token_count": pass_prompt_tokens[index - 1],
                    "messages": value,
                }
                for index, value in enumerate(pass_messages, 1)
            )
    rows.sort(key=lambda row: (-row["full_prompt_tokens"], row["id"]))
    result = {
        "method": "Gemma tokenizer.apply_chat_template on final system/user messages",
        "tokenizer": str(tokenizer_source),
        "max_model_len": args.max_model_len,
        "output_reserve_tokens": args.output_reserve_tokens,
        "prompt_budget_tokens": prompt_budget,
        "reference": str(args.reference) if args.reference else None,
        "record_count": len(rows),
        "fit_count": sum(row["fits_prompt_budget"] for row in rows),
        "overflow_count": sum(not row["fits_prompt_budget"] for row in rows),
        "overflow_ids": [row["id"] for row in rows if not row["fits_prompt_budget"]],
        "multi_pass_count": sum(row["pass_count"] > 1 for row in rows),
        "rows": rows,
    }
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.dump_inputs:
        input_destination = Path(args.dump_inputs)
        input_destination.parent.mkdir(parents=True, exist_ok=True)
        with input_destination.open("w", encoding="utf-8") as handle:
            for value in input_rows:
                handle.write(json.dumps(value, ensure_ascii=False) + "\n")
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
