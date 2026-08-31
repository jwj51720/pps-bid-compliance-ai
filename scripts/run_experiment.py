#!/usr/bin/env python3
"""Run a resumable local experiment and evaluate a submission-shaped result."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import ExperimentConfig, load_config
from src.data import load_item_table, load_records
from src.evaluate import evaluate_submission, write_rows
from src.external.openrouter import MockClient, OpenRouterClient
from src.pipeline import BaselinePipeline, Prediction, PredictionError, judgment_to_row
from src.submission import validate_submission, write_submission


def _logger(output_dir: Path) -> logging.Logger:
    logger = logging.getLogger("experiment")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    for handler in (logging.StreamHandler(), logging.FileHandler(output_dir / "run.log", encoding="utf-8")):
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _source_hashes() -> dict[str, str]:
    paths = sorted((ROOT / "src").rglob("*.py")) + [Path(__file__).resolve()]
    return {str(path.relative_to(ROOT)): _sha256(path) for path in paths}


def _run_signature(
    config: ExperimentConfig,
    mock: bool,
    *,
    limit: int | None,
    selected_ids: list[str] | None,
) -> str:
    identity = {
        "config": config.raw,
        "effective_model": "mock" if mock else config.llm.model,
        "input_sha256": _sha256(config.data.input_path),
        "item_table_sha256": _sha256(config.data.item_table_path),
        "reference_sha256": _sha256(config.reference_path) if config.reference_path else None,
        "source_sha256": _source_hashes(),
        "selection": {"limit": limit, "ids": selected_ids},
    }
    encoded = json.dumps(identity, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _git_commit() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _prediction_to_json(prediction: Prediction) -> dict[str, Any]:
    return {
        "id": prediction.record_id,
        "judgment": prediction.judgment,
        "row": judgment_to_row(prediction.record_id, prediction.judgment),
        "raw_response": prediction.raw_response,
        "model": prediction.model,
        "latency_seconds": prediction.latency_seconds,
        "usage": prediction.usage,
        "finish_reason": prediction.finish_reason,
        "pass_judgments": list(prediction.pass_judgments),
        "parse_errors": list(prediction.parse_errors),
    }


def _load_checkpoint(path: Path) -> dict[str, dict[str, Any]]:
    checkpoint: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return checkpoint
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
                checkpoint[value["id"]] = value
            except (json.JSONDecodeError, KeyError) as exc:
                raise ValueError(f"invalid checkpoint line {line_number}: {exc}") from exc
    return checkpoint


def _load_selected_ids(path: str | None) -> list[str] | None:
    if path is None:
        return None
    source = Path(path)
    value = json.loads(source.read_text(encoding="utf-8"))
    ids = value.get("ids") if isinstance(value, dict) else value
    if not isinstance(ids, list) or not ids or not all(isinstance(item, str) for item in ids):
        raise ValueError("IDs file must contain a non-empty JSON string list or an object with ids")
    if len(ids) != len(set(ids)):
        raise ValueError("IDs file contains duplicate IDs")
    return ids


def _make_client(config: ExperimentConfig, mock: bool):
    if mock:
        return MockClient()
    api_key = os.environ.get(config.llm.api_key_env, "")
    if not api_key:
        raise RuntimeError(f"missing environment variable: {config.llm.api_key_env}")
    return OpenRouterClient(
        api_key=api_key,
        api_url=config.llm.api_url,
        model=config.llm.model,
        temperature=config.llm.temperature,
        max_tokens=config.llm.max_tokens,
        seed=config.llm.seed,
        timeout_seconds=config.llm.timeout_seconds,
        request_retries=config.llm.request_retries,
        provider_sort=config.llm.provider_sort,
        require_parameters=config.llm.require_parameters,
        min_request_interval_seconds=config.llm.min_request_interval_seconds,
    )


def _make_token_counter(config: ExperimentConfig, mock: bool):
    if (
        mock
        or not config.overflow_split_enabled
        or config.max_document_chars is not None
        or config.context_strategy == "split"
    ):
        return None
    from transformers import AutoTokenizer

    tokenizer_source = os.environ.get("PPS_MODEL_DIR") or config.llm.model
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_source)

    def count_tokens(messages: list[dict[str, str]]) -> int:
        encoded = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True
        )
        token_ids = encoded["input_ids"] if hasattr(encoded, "keys") else encoded
        return len(token_ids)

    return count_tokens


def _predict_with_retries(
    pipeline: BaselinePipeline,
    record: dict[str, Any],
    attempts: int,
) -> tuple[Prediction | None, list[dict[str, Any]]]:
    failed_attempts: list[dict[str, Any]] = []
    for attempt in range(1, attempts + 1):
        try:
            return pipeline.predict(record), failed_attempts
        except Exception as exc:
            failed_attempts.append(
                {
                    "id": record["id"],
                    "attempt": attempt,
                    "error": str(exc),
                    "raw_response": exc.raw_response
                    if isinstance(exc, PredictionError) and exc.raw_response is not None
                    else None,
                }
            )
    return None, failed_attempts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--ids-file", help="JSON list, or object with ids, selecting input records")
    parser.add_argument("--mock", action="store_true")
    parser.add_argument(
        "--dump-inputs",
        action="store_true",
        help="write every final chat message/pass to inputs.jsonl before model calls",
    )
    parser.add_argument("--fresh", action="store_true", help="discard the existing prediction checkpoint")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    config = load_config(args.config)
    output_dir = config.output_dir if not args.mock else config.output_dir.with_name(config.output_dir.name + "-mock")
    output_dir.mkdir(parents=True, exist_ok=True)
    logger = _logger(output_dir)
    checkpoint_path = output_dir / "predictions.jsonl"
    checkpoint_meta_path = output_dir / "checkpoint_meta.json"
    failed_response_path = output_dir / "failed_responses.jsonl"
    if args.fresh and checkpoint_path.exists():
        checkpoint_path.unlink()
    if args.fresh and checkpoint_meta_path.exists():
        checkpoint_meta_path.unlink()
    if args.fresh and failed_response_path.exists():
        failed_response_path.unlink()
    selected_ids = _load_selected_ids(args.ids_file)
    effective_limit = args.limit if args.limit is not None else config.local_limit
    if selected_ids is not None and effective_limit is not None:
        source = "--limit" if args.limit is not None else "run.local_limit"
        raise ValueError(f"--ids-file and {source} are mutually exclusive")
    if args.limit is not None and config.local_limit is not None:
        logger.info("command-line --limit overrides run.local_limit=%d", config.local_limit)
    run_signature = _run_signature(
        config,
        args.mock,
        limit=effective_limit,
        selected_ids=selected_ids,
    )
    if checkpoint_path.exists():
        if not checkpoint_meta_path.exists():
            raise RuntimeError("checkpoint metadata is missing; use --fresh to restart safely")
        checkpoint_meta = json.loads(checkpoint_meta_path.read_text(encoding="utf-8"))
        if checkpoint_meta.get("run_signature") != run_signature:
            raise RuntimeError("checkpoint does not match current code/config/data; use --fresh")
    else:
        checkpoint_meta_path.write_text(
            json.dumps({"run_signature": run_signature}, indent=2) + "\n", encoding="utf-8"
        )
    checkpoint = _load_checkpoint(checkpoint_path) if config.resume else {}
    records = load_records(config.data.input_path)
    if selected_ids is not None:
        records_by_id = {record["id"]: record for record in records}
        missing_ids = [record_id for record_id in selected_ids if record_id not in records_by_id]
        if missing_ids:
            raise ValueError(f"IDs file contains IDs absent from input: {missing_ids[:10]}")
        records = [records_by_id[record_id] for record_id in selected_ids]
    elif effective_limit is not None:
        records = records[:effective_limit]
    item_table = load_item_table(config.data.item_table_path)
    client = _make_client(config, args.mock)
    reference_text = (
        config.reference_path.read_text(encoding="utf-8") if config.reference_path else None
    )
    pipeline = BaselinePipeline(
        item_table=item_table,
        client=client,
        max_document_chars=config.max_document_chars,
        prompt_mode=config.prompt_mode,
        include_normalized_facts=config.include_normalized_facts,
        context_strategy=config.context_strategy,
        notice_anchor_chars=config.notice_anchor_chars,
        overflow_split_enabled=config.overflow_split_enabled,
        count_tokens=_make_token_counter(config, args.mock),
        prompt_budget_tokens=config.max_model_len - config.output_reserve_tokens,
        reference_text=reference_text,
    )
    shutil.copy2(config.path, output_dir / "config.yaml")
    if config.reference_path:
        shutil.copy2(config.reference_path, output_dir / "reference_context.txt")
    if args.dump_inputs:
        dump_path = output_dir / "inputs.jsonl"
        with dump_path.open("w", encoding="utf-8") as handle:
            for record in records:
                for pass_index, context in enumerate(pipeline.contexts_for_record(record), 1):
                    messages = pipeline.messages_for_context(record, context)
                    handle.write(
                        json.dumps(
                            {
                                "id": record["id"],
                                "pass_index": pass_index,
                                "token_count": pipeline.count_tokens(messages)
                                if pipeline.count_tokens
                                else None,
                                "messages": messages,
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
    started = time.monotonic()
    failures: list[dict[str, str]] = []
    logger.info(
        "experiment=%s records=%d model=%s resumed=%d concurrency=%d",
        config.experiment_id,
        len(records),
        getattr(client, "model", config.llm.model),
        len(checkpoint),
        config.concurrency,
    )

    pending = [
        (position, record)
        for position, record in enumerate(records, 1)
        if record["id"] not in checkpoint
    ]
    for position, record in enumerate(records, 1):
        if record["id"] in checkpoint:
            logger.info("[%d/%d] %s cached", position, len(records), record["id"])

    with checkpoint_path.open("a", encoding="utf-8") as checkpoint_handle:
        with ThreadPoolExecutor(max_workers=config.concurrency) as executor:
            futures = {
                executor.submit(
                    _predict_with_retries,
                    pipeline,
                    record,
                    config.llm.prediction_attempts,
                ): (position, record)
                for position, record in pending
            }
            for future in as_completed(futures):
                position, record = futures[future]
                prediction, failed_attempts = future.result()
                if failed_attempts:
                    with failed_response_path.open("a", encoding="utf-8") as failed_handle:
                        for failed_attempt in failed_attempts:
                            failed_handle.write(json.dumps(failed_attempt, ensure_ascii=False) + "\n")
                            logger.warning(
                                "[%d/%d] %s attempt %d/%d failed: %s",
                                position,
                                len(records),
                                record["id"],
                                failed_attempt["attempt"],
                                config.llm.prediction_attempts,
                                failed_attempt["error"],
                            )
                if prediction is None:
                    failures.append({"id": record["id"], "error": failed_attempts[-1]["error"]})
                    continue
                value = _prediction_to_json(prediction)
                checkpoint[record["id"]] = value
                checkpoint_handle.write(json.dumps(value, ensure_ascii=False) + "\n")
                checkpoint_handle.flush()
                logger.info(
                    "[%d/%d] %s %.2fs prompt=%s completion=%s",
                    position,
                    len(records),
                    record["id"],
                    prediction.latency_seconds,
                    prediction.usage.get("prompt_tokens", "?"),
                    prediction.usage.get("completion_tokens", "?"),
                )

    if failures:
        (output_dir / "failures.json").write_text(
            json.dumps(failures, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        raise RuntimeError(f"{len(failures)} predictions failed; rerun to resume")

    ordered_values = [checkpoint[record["id"]] for record in records]
    submission_path = output_dir / "submission.csv"
    write_submission([value["row"] for value in ordered_values], submission_path)
    validation = validate_submission(submission_path, records)
    (output_dir / "validation.json").write_text(
        json.dumps(
            {"passed": validation.passed, "errors": validation.errors, "warnings": validation.warnings},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if not validation.passed:
        raise RuntimeError(f"submission validation failed: {validation.errors[:5]}")

    metrics: dict[str, Any] | None = None
    if config.data.labels_path is not None:
        metrics, per_item, errors = evaluate_submission(
            submission_path,
            config.data.labels_path,
            records,
        )
        metrics = {"experiment_id": config.experiment_id, **metrics}
        (output_dir / "metrics.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        write_rows(output_dir / "per_item_metrics.csv", per_item)
        write_rows(output_dir / "errors.csv", errors)

    usage_keys = ("prompt_tokens", "completion_tokens", "total_tokens", "cost")
    usage = {
        key: sum(float(value.get("usage", {}).get(key, 0) or 0) for value in ordered_values)
        for key in usage_keys
    }
    run_meta = {
        "experiment_id": config.experiment_id,
        "git_commit": _git_commit(),
        "input": str(config.data.input_path.relative_to(ROOT)),
        "input_sha256": _sha256(config.data.input_path),
        "labels_sha256": _sha256(config.data.labels_path) if config.data.labels_path else None,
        "run_signature": run_signature,
        "source_sha256": _source_hashes(),
        "input_count": len(records),
        "local_limit": config.local_limit,
        "derived_data": list(config.derived_data),
        "reference_path": str(config.reference_path.relative_to(ROOT))
        if config.reference_path
        else None,
        "reference_sha256": _sha256(config.reference_path) if config.reference_path else None,
        "llm_provider": "mock" if args.mock else config.llm.provider,
        "model": getattr(client, "model", config.llm.model),
        "rag_enabled": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "runtime_seconds": round(time.monotonic() - started, 3),
        "usage": usage,
        "validation_warning_count": len(validation.warnings),
        "macro_f1": metrics["leaderboard_metric"]["macro_f1"] if metrics else None,
    }
    (output_dir / "run_meta.json").write_text(
        json.dumps(run_meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    logger.info("completed in %.1fs macro_f1=%s", run_meta["runtime_seconds"], run_meta["macro_f1"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
