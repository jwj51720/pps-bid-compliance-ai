#!/usr/bin/env python3
"""S0D: test whether dev evidence examples are retrievable as few-shot precedents.

This is an offline-evaluation retrieval audit.  It never emits predictions,
changes labels, invokes Gemma/Luna, or writes organizer source text to tracked
files.  BGE sees only the static dev precedent corpus and unlabeled query
fragments; each query excludes its own notice from candidate retrieval.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dev_precedent_audit import (
    candidate_indexes_except_notice,
    source_valid_positive_candidates,
)
from src.evidence_audit import locate_evidence
from src.fact_precedent_audit import rank_auc, source_fragments


ITEMS = tuple(f"v{number}" for number in range(1, 25))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _records(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _labels(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return {row["id"]: row for row in csv.DictReader(handle)}


def _fragments(records: list[dict[str, Any]]) -> tuple[list[dict[str, str]], dict[str, list[int]]]:
    fragments: list[dict[str, str]] = []
    by_notice: dict[str, list[int]] = defaultdict(list)
    for record in records:
        for document in record["docs"]:
            for ordinal, text in enumerate(source_fragments(document["text"])):
                by_notice[record["id"]].append(len(fragments))
                fragments.append({
                    "notice_id": record["id"],
                    "doc_id": document["doc_id"],
                    "document_type": document["type"],
                    "ordinal": str(ordinal),
                    "text": text,
                })
    return fragments, by_notice


def _embed(api_key: str, values: list[str], model: str) -> tuple[list[list[float]], list[dict[str, Any]]]:
    vectors: list[list[float]] = []
    usages: list[dict[str, Any]] = []
    for start in range(0, len(values), 12):
        batch = values[start:start + 12]
        failure = ""
        for attempt in range(3):
            try:
                response = requests.post(
                    "https://openrouter.ai/api/v1/embeddings",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model, "input": batch, "encoding_format": "float"},
                    timeout=180,
                )
                if response.ok:
                    payload = response.json()
                    vectors.extend(row["embedding"] for row in sorted(payload["data"], key=lambda row: row["index"]))
                    usages.append(payload.get("usage", {}))
                    break
                failure = f"HTTP {response.status_code}: {response.text[:300]}"
                if response.status_code < 500 and response.status_code != 429:
                    raise RuntimeError(f"BGE failed: {failure}")
            except requests.RequestException as error:
                failure = f"{type(error).__name__}: {error}"
            if attempt == 2:
                raise RuntimeError(f"BGE failed after 3 attempts: {failure}")
            time.sleep(1 + attempt)
    return vectors, usages


def _markdown(report: dict[str, Any]) -> str:
    evaluation = report["evaluation"]
    return "\n".join([
        "# S0D — dev source-grounded precedent retrieval audit",
        "",
        "This ignored artifact contains no copied organizer source text.",
        "",
        "## Coverage",
        f"- source-valid dev positive precedents: {report['coverage']['candidate_count']}",
        f"- covered items: {', '.join(report['coverage']['covered_items'])}",
        f"- query source fragments: {report['coverage']['fragment_count']}",
        "",
        "## Leave-one-notice-out result",
        f"- positive evidence localization: {evaluation['localization_hit_rate']}",
        f"- same document type: {evaluation['same_document_type_rate']}",
        f"- positive-vs-negative score AUC: {evaluation['score_auc']}",
        f"- item AUC >= 0.60: {evaluation['items_auc_at_least_060']}/{evaluation['items_with_auc']}",
        "",
        "## Decision",
        report["decision"],
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", default="data/raw/open/dev.jsonl.gz")
    parser.add_argument("--labels", default="data/raw/open/dev_labels.csv")
    parser.add_argument("--model", default="baai/bge-m3")
    parser.add_argument("--output-dir", default="outputs/dev-precedent-s0d")
    args = parser.parse_args()

    dev_path, labels_path = Path(args.dev), Path(args.labels)
    records, labels = _records(dev_path), _labels(labels_path)
    candidates = source_valid_positive_candidates(records, labels)
    fragments, fragment_indexes = _fragments(records)
    if not candidates:
        raise RuntimeError("no source-valid dev positive precedents")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "run_manifest.json").write_text(json.dumps({
        "audit": "dev_precedent_s0d", "dev": str(dev_path), "dev_sha256": _sha256(dev_path),
        "labels": str(labels_path), "labels_sha256": _sha256(labels_path),
        "embedding_model": args.model, "candidate_count": len(candidates),
        "fragment_count": len(fragments), "self_candidate_excluded": True,
        "query_uses_gold_labels_or_evidence": False,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    load_dotenv(ROOT / ".env")
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required")
    candidate_vectors, candidate_usage = _embed(
        api_key, [f"검토 항목 {row['item']}의 원문 관찰:\n{row['evidence']}" for row in candidates], args.model
    )
    fragment_vectors, fragment_usage = _embed(api_key, [row["text"] for row in fragments], args.model)
    candidate_matrix = np.asarray(candidate_vectors, dtype=np.float32)
    fragment_matrix = np.asarray(fragment_vectors, dtype=np.float32)
    candidate_matrix /= np.maximum(np.linalg.norm(candidate_matrix, axis=1, keepdims=True), 1e-12)
    fragment_matrix /= np.maximum(np.linalg.norm(fragment_matrix, axis=1, keepdims=True), 1e-12)

    positive_scores: list[float] = []
    negative_scores: list[float] = []
    localization_hits = 0
    type_hits = 0
    positive_localizable = 0
    per_item: dict[str, dict[str, Any]] = {}
    selected: list[dict[str, Any]] = []
    for item in ITEMS:
        item_positive: list[float] = []
        item_negative: list[float] = []
        item_localizable = item_localized = item_type = 0
        for record in records:
            candidate_indexes = candidate_indexes_except_notice(candidates, item, record["id"])
            if not candidate_indexes:
                continue
            current_indexes = fragment_indexes[record["id"]]
            score_matrix = fragment_matrix[current_indexes] @ candidate_matrix[candidate_indexes].T
            flat_index = int(np.argmax(score_matrix))
            fragment_offset, candidate_offset = np.unravel_index(flat_index, score_matrix.shape)
            score = float(score_matrix[fragment_offset, candidate_offset])
            selected_fragment = fragments[current_indexes[fragment_offset]]
            selected_candidate = candidates[candidate_indexes[candidate_offset]]
            gold_positive = labels[record["id"]][item] == "1"
            if gold_positive:
                item_positive.append(score)
                evidence = labels[record["id"]][f"e{item[1:]}"]
                location = locate_evidence(record, evidence) if evidence else None
                if location is not None:
                    item_localizable += 1
                    hit = evidence in selected_fragment["text"]
                    item_localized += int(hit)
                    item_type += int(location.document_type == selected_fragment["document_type"])
                    positive_localizable += 1
                    localization_hits += int(hit)
                    type_hits += int(location.document_type == selected_fragment["document_type"])
            else:
                item_negative.append(score)
            selected.append({
                "notice_id": record["id"], "item": item,
                "gold_positive_evaluation_only": gold_positive,
                "top_score": round(score, 6),
                "selected_fragment": {key: selected_fragment[key] for key in ("doc_id", "document_type", "ordinal")},
                "selected_precedent": {key: selected_candidate[key] for key in ("notice_id", "document_type")},
            })
        auc = rank_auc(item_positive, item_negative)
        positive_scores.extend(item_positive)
        negative_scores.extend(item_negative)
        if item_positive or item_negative:
            per_item[item] = {
                "candidate_count": sum(row["item"] == item for row in candidates),
                "positive_scores": len(item_positive), "negative_scores": len(item_negative),
                "auc": round(auc, 6) if auc is not None else None,
                "localization_hit_rate": round(item_localized / item_localizable, 6) if item_localizable else None,
                "same_document_type_rate": round(item_type / item_localizable, 6) if item_localizable else None,
            }
    auc = rank_auc(positive_scores, negative_scores)
    item_aucs = [row["auc"] for row in per_item.values() if row["auc"] is not None]
    localization_rate = localization_hits / positive_localizable if positive_localizable else None
    success = bool(
        localization_rate is not None and localization_rate >= 0.50
        and auc is not None and auc >= 0.65
        and sum(value >= 0.60 for value in item_aucs) * 2 >= len(item_aucs)
    )
    report = {
        "audit": "dev_precedent_s0d",
        "policy": {
            "organizer_dev_static_precedents_only": True,
            "self_notice_precedent_excluded": True,
            "ranking_query_excludes_gold_labels_and_evidence": True,
            "label_transfer_threshold_voting": "prohibited",
            "absence_items_out_of_scope": ["v10", "v11", "v16", "v18", "v20"],
        },
        "provenance": {
            "dev": str(dev_path), "dev_sha256": _sha256(dev_path),
            "labels": str(labels_path), "labels_sha256": _sha256(labels_path),
            "embedding_model": args.model, "candidate_usage": candidate_usage,
            "fragment_usage": fragment_usage,
        },
        "coverage": {
            "candidate_count": len(candidates), "covered_items": sorted({row["item"] for row in candidates}),
            "fragment_count": len(fragments),
        },
        "evaluation": {
            "positive_localizable": positive_localizable,
            "localization_hit_rate": round(localization_rate, 6) if localization_rate is not None else None,
            "same_document_type_rate": round(type_hits / positive_localizable, 6) if positive_localizable else None,
            "score_auc": round(auc, 6) if auc is not None else None,
            "items_with_auc": len(item_aucs),
            "items_auc_at_least_060": sum(value >= 0.60 for value in item_aucs),
            "per_item": per_item,
        },
        "decision": (
            "CONDITIONAL PROCEED: dev source-grounded precedents clear every predeclared retrieval gate; "
            "design one small Gemma few-shot injection pilot next."
            if success else
            "STOP: leave-one-notice-out dev precedents do not establish a retrieval key strong enough for "
            "few-shot Gemma injection. Do not spend Gemma/Luna or expand a casebook."
        ),
    }
    (output_dir / "report.json").write_text(json.dumps({**report, "selected": selected}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "report.md").write_text(_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
