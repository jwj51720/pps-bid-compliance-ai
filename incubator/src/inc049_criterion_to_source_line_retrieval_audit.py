#!/usr/bin/env python3
"""BGE audit: published item criterion/metadata to intact source lines only."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

import inc001_simple_joint24 as common
from inc048_source_fragment_ontology_audit import fragments


ROOT = Path(__file__).resolve().parents[2]
RANKS = (1, 3, 5, 10, 20)
TOKEN = re.compile(r"[0-9A-Za-z가-힣]+")


def embed_request(config: dict[str, Any], values: list[str], input_type: str) -> tuple[list[list[float]], dict[str, Any]]:
    key = os.environ.get(config["api_key_env"], "")
    if not key:
        raise RuntimeError(f"missing {config['api_key_env']}")
    payload = {"model": config["model"], "input": values, "encoding_format": "float", "input_type": input_type}
    last = "unknown"
    for attempt in range(config["request_retries"] + 1):
        try:
            response = requests.post(config["api_url"], headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json=payload, timeout=config["timeout_seconds"])
            if response.ok:
                body = response.json()
                rows = sorted(body["data"], key=lambda row: row["index"])
                vectors = [row["embedding"] for row in rows]
                if len(vectors) != len(values):
                    raise RuntimeError("embedding response count mismatch")
                return vectors, body.get("usage", {})
            last = f"HTTP {response.status_code}: {response.text[:240]}"
        except requests.RequestException as exc:
            last = f"{type(exc).__name__}: {exc}"
        if attempt < config["request_retries"]:
            time.sleep(2 ** attempt)
    raise RuntimeError(last)


def recursively_embed(config: dict[str, Any], rows: list[dict[str, Any]], input_type: str, usage: list[dict[str, Any]]) -> list[list[float]]:
    """Retry the identical ordered input; bisect only on provider-size failure."""
    try:
        vectors, row_usage = embed_request(config, [row["text"] for row in rows], input_type)
        usage.append({"count": len(rows), "usage": row_usage, "split": False})
        return vectors
    except RuntimeError as exc:
        if len(rows) == 1:
            raise RuntimeError(f"unembeddable intact input {rows[0]['key']}: {exc}") from exc
        midpoint = len(rows) // 2
        usage.append({"count": len(rows), "error": str(exc), "split": True})
        return recursively_embed(config, rows[:midpoint], input_type, usage) + recursively_embed(config, rows[midpoint:], input_type, usage)


def criterion_query(item: str, definition: dict[str, Any], meta: dict[str, Any] | None) -> str:
    rows = [
        f"검사항목 {item}: {definition['항목명']}",
        f"국가계약: {definition.get('국가계약법', '')}",
        f"지방계약: {definition.get('지방계약법', '')}",
        f"비고: {definition.get('비고', '')}",
        "이 항목의 위반 여부를 판단하는 공고 원문 근거를 찾는다.",
    ]
    if meta is not None:
        rows.append("공고 메타: " + json.dumps(meta, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return "\n".join(rows)


def cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


def lexical_score(query: str, text: str) -> float:
    query_terms, text_terms = set(TOKEN.findall(query.lower())), set(TOKEN.findall(text.lower()))
    return len(query_terms & text_terms) / len(query_terms | text_terms) if query_terms or text_terms else 0.0


def rank_of_evidence(lines: list[dict[str, Any]], scores: list[float], evidence: str) -> int | None:
    ordered = sorted(range(len(lines)), key=lambda index: (-scores[index], lines[index]["key"]))
    for rank, index in enumerate(ordered, 1):
        if evidence in lines[index]["text"]:
            return rank
    return None


def summarize(rows: list[dict[str, Any]], representation: str) -> dict[str, Any]:
    current = [row for row in rows if row["representation"] == representation]
    ranks = [row["rank"] for row in current if row["rank"] is not None]
    total = len(current)
    ordered = sorted(ranks)
    def quantile(value: float) -> int | None:
        return ordered[math.ceil(value * len(ordered)) - 1] if ordered else None
    per_item = []
    for item in common.ITEMS:
        subset = [row for row in current if row["item"] == item]
        if not subset:
            continue
        item_ranks = [row["rank"] for row in subset if row["rank"] is not None]
        per_item.append({"item": item, "eligible": len(subset), "found": len(item_ranks), "mrr": sum(1 / rank for rank in item_ranks) / len(subset), **{f"recall_at_{limit}": sum(rank <= limit for rank in item_ranks) / len(subset) for limit in RANKS}})
    return {"eligible": total, "found": len(ranks), "mrr": sum(1 / rank for rank in ranks) / total if total else None, **{f"recall_at_{limit}": sum(rank <= limit for rank in ranks) / total if total else None for limit in RANKS}, "rank_quantiles": {"p50": quantile(.50), "p90": quantile(.90), "p95": quantile(.95), "max": max(ordered) if ordered else None}, "per_item": per_item}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="incubator/configs/inc049_criterion_to_source_line_retrieval_audit.json")
    parser.add_argument("--mode", choices=("preflight", "run"), default="preflight")
    parser.add_argument("--workers", type=int)
    args = parser.parse_args()
    config = json.loads((ROOT / args.config).read_text(encoding="utf-8"))
    load_dotenv(ROOT / ".env")
    output = ROOT / "incubator/runs" / config["experiment_id"]
    output.mkdir(parents=True, exist_ok=True)
    data = ROOT / config["data_root"]
    records = common.read_jsonl_gz(data / "dev.jsonl.gz")
    labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}
    table = json.loads((data / "data/항목표.json").read_text(encoding="utf-8"))["항목"]
    lines_by_id: dict[str, list[dict[str, Any]]] = {}
    inputs = []
    for record in records:
        lines = [{"key": f"{record['id']}:{row['doc_id']}:{row['line_id']}", "id": record["id"], "doc_id": row["doc_id"], "doc_type": row["doc_type"], "line_id": row["line_id"], "text": row["text"], "selectable": row["selectable"]} for row in fragments(record) if row["kind"] == "line"]
        lines_by_id[record["id"]] = lines
        inputs.extend(lines)
    queries = []
    for record in records:
        for item, definition in table.items():
            for representation, meta in (("criterion", None), ("criterion_plus_metadata", record["meta"])):
                queries.append({"key": f"{record['id']}:{item}:{representation}", "id": record["id"], "item": item, "representation": representation, "text": criterion_query(item, definition, meta)})
    eligible = [{"id": record["id"], "item": item, "evidence": labels[record["id"]][f"e{item[1:]}"]} for record in records for item in common.ITEMS if labels[record["id"]][item] == "1" and labels[record["id"]][f"e{item[1:]}"]]
    plan = {"experiment_id": config["experiment_id"], "protocol": "incubator/docs/inc049_criterion_to_source_line_retrieval_protocol.md", "source_line_count": len(inputs), "query_count": len(queries), "eligible_evidence_pairs": len(eligible), "initial_batch_size": config["initial_batch_size"], "source_sha256": {"dev": common.sha256_file(data / "dev.jsonl.gz"), "labels": common.sha256_file(data / "dev_labels.csv"), "item_table": common.sha256_file(data / "data/항목표.json")}, "query_sha256": common.sha256_text(json.dumps(queries, ensure_ascii=False, sort_keys=True))}
    common.write_json(output / "config.json", config)
    common.write_json(output / "plan.json", plan)
    if args.mode == "preflight":
        print(json.dumps({"status": "preflight_ok", **plan}, ensure_ascii=False, indent=2))
        return
    targets_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for target in eligible:
        targets_by_id[target["id"]].append(target)
    queries_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for query in queries:
        queries_by_id[query["id"]].append(query)

    def process_notice(record_id: str) -> dict[str, Any]:
        checkpoint = output / "notices" / f"{record_id}.json"
        if checkpoint.exists():
            return json.loads(checkpoint.read_text(encoding="utf-8"))
        lines = lines_by_id[record_id]
        source_usage: list[dict[str, Any]] = []
        source_vectors: list[list[float]] = []
        for start in range(0, len(lines), config["initial_batch_size"]):
            source_vectors.extend(recursively_embed(config, lines[start:start + config["initial_batch_size"]], "search_document", source_usage))
        notice_queries = queries_by_id[record_id]
        query_usage: list[dict[str, Any]] = []
        query_vectors = recursively_embed(config, notice_queries, "search_query", query_usage)
        vectors_by_line = {row["key"]: vector for row, vector in zip(lines, source_vectors)}
        vectors_by_query = {row["key"]: vector for row, vector in zip(notice_queries, query_vectors)}
        query_by_item = {(row["item"], row["representation"]): row for row in notice_queries}
        rows = []
        for target in targets_by_id.get(record_id, []):
            for representation in ("lexical", "criterion", "criterion_plus_metadata"):
                query = query_by_item[(target["item"], "criterion" if representation == "lexical" else representation)]
                scores = [lexical_score(query["text"], line["text"]) for line in lines] if representation == "lexical" else [cosine(vectors_by_query[query["key"]], vectors_by_line[line["key"]]) for line in lines]
                rows.append({**target, "representation": representation, "rank": rank_of_evidence(lines, scores, target["evidence"]), "line_count": len(lines)})
        entry = {"id": record_id, "success": True, "rank_rows": rows, "source_requests": source_usage, "query_requests": query_usage}
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        common.write_json(checkpoint, entry)
        return entry

    entries = []
    workers = args.workers or config["workers"]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(process_notice, record["id"]): record["id"] for record in records}
        for completed, future in enumerate(as_completed(futures), 1):
            record_id = futures[future]
            try:
                entries.append(future.result())
            except Exception as exc:
                entry = {"id": record_id, "success": False, "error": f"{type(exc).__name__}: {exc}"}
                common.write_json(output / "notices" / f"{record_id}.json", entry)
                entries.append(entry)
            print(f"notices={completed}/{len(records)}", flush=True)
    failures = [entry for entry in entries if not entry["success"]]
    if failures:
        common.write_json(output / "failures.json", failures)
        raise RuntimeError(f"notice embedding failures: {len(failures)}")
    rank_rows = [row for entry in entries for row in entry["rank_rows"]]
    source_usage = [row for entry in entries for row in entry["source_requests"]]
    query_usage = [row for entry in entries for row in entry["query_requests"]]
    token_count = sum(int(row.get("usage", {}).get("total_tokens", 0) or 0) for row in source_usage + query_usage)
    cost = sum(float(row.get("usage", {}).get("cost", 0) or 0) for row in source_usage + query_usage)
    if cost > config["max_cost_usd"]:
        raise RuntimeError(f"reported cost ceiling exceeded: {cost:.6f}")
    summaries = {name: summarize(rank_rows, name) for name in ("lexical", "criterion", "criterion_plus_metadata")}
    metadata = summaries["criterion_plus_metadata"]
    report = {**plan, "embedding_total_tokens": token_count, "reported_cost_usd": cost, "source_requests": source_usage, "query_requests": query_usage, "summaries": summaries, "advance_gate": {"metadata_mrr_higher_than_lexical": metadata["mrr"] > summaries["lexical"]["mrr"], "metadata_recall_at_20_at_least_0_90": metadata["recall_at_20"] >= .90, "pass": metadata["mrr"] > summaries["lexical"]["mrr"] and metadata["recall_at_20"] >= .90}}
    common.write_jsonl(output / "rank_rows.jsonl", rank_rows)
    common.write_json(output / "report.json", report)
    print(json.dumps({"status": "complete", "reported_cost_usd": cost, "summaries": summaries, "advance_gate": report["advance_gate"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
