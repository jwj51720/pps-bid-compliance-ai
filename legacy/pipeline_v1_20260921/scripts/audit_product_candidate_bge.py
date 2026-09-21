#!/usr/bin/env python3
"""Audit organizer-CSV-only BGE product candidate retrieval without labels in ranking."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data import competition_product_fact, load_competition_product_index


CODE = re.compile(r"\d{6,10}")
BRACKET_CODE = re.compile(r"\[\s*\d{6,10}\s*\]")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_records(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def product_query(record: dict[str, Any], announcement_chars: int) -> str:
    """Build a label-blind purchased-object query from organizer-provided fields."""
    meta = record["meta"]
    raw_names = str(meta.get("세부품명번호목록") or "미기재")
    names = CODE.sub(" ", BRACKET_CODE.sub(" ", raw_names))
    announcement = next(
        (doc["text"] for doc in record["docs"] if doc["type"] == "공고문"),
        record["docs"][0]["text"] if record["docs"] else "",
    )
    return (
        f"업무구분: {meta.get('업무구분') or '미입력'}\n"
        f"세부품명 이름: {names.strip()}\n"
        f"공고 시작:\n{announcement[:announcement_chars]}"
    )


def product_chunk_queries(
    record: dict[str, Any], chunk_chars: int, overlap_chars: int, max_chunks: int
) -> list[str]:
    """Create fixed, label-blind source chunks in document-round-robin order."""
    meta = record["meta"]
    raw_names = str(meta.get("세부품명번호목록") or "미기재")
    names = CODE.sub(" ", BRACKET_CODE.sub(" ", raw_names)).strip()
    prefix = (
        f"업무구분: {meta.get('업무구분') or '미입력'}\n"
        f"세부품명 이름: {names}\n"
    )
    step = chunk_chars - overlap_chars
    chunks_by_document: list[list[str]] = []
    for document in record["docs"]:
        text = str(document["text"])
        chunks_by_document.append([
            prefix + f"문서유형: {document['type']}\n원문 조각:\n" + text[start:start + chunk_chars]
            for start in range(0, len(text), step)
        ] or [prefix + f"문서유형: {document['type']}\n원문 조각:\n"])
    selected: list[str] = []
    ordinal = 0
    while len(selected) < max_chunks:
        added = False
        for chunks in chunks_by_document:
            if ordinal < len(chunks):
                selected.append(chunks[ordinal])
                added = True
                if len(selected) == max_chunks:
                    break
        if not added:
            break
        ordinal += 1
    return selected or [prefix]


def catalog_text(row: dict[str, str]) -> str:
    return (
        f"세부품명: {row.get('세부품명', '')}\n"
        f"제품명: {row.get('제품명', '')}\n"
        f"적용조건: {row.get('특이사항', '') or '별도 조건 없음'}"
    )


def embed(api_key: str, values: list[str], model: str) -> tuple[list[list[float]], dict[str, Any]]:
    failure = ""
    for attempt in range(3):
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/embeddings",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "input": values, "encoding_format": "float"},
                timeout=180,
            )
            if response.ok:
                payload = response.json()
                ordered = sorted(payload["data"], key=lambda row: row["index"])
                return [row["embedding"] for row in ordered], payload.get("usage", {})
            failure = f"HTTP {response.status_code}: {response.text[:500]}"
            if response.status_code < 500 and response.status_code != 429:
                raise RuntimeError(f"BGE request failed: {failure}")
        except requests.RequestException as error:
            failure = f"{type(error).__name__}: {error}"
        if attempt == 2:
            break
        time.sleep(1 + attempt)
    raise RuntimeError(f"BGE request failed after 3 attempts: {failure}")


def batch_embed(
    api_key: str, values: list[str], model: str, batch_size: int
) -> tuple[list[list[float]], list[dict[str, Any]]]:
    vectors: list[list[float]] = []
    usages: list[dict[str, Any]] = []
    for start in range(0, len(values), batch_size):
        batch, usage = embed(api_key, values[start:start + batch_size], model)
        vectors.extend(batch)
        usages.append(usage)
    return vectors, usages


def cosine(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", type=Path, default=Path("data/raw/open/dev.jsonl.gz"))
    parser.add_argument("--labels", type=Path, default=Path("data/raw/open/dev_labels.csv"))
    parser.add_argument(
        "--products", type=Path,
        default=Path("data/derived/competition_products_v1.json"),
    )
    parser.add_argument("--model", default="baai/bge-m3")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--announcement-chars", type=int, default=1600)
    parser.add_argument(
        "--query-mode", choices=("headline_v1", "source_chunks_v2"),
        default="headline_v1",
    )
    parser.add_argument("--chunk-chars", type=int, default=900)
    parser.add_argument("--overlap-chars", type=int, default=150)
    parser.add_argument("--max-chunks", type=int, default=12)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("outputs/product-candidate-bge-capability-20260918"),
    )
    args = parser.parse_args()
    if args.batch_size < 1 or args.announcement_chars < 1 or args.top_k < 1:
        raise ValueError("batch size, announcement chars, and top-k must be positive")
    if not 0 <= args.overlap_chars < args.chunk_chars or args.max_chunks < 1:
        raise ValueError("chunk overlap must be smaller than chunk size and max-chunks positive")

    records = load_records(args.dev)
    index = load_competition_product_index(args.products)
    catalog = list(index.items())
    queries_by_record = [
        [product_query(record, args.announcement_chars)]
        if args.query_mode == "headline_v1"
        else product_chunk_queries(
            record, args.chunk_chars, args.overlap_chars, args.max_chunks
        )
        for record in records
    ]
    queries = [query for record_queries in queries_by_record for query in record_queries]
    candidate_texts = [catalog_text(row) for _, row in catalog]

    load_dotenv(ROOT / ".env")
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required")
    catalog_vectors, catalog_usage = batch_embed(
        api_key, candidate_texts, args.model, args.batch_size
    )
    query_vectors, query_usage = batch_embed(api_key, queries, args.model, args.batch_size)

    labels: dict[str, dict[str, str]] = {}
    with args.labels.open(encoding="utf-8", newline="") as handle:
        labels = {row["id"]: row for row in csv.DictReader(handle)}
    panels = {
        name: set(json.loads((ROOT / "configs" / filename).read_text())["ids"])
        for name, filename in (
            ("fast", "dev_fast_panel_v1.json"),
            ("holdout", "dev_prompt_holdout_v1.json"),
        )
    }

    rows: list[dict[str, Any]] = []
    matched_ranks: list[int] = []
    vector_offset = 0
    for record, record_queries in zip(records, queries_by_record):
        record_vectors = query_vectors[vector_offset:vector_offset + len(record_queries)]
        vector_offset += len(record_queries)
        ranked = sorted(
            (
                (max(cosine(vector, candidate) for vector in record_vectors), position)
                for position, candidate in enumerate(catalog_vectors)
            ),
            reverse=True,
        )[:args.top_k]
        candidates = [
            {
                "rank": rank,
                "score": score,
                "code": catalog[position][0],
                **catalog[position][1],
            }
            for rank, (score, position) in enumerate(ranked, 1)
        ]
        fact = competition_product_fact(record, index)
        targets = {str(product["세부품명번호"]) for product in fact["matched_products"]}
        target_ranks = [
            next((candidate["rank"] for candidate in candidates if candidate["code"] == code), None)
            for code in sorted(targets)
        ]
        matched_ranks.extend(rank for rank in target_ranks if rank is not None)
        rows.append({
            "id": record["id"],
            "queries": record_queries,
            "exact_status": fact["status"],
            "exact_target_codes": sorted(targets),
            "exact_target_ranks_within_top_k": target_ranks,
            "panels": [name for name, ids in panels.items() if record["id"] in ids],
            "v10_gold_for_post_ranking_diagnostic": int(labels[record["id"]]["v10"]),
            "candidates": candidates,
        })

    matched_rows = [row for row in rows if row["exact_target_codes"]]
    target_total = sum(len(row["exact_target_codes"]) for row in matched_rows)
    recall = {
        f"recall_at_{cutoff}": sum(
            rank is not None and rank <= cutoff
            for row in matched_rows for rank in row["exact_target_ranks_within_top_k"]
        ) / target_total if target_total else 0.0
        for cutoff in (1, 3, 5, 10)
    }
    report = {
        "method": "label-blind organizer-CSV-only BGE ranking; labels attached after ranking",
        "model": args.model,
        "dev_sha256": sha256(args.dev),
        "products_sha256": sha256(args.products),
        "record_count": len(records),
        "catalog_count": len(catalog),
        "announcement_chars": args.announcement_chars,
        "query_mode": args.query_mode,
        "chunk_chars": args.chunk_chars,
        "overlap_chars": args.overlap_chars,
        "max_chunks": args.max_chunks,
        "query_count": len(queries),
        "top_k": args.top_k,
        "exact_matched_record_count": len(matched_rows),
        "exact_target_count": target_total,
        "exact_target_recall": recall,
        "usage": {"catalog": catalog_usage, "queries": query_usage},
        "rows": rows,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary = {key: value for key, value in report.items() if key not in {"rows", "usage"}}
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
