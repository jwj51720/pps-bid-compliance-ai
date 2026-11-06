#!/usr/bin/env python3
"""Organizer-law BGE-M3 index and item-query retrieval audit."""
from __future__ import annotations

import argparse
import json
import math
import os
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

import inc001_simple_joint24 as common


def chunks(path: Path, size: int, overlap: int) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    rows = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            boundary = max(text.rfind("\n", start, end), text.rfind(". ", start, end))
            if boundary > start + size // 2:
                end = boundary + 1
        value = text[start:end]
        if value.strip(): rows.append({"source_file": path.name, "start": start, "end": end, "text": value})
        if end == len(text): break
        start = max(end - overlap, start + 1)
    return rows


def embed(config: dict[str, Any], values: list[str]) -> tuple[list[list[float]], dict[str, Any]]:
    key = os.environ.get(config["api_key_env"], "")
    if not key: raise RuntimeError(f"missing {config['api_key_env']}")
    payload = {"model": config["model"], "input": values, "encoding_format": "float", "input_type": "search_document"}
    last = "unknown"
    for attempt in range(config["request_retries"] + 1):
        try:
            response = requests.post(config["api_url"], headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json=payload, timeout=config["timeout_seconds"])
            if response.ok:
                body = response.json(); return [row["embedding"] for row in sorted(body["data"], key=lambda row: row["index"])], body.get("usage", {})
            last = f"HTTP {response.status_code}: {response.text[:240]}"
        except requests.RequestException as exc: last = f"{type(exc).__name__}: {exc}"
        if attempt < config["request_retries"]: time.sleep(2 ** attempt)
    raise RuntimeError(last)


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b)); an = math.sqrt(sum(x * x for x in a)); bn = math.sqrt(sum(y * y for y in b))
    return dot / (an * bn) if an and bn else 0.0


def query_for(item: str, definition: dict[str, Any]) -> str:
    return "\n".join([f"검사항목 {item}: {definition['항목명']}", f"국가계약: {definition.get('국가계약법', '')}", f"지방계약: {definition.get('지방계약법', '')}", f"비고: {definition.get('비고', '')}", "이 위반 여부를 판단하기 위한 적용 요건·예외·금액 기준·명시 의무 법령을 찾는다."])


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--config", default="incubator/configs/inc020_bge_law_rag_audit.json"); args = parser.parse_args()
    root = common.repo_root(); config = json.loads((root / args.config).read_text(encoding="utf-8")); load_dotenv(root / ".env")
    out = root / "incubator/runs" / config["experiment_id"]; out.mkdir(parents=True, exist_ok=True); data = root / config["data_root"]
    files = sorted((data / config["law_directory"]).glob("*.txt")); corpus = [row for path in files for row in chunks(path, config["chunk_chars"], config["overlap_chars"])]
    items = json.loads((data / "data/항목표.json").read_text(encoding="utf-8"))["항목"]; item_ids = list(items); queries = [query_for(item, items[item]) for item in item_ids]
    corpus_embeddings: list[list[float]] = []; usage = []
    for start in range(0, len(corpus), config["batch_size"]):
        vectors, row_usage = embed(
            config, [row["text"] for row in corpus[start:start + config["batch_size"]]]
        )
        corpus_embeddings.extend(vectors)
        usage.append(row_usage)
        print(f"[corpus {min(start + config['batch_size'], len(corpus))}/{len(corpus)}]", flush=True)
    query_embeddings, query_usage = embed(config, queries); usage.append(query_usage)
    retrieval = []
    for item, query, vector in zip(item_ids, queries, query_embeddings):
        ranked = sorted(((cosine(vector, doc), index) for index, doc in enumerate(corpus_embeddings)), reverse=True)[:config["top_k"]]
        retrieval.append({"item": item, "query": query, "results": [{"rank": rank + 1, "score": score, "chunk_index": index, **corpus[index]} for rank, (score, index) in enumerate(ranked)]})
    token_count = sum(int(row.get("total_tokens", 0) or 0) for row in usage)
    report = {"experiment_id": config["experiment_id"], "model": config["model"], "law_file_count": len(files), "chunk_count": len(corpus), "query_count": len(queries), "embedding_usage": usage, "embedding_total_tokens": token_count, "estimated_cost_usd": token_count * 0.01 / 1_000_000, "source_sha256": {path.name: common.sha256_file(path) for path in files}, "item_table_sha256": common.sha256_file(data / "data/항목표.json")}
    if report["estimated_cost_usd"] > config["max_cost_usd"]: raise RuntimeError("embedding cost ceiling exceeded")
    common.write_json(out / "config.json", config); common.write_json(out / "report.json", report); common.write_jsonl(out / "retrieval_manifest.jsonl", retrieval)
    common.write_json(root / "incubator/data/derived/bge_law_index_v1.json", {"model": config["model"], "config": config, "corpus": corpus, "embeddings": corpus_embeddings, "retrieval": retrieval, "source_sha256": report["source_sha256"]})
    print(json.dumps({key: report[key] for key in ("experiment_id", "law_file_count", "chunk_count", "query_count", "embedding_total_tokens", "estimated_cost_usd")}, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
