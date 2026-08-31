#!/usr/bin/env python3
"""DACON entrypoint for the shared adaptive full-context pipeline."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data import (
    load_competition_product_index,
    load_decision_cards,
    load_item_table,
    load_records,
)
from src.pipeline import BaselinePipeline, parse_judgment
from src.schema import judgment_schema
from src.submission import prediction_rows, validate_submission, write_submission

RUNTIME_CONFIG = json.loads((ROOT / "runtime_config.json").read_text(encoding="utf-8"))
PROMPT_CONFIG = RUNTIME_CONFIG["prompt"]
RUNTIME = RUNTIME_CONFIG["runtime"]
MAX_MODEL_LEN = int(PROMPT_CONFIG["max_model_len"])
OUTPUT_RESERVE_TOKENS = int(PROMPT_CONFIG["output_reserve_tokens"])
SEED = int(RUNTIME["seed"])


@dataclass(frozen=True)
class Completion:
    content: str
    model: str
    latency_seconds: float
    usage: dict[str, Any]
    finish_reason: str | None = None


class MockClient:
    model = "mock"

    def complete(self, messages, response_schema) -> Completion:
        import json

        del messages, response_schema
        return Completion(
            content=json.dumps(
                {f"v{i}": {"위반여부": 0, "근거문구": None} for i in range(1, 25)},
                ensure_ascii=False,
            ),
            model=self.model,
            latency_seconds=0.0,
            usage={},
        )

    def complete_batch(self, batch, response_schema):
        return [self.complete(messages, response_schema) for messages in batch]


class VLLMClient:
    """Offline fixed-Gemma client; its tokenizer is the admission authority."""

    def __init__(self, model_dir: str) -> None:
        from vllm import LLM, SamplingParams
        from vllm.sampling_params import StructuredOutputsParams

        self.llm = LLM(
            model=model_dir,
            tokenizer=model_dir,
            max_model_len=MAX_MODEL_LEN,
            quantization=os.environ.get(
                RUNTIME["quantization_env"], RUNTIME["default_quantization"]
            ),
            gpu_memory_utilization=float(RUNTIME["gpu_memory_utilization"]),
            seed=SEED,
            tensor_parallel_size=1,
            dtype="auto",
        )
        self.tokenizer = self.llm.get_tokenizer()
        self.sampling_params = SamplingParams(
            temperature=0.0,
            max_tokens=OUTPUT_RESERVE_TOKENS,
            seed=SEED,
            structured_outputs=StructuredOutputsParams(
                json=judgment_schema(), disable_any_whitespace=True
            ),
        )
        self.model = model_dir

    def count_tokens(self, messages: list[dict[str, str]]) -> int:
        encoded = self.tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True
        )
        token_ids = encoded["input_ids"] if hasattr(encoded, "keys") else encoded
        return len(token_ids)

    def complete(self, messages: list[dict[str, str]], response_schema: dict[str, Any]) -> Completion:
        return self.complete_batch([messages], response_schema)[0]

    def complete_batch(self, batch, response_schema):
        del response_schema
        outputs = self.llm.chat(batch, sampling_params=self.sampling_params, use_tqdm=False)
        return [
            Completion(
                content=output.outputs[0].text if output.outputs else "",
                model=self.model,
                latency_seconds=0.0,
                usage={},
                finish_reason=(output.outputs[0].finish_reason if output.outputs else None),
            )
            for output in outputs
        ]


def _invalid_json(completion: Completion) -> bool:
    try:
        parse_judgment(completion.content)
    except Exception:
        return True
    return False


def _complete_group_with_json_retries(client, messages_batch, response_schema):
    """Retry only malformed structured candidates; preserve a row for every pass."""
    outputs = list(client.complete_batch(messages_batch, response_schema))
    if len(outputs) != len(messages_batch):
        raise RuntimeError(
            f"vLLM returned {len(outputs)} outputs for a batch of {len(messages_batch)}"
        )
    retry_count = 0
    for index, output in enumerate(outputs):
        if not _invalid_json(output):
            continue
        retry_count += 1
        replacement = client.complete(messages_batch[index], response_schema)
        if not _invalid_json(replacement):
            outputs[index] = replacement
    return outputs, retry_count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--batch-size", type=int, default=int(RUNTIME["batch_size"]))
    args = parser.parse_args()
    data_dir = Path(os.environ["PPS_DATA_DIR"])
    output_dir = Path(os.environ["PPS_OUTPUT_DIR"])
    model_dir = os.environ["PPS_MODEL_DIR"]
    records = load_records(data_dir / "test.jsonl.gz", limit=args.limit)
    item_table = load_item_table(data_dir / "항목표.json")
    cards_file = PROMPT_CONFIG.get("decision_cards_file")
    decision_cards = (
        load_decision_cards(ROOT / str(cards_file), item_table) if cards_file else None
    )
    products_file = PROMPT_CONFIG.get("competition_products_file")
    competition_products = (
        load_competition_product_index(ROOT / str(products_file)) if products_file else None
    )
    client = MockClient() if args.mock else VLLMClient(model_dir)
    counter = None if args.mock else client.count_tokens
    pipeline = BaselinePipeline(
        item_table=item_table,
        client=client,
        max_document_chars=PROMPT_CONFIG["max_document_chars"],
        context_strategy=PROMPT_CONFIG["context_strategy"],
        overflow_split_enabled=bool(PROMPT_CONFIG["overflow_split_enabled"]),
        strict_document_evidence=bool(PROMPT_CONFIG["strict_document_evidence"]),
        absence_detection_strategy=PROMPT_CONFIG["absence_detection_strategy"],
        decision_cards=decision_cards,
        competition_products=competition_products,
        count_tokens=counter,
        prompt_budget_tokens=MAX_MODEL_LEN - OUTPUT_RESERVE_TOKENS,
    )
    pending = []
    contexts_by_record = []
    completions = [[] for _ in records]
    retried_malformed = 0
    for index, record in enumerate(records):
        contexts = pipeline.contexts_for_record(record)
        contexts_by_record.append(contexts)
        for context in contexts:
            pending.append((index, pipeline.messages_for_context(record, context)))
    for start in range(0, len(pending), args.batch_size):
        group = pending[start : start + args.batch_size]
        outputs, retries = _complete_group_with_json_retries(
            client,
            [messages for _, messages in group],
            pipeline.response_schema,
        )
        retried_malformed += retries
        for (index, _), output in zip(group, outputs):
            completions[index].append(output)
    rows = [
        pipeline.finalize(record, completions[index], contexts_by_record[index])
        for index, record in enumerate(records)
    ]
    unrecovered = sum(len(row.parse_errors) for row in rows)
    print(
        f"[submission] malformed structured candidates retried={retried_malformed}; "
        f"unrecovered passes defaulted_to_zero={unrecovered}",
        file=sys.stderr,
        flush=True,
    )
    destination = output_dir / "submission.csv"
    write_submission(prediction_rows(rows), destination)
    validation = validate_submission(destination, records)
    if not validation.passed:
        raise RuntimeError("submission validation failed: " + "; ".join(validation.errors[:5]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
