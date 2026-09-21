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
from src.pipeline import (
    PredictionError,
    collect_validated_fact_inventory,
    judgment_to_row,
    parse_fact_inventory_response,
    zero_judgment,
)
from src.context_budget import DocumentContext
from src.legal_groups import groups_for_scheme
from src.prompt import build_fact_inventory_system_prompt
from src.schema import FACT_INVENTORY_CATEGORIES, fact_inventory_schema, judgment_schema
from src.submission import prediction_rows, validate_submission, write_submission

RUNTIME_CONFIG = json.loads((ROOT / "runtime_config.json").read_text(encoding="utf-8"))
PROMPT_CONFIG = RUNTIME_CONFIG["prompt"]
RUNTIME = RUNTIME_CONFIG["runtime"]
MAX_MODEL_LEN = int(PROMPT_CONFIG["max_model_len"])
OUTPUT_RESERVE_TOKENS = int(PROMPT_CONFIG["output_reserve_tokens"])
SEED = int(RUNTIME["seed"])


def _log(message: str) -> None:
    print(f"[submission] {message}", file=sys.stderr, flush=True)


def _normalized_quantization(value: Any) -> str | None:
    """Match the organizer baseline's `PPS_QUANT=none` behavior."""
    if value is None or str(value).strip().lower() in {"", "none"}:
        return None
    return str(value).strip()


def _vllm_init_options(model_dir: str, quantization: Any) -> dict[str, Any]:
    options: dict[str, Any] = {
        "model": model_dir,
        "tokenizer": model_dir,
        "max_model_len": MAX_MODEL_LEN,
        "gpu_memory_utilization": float(RUNTIME["gpu_memory_utilization"]),
        "seed": SEED,
        "tensor_parallel_size": 1,
        "dtype": "auto",
    }
    normalized = _normalized_quantization(quantization)
    if normalized is not None:
        options["quantization"] = normalized
    return options


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
        if properties and all(value.get("type") == "array" for value in properties.values()):
            content = {key: [] for key in properties}
            return Completion(
                content=json.dumps(content, ensure_ascii=False),
                model=self.model,
                latency_seconds=0.0,
                usage={},
            )
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
        started = time.perf_counter()
        from vllm import LLM, SamplingParams
        from vllm.sampling_params import StructuredOutputsParams

        quantization = os.environ.get(
            RUNTIME["quantization_env"], RUNTIME["default_quantization"]
        )
        options = _vllm_init_options(model_dir, quantization)
        _log(
            "model_load start "
            f"max_model_len={MAX_MODEL_LEN} quantization="
            f"{options.get('quantization', 'none')}"
        )
        self.llm = LLM(**options)
        self.tokenizer = self.llm.get_tokenizer()
        self._sampling_params_type = SamplingParams
        self._structured_outputs_type = StructuredOutputsParams
        self._sampling_cache: dict[str, Any] = {}
        self.model = model_dir
        _log(f"model_load complete seconds={time.perf_counter() - started:.3f}")

    def _sampling_params_for(self, response_schema: dict[str, Any]):
        schema_key = json.dumps(response_schema, ensure_ascii=False, sort_keys=True)
        if schema_key not in self._sampling_cache:
            self._sampling_cache[schema_key] = self._sampling_params_type(
                temperature=0.0,
                max_tokens=OUTPUT_RESERVE_TOKENS,
                seed=SEED,
                structured_outputs=self._structured_outputs_type(
                    json=response_schema, disable_any_whitespace=True
                ),
            )
        return self._sampling_cache[schema_key]

    def count_tokens(self, messages: list[dict[str, str]]) -> int:
        encoded = self.tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True
        )
        token_ids = encoded["input_ids"] if hasattr(encoded, "keys") else encoded
        return len(token_ids)

    def complete(self, messages: list[dict[str, str]], response_schema: dict[str, Any]) -> Completion:
        return self.complete_batch([messages], response_schema)[0]

    def complete_batch(self, batch, response_schema):
        outputs = self.llm.chat(
            batch, sampling_params=self._sampling_params_for(response_schema), use_tqdm=False
        )
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


def _complete_inventory_with_json_retries(
    client,
    messages_batch: list[list[dict[str, str]]],
    response_schema: dict[str, Any],
    batch_retries: int,
) -> tuple[list[Completion], int]:
    """Retry malformed source-fact inventory independently of V/E parsing."""
    outputs = _complete_batch_with_retries(
        client, messages_batch, response_schema, batch_retries
    )
    retry_count = 0
    for index, output in enumerate(outputs):
        try:
            parse_fact_inventory_response(output.content)
            continue
        except PredictionError:
            retry_count += 1
        replacement = _complete_batch_with_retries(
            client, [messages_batch[index]], response_schema, batch_retries
        )[0]
        try:
            parse_fact_inventory_response(replacement.content)
            outputs[index] = replacement
        except PredictionError:
            pass
    return outputs, retry_count


def build_submission_pipeline(
    *,
    item_table: dict[str, dict[str, Any]],
    client: Any,
    decision_cards: dict[str, dict[str, Any]] | None,
    competition_products: dict[str, dict[str, str]] | None,
    active_items: tuple[str, ...] = tuple(f"v{i}" for i in range(1, 25)),
    prompt_config: dict[str, Any] | None = None,
) -> BaselinePipeline:
    """Build the shared pipeline from every tracked submission prompt option."""
    selected_prompt = PROMPT_CONFIG if prompt_config is None else prompt_config
    return BaselinePipeline(
        item_table=item_table,
        client=client,
        max_document_chars=selected_prompt["max_document_chars"],
        prompt_mode=str(selected_prompt["mode"]),
        include_normalized_facts=bool(selected_prompt["include_normalized_facts"]),
        context_strategy=selected_prompt["context_strategy"],
        overflow_split_enabled=bool(selected_prompt["overflow_split_enabled"]),
        strict_document_evidence=bool(selected_prompt["strict_document_evidence"]),
        absence_detection_strategy=selected_prompt["absence_detection_strategy"],
        decision_cards=decision_cards,
        competition_products=competition_products,
        competition_product_context_mode=str(
            selected_prompt.get("competition_product_context_mode", "names_only_v1")
        ),
        organizer_input_semantics_mode=str(
            selected_prompt.get("organizer_input_semantics_mode", "off")
        ),
        count_tokens=client.count_tokens,
        prompt_budget_tokens=MAX_MODEL_LEN - OUTPUT_RESERVE_TOKENS,
        active_items=active_items,
        prompt_layout=str(selected_prompt.get("layout", "plain")),
        prompt_profile=str(selected_prompt.get("profile", "default")),
        role_directive=str(selected_prompt.get("role_directive", "standard")),
        item_catalog_style=str(selected_prompt.get("item_catalog_style", "minimal")),
        metadata_style=str(selected_prompt.get("metadata_style", "full_json")),
        output_mode=str(selected_prompt.get("output_mode", "labels_and_evidence")),
        frozen_rule_set=(
            str(RUNTIME_CONFIG.get("postprocess", {}).get("frozen_rule_set"))
            if RUNTIME_CONFIG.get("postprocess", {}).get("frozen_rule_set") else None
        ),
        visible_document_types=(
            tuple(selected_prompt["visible_document_types"])
            if selected_prompt.get("visible_document_types") is not None else None
        ),
    )


def _batched_pipeline_predictions(
    records: list[dict[str, Any]],
    pipeline: BaselinePipeline,
    client: Any,
    batch_size: int,
    batch_retries: int,
) -> tuple[list[Any], int, int, int]:
    """Run one pipeline policy as globally batched source-pack requests."""
    contexts_by_record: list[list[str | DocumentContext | None]] = []
    completions: list[list[Completion]] = [[] for _ in records]
    pending: list[tuple[int, list[dict[str, str]]]] = []
    for index, record in enumerate(records):
        contexts = pipeline.contexts_for_record(record)
        contexts_by_record.append(contexts)
        for context in contexts:
            pending.append((index, pipeline.messages_for_context(record, context)))

    retried_malformed = 0
    for start in range(0, len(pending), batch_size):
        batch = pending[start : start + batch_size]
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

    predictions = [
        pipeline.finalize(record, completions[index], contexts_by_record[index])
        for index, record in enumerate(records)
    ]
    unrecovered = sum(len(prediction.parse_errors) for prediction in predictions)
    return predictions, retried_malformed, unrecovered, len(pending)


def _replace_specialist_items(
    base_predictions: list[Any],
    specialist_predictions: list[Any],
    active_items: tuple[str, ...],
) -> None:
    """Replace only declared model-owned fields, matching offline CSV composition."""
    if len(base_predictions) != len(specialist_predictions):
        raise ValueError("base and specialist prediction counts differ")
    for base, specialist in zip(base_predictions, specialist_predictions):
        if base.record_id != specialist.record_id:
            raise ValueError("base and specialist ordered IDs differ")
        for item in active_items:
            base.judgment[item] = dict(specialist.judgment[item])


def _specialist_composite_rows(
    records: list[dict[str, Any]],
    item_table: dict[str, dict[str, Any]],
    base_pipeline: BaselinePipeline,
    competition_products: dict[str, dict[str, str]] | None,
    client: Any,
    batch_size: int,
    batch_retries: int,
) -> tuple[list[dict[str, Any]], int, int]:
    """Reproduce EXP208 + EXP221(v4) + EXP231(v5) replacement composition."""
    base, retried, unrecovered, request_count = _batched_pipeline_predictions(
        records, base_pipeline, client, batch_size, batch_retries
    )
    _log(f"composite base requests={request_count}")
    for specialist_config in RUNTIME_CONFIG["specialist_run"]["specialists"]:
        active_items = tuple(str(item) for item in specialist_config["active_items"])
        prompt_config = {
            **PROMPT_CONFIG,
            "mode": str(specialist_config["mode"]),
            "profile": str(specialist_config["profile"]),
        }
        cards = load_decision_cards(
            ROOT / str(specialist_config["decision_cards_file"]), item_table
        )
        specialist_pipeline = build_submission_pipeline(
            item_table=item_table,
            client=client,
            decision_cards=cards,
            competition_products=competition_products,
            active_items=active_items,
            prompt_config=prompt_config,
        )
        specialist, retries, parse_errors, specialist_requests = (
            _batched_pipeline_predictions(
                records, specialist_pipeline, client, batch_size, batch_retries
            )
        )
        retried += retries
        unrecovered += parse_errors
        request_count += specialist_requests
        _replace_specialist_items(base, specialist, active_items)
        _log(
            f"composite specialist={specialist_config['id']} "
            f"items={','.join(active_items)} requests={specialist_requests}"
        )
    _log(f"composite total_requests={request_count}")
    return prediction_rows(base), retried, unrecovered


def _source_first_full_final_rows(
    records: list[dict[str, Any]], pipeline: BaselinePipeline, client: Any,
    batch_size: int, batch_retries: int,
) -> tuple[list[dict[str, Any]], int, int]:
    """Run EXP171's source-first/full-final policy in two vLLM-batched stages.

    The first stage produces only source-grounded factual navigation.  It has
    no label semantics.  The second stage owns V/E and receives all original
    admitted source again.  This mirrors the shared pipeline method while
    batching each stage across notices for submission throughput.
    """
    phase_started = time.perf_counter()
    inventory_system = build_fact_inventory_system_prompt()
    inventory_schema = fact_inventory_schema()
    inventory_responses: list[list[tuple[str, str]]] = [[] for _ in records]
    pending: list[tuple[int, str, list[dict[str, str]]]] = []
    for index, record in enumerate(records):
        contexts = pipeline.contexts_for_record(record)
        for context in contexts:
            source, messages = pipeline.navigation_messages_for_context(
                record,
                context,
                inventory_system,
            )
            pending.append((index, source, messages))

    _log(
        f"stage1_prepare records={len(records)} requests={len(pending)} "
        f"seconds={time.perf_counter() - phase_started:.3f}"
    )

    phase_started = time.perf_counter()
    retried_malformed = 0
    for start in range(0, len(pending), batch_size):
        batch = pending[start : start + batch_size]
        outputs, retries = _complete_inventory_with_json_retries(
            client, [messages for _, _, messages in batch], inventory_schema,
            batch_retries,
        )
        retried_malformed += retries
        for (index, source, _), completion in zip(batch, outputs):
            inventory_responses[index].append((source, completion.content))
    _log(
        f"stage1_generate requests={len(pending)} retries={retried_malformed} "
        f"seconds={time.perf_counter() - phase_started:.3f}"
    )

    phase_started = time.perf_counter()
    final_contexts: list[list[str | DocumentContext | None]] = []
    final_completions: list[list[Completion]] = [[] for _ in records]
    final_pending: list[tuple[int, list[dict[str, str]]]] = []
    for index, record in enumerate(records):
        inventory, _ = collect_validated_fact_inventory(
            pipeline._visible_record(record),
            inventory_responses[index],
        )
        contexts, messages_by_context = pipeline.fact_inventory_final_plan(
            record, inventory,
        )
        final_contexts.append(contexts)
        for messages in messages_by_context:
            final_pending.append((index, messages))

    _log(
        f"final_prepare records={len(records)} requests={len(final_pending)} "
        f"seconds={time.perf_counter() - phase_started:.3f}"
    )

    phase_started = time.perf_counter()
    final_retry_start = retried_malformed
    for start in range(0, len(final_pending), batch_size):
        batch = final_pending[start : start + batch_size]
        outputs, retries = _complete_group_with_json_retries(
            client, [messages for _, messages in batch], pipeline.response_schema,
            batch_retries, pipeline.active_items,
        )
        retried_malformed += retries
        for (index, _), completion in zip(batch, outputs):
            final_completions[index].append(completion)

    _log(
        f"final_generate requests={len(final_pending)} "
        f"retries={retried_malformed - final_retry_start} "
        f"seconds={time.perf_counter() - phase_started:.3f}"
    )

    phase_started = time.perf_counter()
    rows = [
        pipeline.finalize(record, final_completions[index], final_contexts[index])
        for index, record in enumerate(records)
    ]
    changed_records = sum(bool(row.postprocess_changes) for row in rows)
    changed_cells = sum(len(row.postprocess_changes) for row in rows)
    changed_label_cells = sum(
        int(change["label_changed"])
        for row in rows
        for change in row.postprocess_changes
    )
    _log(
        f"postprocess policy={pipeline.frozen_rule_set or 'none'} "
        f"changed_records={changed_records} changed_items={changed_cells} "
        f"changed_label_cells={changed_label_cells}"
    )
    _log(f"finalize records={len(rows)} seconds={time.perf_counter() - phase_started:.3f}")
    return prediction_rows(rows), retried_malformed, sum(
        len(row.parse_errors) for row in rows
    )


def main() -> int:
    total_started = time.perf_counter()
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--batch-size", type=int, default=int(RUNTIME["batch_size"]))
    args = parser.parse_args()
    data_dir = Path(os.environ["PPS_DATA_DIR"])
    output_dir = Path(os.environ["PPS_OUTPUT_DIR"])
    model_dir = os.environ["PPS_MODEL_DIR"]
    phase_started = time.perf_counter()
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
    _log(
        f"input_load records={len(records)} documents="
        f"{sum(len(record['docs']) for record in records)} "
        f"seconds={time.perf_counter() - phase_started:.3f}"
    )
    client = MockClient() if args.mock else VLLMClient(model_dir)
    grouping = str(RUNTIME.get("grouping", "all"))
    staged_mode = str(RUNTIME_CONFIG.get("staged_run", {}).get("mode", "off"))
    specialist_mode = str(
        RUNTIME_CONFIG.get("specialist_run", {}).get("mode", "off")
    )
    batch_retries = int(RUNTIME.get("batch_retries", 2))
    if batch_retries < 0:
        raise ValueError("runtime.batch_retries must be non-negative")
    groups = groups_for_scheme(grouping) if grouping != "all" else ()
    if staged_mode not in {"off", "fact_inventory_full_final_v1"}:
        raise ValueError(f"unsupported submission staged mode: {staged_mode}")
    if specialist_mode not in {"off", "replace_items_v1"}:
        raise ValueError(f"unsupported submission specialist mode: {specialist_mode}")
    if staged_mode != "off" and groups:
        raise ValueError("source-first submission mode does not support item grouping")
    if specialist_mode != "off" and (staged_mode != "off" or groups):
        raise ValueError("specialist replacement cannot be combined with staging or grouping")

    pipeline = build_submission_pipeline(
        item_table=item_table,
        client=client,
        decision_cards=decision_cards,
        competition_products=competition_products,
    )
    retried_malformed = 0

    if specialist_mode == "replace_items_v1":
        output_rows, retried_malformed, unrecovered = _specialist_composite_rows(
            records, item_table, pipeline, competition_products, client,
            args.batch_size, batch_retries,
        )
    elif staged_mode == "fact_inventory_full_final_v1":
        output_rows, retried_malformed, unrecovered = _source_first_full_final_rows(
            records, pipeline, client, args.batch_size, batch_retries,
        )
    elif not groups:
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
        group_pipelines = {
            group.group_id: build_submission_pipeline(
                item_table=item_table,
                client=client,
                decision_cards=decision_cards,
                competition_products=competition_products,
                active_items=group.items,
            )
            for group in groups
        }
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
    _log(
        f"malformed structured candidates retried={retried_malformed}; "
        f"unrecovered passes defaulted_to_zero={unrecovered}",
    )
    phase_started = time.perf_counter()
    destination = output_dir / "submission.csv"
    write_submission(output_rows, destination)
    validation = validate_submission(destination, records)
    if not validation.passed:
        raise RuntimeError("submission validation failed: " + "; ".join(validation.errors[:5]))
    _log(
        f"csv_write_validate rows={len(output_rows)} warnings={len(validation.warnings)} "
        f"seconds={time.perf_counter() - phase_started:.3f}"
    )
    _log(f"complete total_seconds={time.perf_counter() - total_started:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
