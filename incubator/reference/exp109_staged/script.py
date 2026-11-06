#!/usr/bin/env python3
"""DACON entrypoint for the configured shared full-split pipeline."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
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
from src.pipeline import judgment_to_row, zero_judgment
from src.legal_groups import groups_for_scheme
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

    def count_tokens(self, messages: list[dict[str, str]]) -> int:
        """Deterministic mock-only admission counter for staged zip tests.

        Production always injects vLLM's Gemma tokenizer. This fallback merely
        lets `script.py --mock` exercise full-split routing without a model.
        """
        return sum(len(message["content"]) for message in messages)

    def complete(self, messages, response_schema) -> Completion:
        import json

        del messages
        properties = response_schema["properties"]
        sparse = "판정" in properties and "발췌" in properties
        label_properties = properties["판정"]["properties"] if sparse else properties
        first_item = next(iter(label_properties))
        labels_only = label_properties[first_item]["type"] == "integer"
        anchor_mode = not labels_only and "판단어구" in label_properties[first_item]["properties"]
        content = (
            {
                "판정": {item: 0 for item in label_properties},
                "발췌": [],
                "부재검토": {
                    item: "필수조건_확인"
                    for item in label_properties
                    if item in {"v10", "v11", "v16", "v18", "v20"}
                },
            }
            if sparse
            else {item: 0 for item in label_properties}
            if labels_only
            else {item: {"위반여부": 0, "판단어구": None} for item in label_properties}
            if anchor_mode
            else {item: {"위반여부": 0, "근거문구": None} for item in label_properties}
        )
        return Completion(
            content=json.dumps(content, ensure_ascii=False),
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
                json=judgment_schema(
                    output_mode=str(PROMPT_CONFIG.get("output_mode", "labels_and_evidence"))
                ), disable_any_whitespace=True
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


def _invalid_json(
    completion: Completion,
    items: tuple[str, ...] = tuple(f"v{index}" for index in range(1, 25)),
) -> bool:
    try:
        parse_judgment(
            completion.content,
            items=items,
            output_mode=str(PROMPT_CONFIG.get("output_mode", "labels_and_evidence")),
        )
    except Exception:
        return True
    return False


def _complete_batch_with_retries(
    client,
    messages_batch: list[list[dict[str, str]]],
    response_schema: dict[str, Any],
    batch_retries: int,
) -> list[Completion]:
    """Retry a transient vLLM batch failure without losing pass alignment."""
    last_error: Exception | None = None
    for attempt in range(batch_retries + 1):
        try:
            outputs = list(client.complete_batch(messages_batch, response_schema))
            if len(outputs) != len(messages_batch):
                raise RuntimeError(
                    f"vLLM returned {len(outputs)} outputs for a batch of "
                    f"{len(messages_batch)}"
                )
            return outputs
        except Exception as exc:
            last_error = exc
            if attempt == batch_retries:
                break
            time.sleep(min(8.0, 2.0**attempt))
    raise RuntimeError(
        f"vLLM batch failed after {batch_retries + 1} attempts: {last_error}"
    ) from last_error


def _complete_group_with_json_retries(
    client,
    messages_batch: list[list[dict[str, str]]],
    response_schema: dict[str, Any],
    batch_retries: int,
    items: tuple[str, ...] = tuple(f"v{index}" for index in range(1, 25)),
):
    """Retry malformed JSON once per pass after resilient batch completion."""
    outputs = _complete_batch_with_retries(
        client, messages_batch, response_schema, batch_retries
    )
    retry_count = 0
    for index, output in enumerate(outputs):
        if not _invalid_json(output, items):
            continue
        retry_count += 1
        replacement = _complete_batch_with_retries(
            client, [messages_batch[index]], response_schema, batch_retries
        )[0]
        if not _invalid_json(replacement, items):
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
    counter = client.count_tokens
    grouping = str(RUNTIME.get("grouping", "all"))
    batch_retries = int(RUNTIME.get("batch_retries", 2))
    if batch_retries < 0:
        raise ValueError("runtime.batch_retries must be non-negative")
    groups = groups_for_scheme(grouping) if grouping != "all" else ()

    def make_pipeline(active_items=None) -> BaselinePipeline:
        return BaselinePipeline(
            item_table=item_table,
            client=client,
            max_document_chars=PROMPT_CONFIG["max_document_chars"],
            prompt_mode=str(PROMPT_CONFIG["mode"]),
            include_normalized_facts=bool(PROMPT_CONFIG["include_normalized_facts"]),
            context_strategy=PROMPT_CONFIG["context_strategy"],
            overflow_split_enabled=bool(PROMPT_CONFIG["overflow_split_enabled"]),
            strict_document_evidence=bool(PROMPT_CONFIG["strict_document_evidence"]),
            absence_detection_strategy=PROMPT_CONFIG["absence_detection_strategy"],
            decision_cards=decision_cards,
            competition_products=competition_products,
            count_tokens=counter,
            prompt_budget_tokens=MAX_MODEL_LEN - OUTPUT_RESERVE_TOKENS,
            active_items=active_items or tuple(f"v{i}" for i in range(1, 25)),
            prompt_layout=str(PROMPT_CONFIG.get("layout", "plain")),
            prompt_profile=str(PROMPT_CONFIG.get("profile", "default")),
            role_directive=str(PROMPT_CONFIG.get("role_directive", "standard")),
            output_mode=str(PROMPT_CONFIG.get("output_mode", "labels_and_evidence")),
            visible_document_types=(
                tuple(PROMPT_CONFIG["visible_document_types"])
                if PROMPT_CONFIG.get("visible_document_types") is not None else None
            ),
        )
    pipeline = make_pipeline()
    retried_malformed = 0

    if not groups:
        pending = []
        contexts_by_record = []
        completions = [[] for _ in records]
        for index, record in enumerate(records):
            contexts = pipeline.contexts_for_record(record)
            contexts_by_record.append(contexts)
            for context in contexts:
                pending.append((index, pipeline.messages_for_context(record, context)))
        for start in range(0, len(pending), args.batch_size):
            batch = pending[start : start + args.batch_size]
            outputs, retries = _complete_group_with_json_retries(
                client,
                [messages for _, messages in batch],
                pipeline.response_schema,
                batch_retries,
                pipeline.active_items,
            )
            retried_malformed += retries
            for (index, _), output in zip(batch, outputs):
                completions[index].append(output)
        rows = [pipeline.finalize(record, completions[index], contexts_by_record[index]) for index, record in enumerate(records)]
        output_rows = prediction_rows(rows)
        unrecovered = sum(len(row.parse_errors) for row in rows)
    else:
        group_pipelines = {group.group_id: make_pipeline(group.items) for group in groups}
        grouped_contexts = {}
        grouped_completions = {}
        for group in groups:
            group_pipeline = group_pipelines[group.group_id]
            pending = []
            for index, record in enumerate(records):
                contexts = group_pipeline.contexts_for_record(record)
                grouped_contexts[index, group.group_id] = contexts
                grouped_completions[index, group.group_id] = []
                for context in contexts:
                    pending.append((index, group_pipeline.messages_for_context(record, context)))
            for start in range(0, len(pending), args.batch_size):
                batch = pending[start : start + args.batch_size]
                outputs, retries = _complete_group_with_json_retries(
                    client,
                    [messages for _, messages in batch],
                group_pipeline.response_schema,
                batch_retries,
                group_pipeline.active_items,
                )
                retried_malformed += retries
                for (index, _), output in zip(batch, outputs):
                    grouped_completions[index, group.group_id].append(output)
        output_rows = []
        unrecovered = 0
        for index, record in enumerate(records):
            judgment = zero_judgment()
            for group in groups:
                result = group_pipelines[group.group_id].finalize(
                    record,
                    grouped_completions[index, group.group_id],
                    grouped_contexts[index, group.group_id],
                )
                unrecovered += len(result.parse_errors)
                for item in group.items:
                    judgment[item] = result.judgment[item]
            output_rows.append(judgment_to_row(record["id"], judgment))
    print(
        f"[submission] malformed structured candidates retried={retried_malformed}; "
        f"unrecovered passes defaulted_to_zero={unrecovered}",
        file=sys.stderr,
        flush=True,
    )
    destination = output_dir / "submission.csv"
    write_submission(output_rows, destination)
    validation = validate_submission(destination, records)
    if not validation.passed:
        raise RuntimeError("submission validation failed: " + "; ".join(validation.errors[:5]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
