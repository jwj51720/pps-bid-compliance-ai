"""Label-blind BGE-M3 catalog retrieval matching the frozen L41 algorithm."""

from __future__ import annotations

import math
import time
from typing import Any, Sequence

import requests

from ..config import ProviderConfig


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


def _embed(api_key: str, config: ProviderConfig, values: list[str]) -> tuple[list[list[float]], dict[str, Any]]:
    last_error = "unknown"
    for attempt in range(config.request_retries + 1):
        try:
            response = requests.post(
                config.embedding_url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": config.embedding_model, "input": values, "encoding_format": "float"},
                timeout=config.timeout_seconds,
            )
            if response.ok:
                payload = response.json()
                ordered = sorted(payload["data"], key=lambda row: row["index"])
                return [row["embedding"] for row in ordered], payload.get("usage") or {}
            last_error = f"HTTP {response.status_code}: {response.text[:500]}"
            if response.status_code < 500 and response.status_code != 429:
                break
        except (requests.RequestException, ValueError, KeyError, TypeError) as error:
            last_error = f"{type(error).__name__}: {error}"
        if attempt < config.request_retries:
            time.sleep(2.0**attempt)
    raise RuntimeError(f"BGE embedding failed: {last_error}")


def _batch_embed(
    api_key: str, config: ProviderConfig, values: list[str], batch_size: int,
) -> tuple[list[list[float]], list[dict[str, Any]]]:
    vectors: list[list[float]] = []
    usages: list[dict[str, Any]] = []
    for start in range(0, len(values), batch_size):
        batch, usage = _embed(api_key, config, values[start:start + batch_size])
        vectors.extend(batch)
        usages.append(usage)
    return vectors, usages


def build_reference_rankings(
    records: list[dict[str, Any]], builder: Any, catalog_module: Any,
    provider: ProviderConfig, api_key: str, batch_size: int, top_k: int,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    started = time.monotonic()
    catalog_rows = sorted(builder.catalog.items())
    queries = [catalog_module.notice_target_query(record) for record in records]
    catalog_texts = [catalog_module.catalog_text(code, value) for code, value in catalog_rows]
    catalog_vectors, catalog_usage = _batch_embed(
        api_key, provider, catalog_texts, batch_size,
    )
    query_vectors, query_usage = _batch_embed(api_key, provider, queries, batch_size)
    rankings: dict[str, dict[str, Any]] = {}
    for query, vector, record in zip(queries, query_vectors, records):
        ranked = sorted(
            ((_cosine(vector, candidate), position) for position, candidate in enumerate(catalog_vectors)),
            reverse=True,
        )[:top_k]
        rows = []
        for rank, (score, position) in enumerate(ranked, 1):
            code, value = catalog_rows[position]
            rows.append({
                "rank": rank,
                "score": round(float(score), 6),
                "code": code,
                "product_name": (value.get("제품명") or "").strip(),
                "detail_name": (value.get("세부품명") or "").strip(),
                "special_note": (value.get("특이사항") or "").strip() or None,
            })
        notice_id = str(record["id"])
        rankings[notice_id] = {"id": notice_id, "query": query, "ranked": rows}
    return rankings, {
        "module_id": "reference-l41-bge-m3-v1",
        "model": provider.embedding_model,
        "records": len(records),
        "catalog_rows": len(catalog_rows),
        "top_k": top_k,
        "batch_size": batch_size,
        "seconds": round(time.monotonic() - started, 3),
        "usage": {"catalog": catalog_usage, "queries": query_usage},
        "cross_record_features": False,
    }
