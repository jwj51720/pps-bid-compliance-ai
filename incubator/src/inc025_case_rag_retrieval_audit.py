#!/usr/bin/env python3
"""Pre-registered BGE-M3 leave-one-out case retrieval audit (INC-025)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import numpy as np
import requests
from dotenv import load_dotenv
from transformers import AutoTokenizer

import inc001_simple_joint24 as common


RANKS = (1, 3, 5)


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()


def blocks(text: str) -> list[str]:
    """Return original-text paragraph blocks, retaining separator whitespace."""
    result: list[str] = []
    current: list[str] = []
    for line in text.splitlines(keepends=True):
        current.append(line)
        if not line.strip():
            result.append("".join(current))
            current = []
    if current:
        result.append("".join(current))
    return [part for part in result if part.strip()]


def atomic_units(text: str, tokenizer: Any, limit: int) -> list[str]:
    """Use paragraphs, falling back only to intact source lines when required."""
    result: list[str] = []
    for paragraph in blocks(text):
        if len(tokenizer.encode(paragraph, add_special_tokens=True)) <= limit:
            result.append(paragraph)
            continue
        lines = [line for line in paragraph.splitlines(keepends=True) if line.strip()]
        if not lines:
            lines = [paragraph]
        for line in lines:
            if len(tokenizer.encode(line, add_special_tokens=True)) > limit:
                raise ValueError("atomic_source_line_exceeds_bge_context")
            result.append(line)
    return result


def packs(record: dict[str, Any], tokenizer: Any, limit: int) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for document in sorted(record["docs"], key=lambda doc: (common.DOCUMENT_ORDER[doc["type"]], doc["doc_id"])):
        current: list[str] = []
        # Most units are short source lines.  Summing their independently
        # tokenized lengths is a fast conservative *proposal*; every completed
        # pack below is then admitted with one exact tokenizer call.
        proposed_tokens = 0
        for unit in atomic_units(document["text"], tokenizer, limit):
            unit_tokens = len(tokenizer.encode(unit, add_special_tokens=False))
            if proposed_tokens + unit_tokens + 2 <= limit:
                current.append(unit)
                proposed_tokens += unit_tokens
                continue
            if not current:
                raise ValueError("unreachable_atomic_admission_failure")
            text = "".join(current)
            exact_tokens = len(tokenizer.encode(text, add_special_tokens=True))
            if exact_tokens > limit:
                raise ValueError("proposed_pack_exceeds_exact_bge_context")
            result.append({"doc_id": document["doc_id"], "doc_type": document["type"], "text": text, "tokens": exact_tokens})
            current = [unit]
            proposed_tokens = unit_tokens
        if current:
            text = "".join(current)
            exact_tokens = len(tokenizer.encode(text, add_special_tokens=True))
            if exact_tokens > limit:
                raise ValueError("proposed_pack_exceeds_exact_bge_context")
            result.append({"doc_id": document["doc_id"], "doc_type": document["type"], "text": text, "tokens": exact_tokens})
    return result


def embed(config: dict[str, Any], values: list[str]) -> tuple[list[list[float]], dict[str, Any]]:
    key = os.environ.get(config["api_key_env"], "")
    if not key:
        raise RuntimeError(f"missing {config['api_key_env']}")
    response = requests.post(
        config["api_url"],
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": config["model"], "input": values, "encoding_format": "float"},
        timeout=config["timeout_seconds"],
    )
    if not response.ok:
        raise RuntimeError(f"embedding HTTP {response.status_code}: {response.text[:300]}")
    body = response.json()
    rows = sorted(body["data"], key=lambda row: row["index"])
    vectors = [row["embedding"] for row in rows]
    if len(vectors) != len(values):
        raise RuntimeError("embedding response count mismatch")
    return vectors, body.get("usage", {})


def average_precision(ranked_positive: list[bool]) -> float | None:
    total = sum(ranked_positive)
    if not total:
        return None
    hits = 0
    return sum((hits := hits + int(value)) / (index + 1) for index, value in enumerate(ranked_positive) if value) / total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="incubator/configs/inc025_case_rag_retrieval_audit.json")
    parser.add_argument("--mode", choices=("preflight", "run"), default="preflight")
    args = parser.parse_args()
    root = common.repo_root()
    config = json.loads((root / args.config).read_text(encoding="utf-8"))
    load_dotenv(root / ".env")
    output = root / "incubator/runs" / config["experiment_id"]
    output.mkdir(parents=True, exist_ok=True)
    data = root / config["data_root"]
    records = common.read_jsonl_gz(data / "dev.jsonl.gz")
    labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}
    tokenizer = AutoTokenizer.from_pretrained(config["tokenizer"])
    units: list[dict[str, Any]] = []
    admission_limit = config["model_context_tokens"] - config["observed_transport_overhead_tokens"]
    for record in records:
        for unit in packs(record, tokenizer, admission_limit):
            units.append({"id": record["id"], **unit})
    total_tokens = sum(unit["tokens"] for unit in units)
    projected_cost = total_tokens / 1_000_000 * config["input_cost_per_million_usd"]
    plan = {
        "experiment_id": config["experiment_id"], "preregistration": "incubator/docs/inc025_case_rag_retrieval_preregistration.md",
        "record_count": len(records), "unit_count": len(units), "total_bge_input_tokens": total_tokens,
        "model_context_tokens": config["model_context_tokens"], "observed_transport_overhead_tokens": config["observed_transport_overhead_tokens"],
        "tokenizer_admission_limit": admission_limit, "projected_cost_usd": projected_cost,
        "source_sha256": {"dev": common.sha256_file(data / "dev.jsonl.gz"), "labels": common.sha256_file(data / "dev_labels.csv")},
    }
    common.write_json(output / "config.json", config)
    common.write_json(output / "plan.json", plan)
    if projected_cost > config["max_cost_usd"]:
        raise RuntimeError(f"exact token projected cost exceeds ceiling: {projected_cost:.6f}")
    if args.mode == "preflight":
        print(json.dumps({"status": "preflight_ok", **plan}, ensure_ascii=False, indent=2))
        return
    vectors: list[list[float]] = []
    usage_rows: list[dict[str, Any]] = []
    for start in range(0, len(units), config["batch_size"]):
        batch = units[start:start + config["batch_size"]]
        started = time.monotonic()
        current, usage = embed(config, [unit["text"] for unit in batch])
        vectors.extend(current)
        usage_rows.append({"start": start, "count": len(batch), "usage": usage, "seconds": round(time.monotonic() - started, 3)})
        print(f"[{min(start + len(batch), len(units))}/{len(units)}] embedded", flush=True)
    matrix = np.asarray(vectors, dtype=np.float32)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True).clip(min=1e-12)
    ids = [record["id"] for record in records]
    indices_by_id = {record_id: np.asarray([index for index, unit in enumerate(units) if unit["id"] == record_id]) for record_id in ids}
    notice_similarity = np.full((len(ids), len(ids)), -np.inf, dtype=np.float32)
    for left, record_id in enumerate(ids):
        similarities = matrix[indices_by_id[record_id]] @ matrix.T
        for right, other_id in enumerate(ids):
            if left != right:
                notice_similarity[left, right] = float(similarities[:, indices_by_id[other_id]].max())
    item_metrics = []
    neighbors = []
    for item in common.ITEMS:
        positives = [labels[record_id][item] == "1" for record_id in ids]
        if sum(positives) < 2:
            continue
        ap_values = []
        enrichment = {rank: [] for rank in RANKS}
        for query_index, record_id in enumerate(ids):
            # The positive-query condition asks the useful case-RAG question:
            # can a known violation retrieve other violations of the same
            # item? Negative-example retrieval is a separate future contract.
            if not positives[query_index]:
                continue
            order = [index for index in np.argsort(-notice_similarity[query_index]) if index != query_index]
            ranked = [positives[index] for index in order]
            ap = average_precision(ranked)
            if ap is not None:
                ap_values.append(ap)
            available_base = (sum(positives) - 1) / (len(ids) - 1)
            for rank in RANKS:
                rate = sum(ranked[:rank]) / rank
                enrichment[rank].append(rate / available_base if available_base else 0.0)
            neighbors.append({"item": item, "query_id": record_id, "query_gold": positives[query_index], "top5": [{"id": ids[index], "gold": positives[index], "similarity": round(float(notice_similarity[query_index, index]), 8)} for index in order[:5]]})
        item_metrics.append({"item": item, "positive_count": sum(positives), "loo_average_precision": float(np.mean(ap_values)), **{f"mean_enrichment_at_{rank}": float(np.mean(enrichment[rank])) for rank in RANKS}})
    reported_cost = sum(float(row["usage"].get("cost", 0) or 0) for row in usage_rows)
    report = {**plan, "reported_cost_usd": reported_cost, "embedding_usage": usage_rows, "per_item": item_metrics,
              "items_with_2x_enrichment": sum(any(metric[f"mean_enrichment_at_{rank}"] > 2 for rank in RANKS) for metric in item_metrics)}
    common.write_json(output / "report.json", report)
    common.write_jsonl(output / "neighbors.jsonl", neighbors)
    common.write_json(root / config["derived_output_path"], {"plan": plan, "units": [{key: value for key, value in unit.items() if key != "text"} for unit in units], "vectors": vectors})
    print(json.dumps({"status": "complete", "reported_cost_usd": reported_cost, "items_with_2x_enrichment": report["items_with_2x_enrichment"], "per_item": item_metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
