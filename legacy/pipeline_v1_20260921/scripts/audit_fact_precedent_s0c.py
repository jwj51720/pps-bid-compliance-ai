#!/usr/bin/env python3
"""S0C: audit source-fact precedent retrieval without a Gemma/Luna call.

This is evaluation-only infrastructure. It reads a fixed archived Luna
casebook, embeds its *same-item, source-resolved positive facts*, and asks
whether BGE-M3 can localize analogous source fragments in dev notices. Gold
labels/evidence are never supplied to BGE; they are read only after ranking to
score the audit.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import sys
import tarfile
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evidence_audit import locate_evidence
from src.fact_precedent_audit import cosine, rank_auc, source_fragments


ITEMS = tuple(f"v{number}" for number in range(1, 25))
PROFILE_FIELDS = ("적용계약법", "업무구분", "계약방법", "낙찰방법", "조달방식")
ARCHIVE_MEMBER = (
    "pps-dev-wsl-repro-20260907/incubator/runs/"
    "inc108_unlabeled_casebook64/records.jsonl"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def jsonl_from_gzip(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def archived_casebook(archive_path: Path) -> list[dict[str, Any]]:
    with tarfile.open(archive_path, "r:xz") as archive:
        member = archive.getmember(ARCHIVE_MEMBER)
        handle = archive.extractfile(member)
        if handle is None:
            raise RuntimeError(f"cannot read {ARCHIVE_MEMBER}")
        return [json.loads(line) for line in handle.read().decode("utf-8").splitlines() if line]


def compact_meta(meta: dict[str, Any]) -> str:
    return "\n".join(
        f"{field}: {meta.get(field) or '미입력'}" for field in PROFILE_FIELDS
    )


def candidate_records(rows: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    """Keep only teacher-positive records with exact source-resolved quotes."""
    candidates: list[dict[str, str]] = []
    for row in rows:
        stage_a = row.get("stage_a", {})
        stage_b = row.get("stage_b", {})
        if not stage_a.get("success") or not stage_b.get("success"):
            continue
        labels = stage_a.get("value", {}).get("labels", {})
        signature = stage_a.get("value", {}).get("case_signature", "").strip()
        evidence = stage_b.get("value", {}).get("evidence", {})
        resolved = row.get("resolved", {})
        for item, label in labels.items():
            quote_status = resolved.get(item)
            if label != 1 or not isinstance(quote_status, list) or len(quote_status) != 2:
                continue
            quote, status = quote_status
            basis = evidence.get(item, {}).get("basis", "").strip()
            if status != "exact" or not quote or not basis:
                continue
            candidates.append({
                "notice_id": row["id"],
                "item": item,
                "case_signature": signature,
                "basis": basis,
                "quote": quote,
                "embedding_text": (
                    f"항목: {item}\n판단 사실: {basis}\n"
                    f"원문 근거: {quote}\n사례 특징: {signature}"
                ),
            })
    return candidates


def notice_fragments(records: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    fragments: list[dict[str, str]] = []
    for record in records:
        for document in record["docs"]:
            for ordinal, text in enumerate(source_fragments(document["text"])):
                fragments.append({
                    "notice_id": record["id"],
                    "doc_id": document["doc_id"],
                    "document_type": document["type"],
                    "ordinal": str(ordinal),
                    "text": text,
                    "embedding_text": compact_meta(record["meta"]) + "\n원문 조각:\n" + text,
                })
    return fragments


def embed(api_key: str, values: list[str], model: str) -> tuple[list[list[float]], dict[str, Any]]:
    """Embed one bounded batch, retrying only transport/server failures."""
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
                break
            failure = f"HTTP {response.status_code}: {response.text[:500]}"
            if response.status_code < 500 and response.status_code != 429:
                raise RuntimeError(f"BGE request failed: {failure}")
        except requests.RequestException as error:
            failure = f"{type(error).__name__}: {error}"
        if attempt == 2:
            raise RuntimeError(f"BGE request failed after 3 attempts: {failure}")
        time.sleep(1 + attempt)
    else:  # pragma: no cover - loop either breaks or raises
        raise RuntimeError("unreachable embedding transport state")
    ordered = sorted(payload["data"], key=lambda row: row["index"])
    return [row["embedding"] for row in ordered], payload.get("usage", {})


def batch_embed(api_key: str, values: list[str], model: str, batch_size: int) -> tuple[list[list[float]], list[dict[str, Any]]]:
    vectors: list[list[float]] = []
    usages: list[dict[str, Any]] = []
    for start in range(0, len(values), batch_size):
        batch, usage = embed(api_key, values[start:start + batch_size], model)
        vectors.extend(batch)
        usages.append(usage)
    return vectors, usages


def write_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# S0C — source-fact precedent retrieval audit 결과",
        "",
        "이 결과는 dev label/evidence를 ranking에 사용하지 않고, ranking 뒤의 평가에만 사용했다.",
        "teacher label을 최종 판단으로 transfer하거나 cutoff로 사용하지 않았다.",
        "",
        "## Coverage",
        "",
        f"- validated positive teacher facts: {report['coverage']['candidate_count']}",
        f"- covered items ({report['coverage']['covered_item_count']}/24): "
        + ", ".join(report["coverage"]["covered_items"]),
        f"- current source fragments: {report['coverage']['fragment_count']}",
        "",
        "## Evaluation-only measurements",
        "",
        f"- same-v gold-positive queries with a candidate: {report['evaluation']['positive_queries']}",
        f"- oracle fact affinity mean top score: {report['evaluation']['oracle_mean_top_score']}",
        f"- inference-shaped localization hit rate: {report['evaluation']['localization_hit_rate']}",
        f"- localization same-document-type rate: {report['evaluation']['same_document_type_rate']}",
        f"- positive-vs-negative fragment score AUC: {report['evaluation']['score_auc']}",
        "",
        "## Interpretation gate",
        "",
        report["decision"],
        "",
        "Per-item details and every selected fragment are in `report.json`; snippets are deliberately"
        "not copied into this tracked document because they are organizer raw data.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", default="dist/archives/pps-dev-wsl-repro-20260907.tar.xz")
    parser.add_argument("--dev", default="data/raw/open/dev.jsonl.gz")
    parser.add_argument("--labels", default="data/raw/open/dev_labels.csv")
    parser.add_argument("--model", default="baai/bge-m3")
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--output-dir", default="outputs/fact-precedent-s0c")
    args = parser.parse_args()
    if args.batch_size <= 0:
        raise ValueError("--batch-size must be positive")

    archive_path, dev_path, labels_path = Path(args.archive), Path(args.dev), Path(args.labels)
    case_rows = archived_casebook(archive_path)
    candidates = candidate_records(case_rows)
    if not candidates:
        raise RuntimeError("archive has no source-resolved positive teacher facts")
    records = jsonl_from_gzip(dev_path)
    record_by_id = {record["id"]: record for record in records}
    fragments = notice_fragments(records)
    fragment_by_notice: dict[str, list[int]] = defaultdict(list)
    for index, fragment in enumerate(fragments):
        fragment_by_notice[fragment["notice_id"]].append(index)
    candidate_by_item: dict[str, list[int]] = defaultdict(list)
    for index, candidate in enumerate(candidates):
        candidate_by_item[candidate["item"]].append(index)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "run_manifest.json").write_text(json.dumps({
        "audit": "fact_precedent_s0c",
        "archive": str(archive_path), "archive_sha256": sha256(archive_path),
        "dev": str(dev_path), "dev_sha256": sha256(dev_path),
        "labels": str(labels_path), "labels_sha256": sha256(labels_path),
        "candidate_count": len(candidates), "fragment_count": len(fragments),
        "embedding_model": args.model, "batch_size": args.batch_size,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    load_dotenv(ROOT / ".env")
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required for the BGE audit")
    candidate_vectors, candidate_usage = batch_embed(
        api_key, [candidate["embedding_text"] for candidate in candidates], args.model, args.batch_size
    )
    fragment_vectors, fragment_usage = batch_embed(
        api_key, [fragment["embedding_text"] for fragment in fragments], args.model, args.batch_size
    )

    labels = {row["id"]: row for row in csv.DictReader(labels_path.open(encoding="utf-8"))}
    # Gold evidence is materialized only after candidate/query embedding inputs are fixed.
    # It is embedded in batches to keep this evaluation-only upper bound transport-bounded.
    oracle_keys: list[tuple[str, str]] = []
    oracle_inputs: list[str] = []
    for record in records:
        gold = labels[record["id"]]
        for item in candidate_by_item:
            evidence = gold[f"e{item[1:]}"] if gold[item] == "1" else ""
            if evidence and locate_evidence(record, evidence) is not None:
                oracle_keys.append((record["id"], item))
                oracle_inputs.append(compact_meta(record["meta"]) + "\n원문 근거:\n" + evidence)
    oracle_vectors, oracle_usage = batch_embed(api_key, oracle_inputs, args.model, args.batch_size)
    oracle_by_key = dict(zip(oracle_keys, oracle_vectors))
    per_item: dict[str, dict[str, Any]] = {}
    positive_scores: list[float] = []
    negative_scores: list[float] = []
    selected_rows: list[dict[str, Any]] = []
    oracle_scores: list[float] = []
    localization_hits = 0
    type_hits = 0
    positive_queries = 0

    for item in ITEMS:
        candidate_indexes = candidate_by_item.get(item, [])
        if not candidate_indexes:
            continue
        item_stats: Counter[str] = Counter()
        for record in records:
            notice_id = record["id"]
            fragment_indexes = fragment_by_notice[notice_id]
            top_score = -1.0
            top_fragment_index = -1
            top_candidate_index = -1
            for fragment_index in fragment_indexes:
                for candidate_index in candidate_indexes:
                    score = cosine(fragment_vectors[fragment_index], candidate_vectors[candidate_index])
                    if score > top_score:
                        top_score = score
                        top_fragment_index = fragment_index
                        top_candidate_index = candidate_index
            gold = labels[notice_id]
            gold_positive = gold[item] == "1"
            if gold_positive:
                positive_scores.append(top_score)
                evidence = gold[f"e{item[1:]}"]
                location = locate_evidence(record_by_id[notice_id], evidence) if evidence else None
                if location is not None:
                    positive_queries += 1
                    item_stats["positive_queries"] += 1
                    selected = fragments[top_fragment_index]
                    hit = evidence in selected["text"]
                    same_type = selected["document_type"] == location.document_type
                    localization_hits += int(hit)
                    type_hits += int(same_type)
                    item_stats["localization_hits"] += int(hit)
                    item_stats["same_document_type"] += int(same_type)
                    oracle_vector = oracle_by_key[(notice_id, item)]
                    oracle_scores.append(max(cosine(oracle_vector, candidate_vectors[index]) for index in candidate_indexes))
            else:
                negative_scores.append(top_score)
            selected_rows.append({
                "notice_id": notice_id,
                "item": item,
                "gold_positive_for_evaluation_only": gold_positive,
                "top_score": round(top_score, 6),
                "selected_fragment": {key: fragments[top_fragment_index][key] for key in ("doc_id", "document_type", "ordinal")},
                "selected_candidate": {key: candidates[top_candidate_index][key] for key in ("notice_id", "item")},
            })
        per_item[item] = {
            "teacher_candidate_count": len(candidate_indexes),
            "positive_queries": item_stats["positive_queries"],
            "localization_hit_rate": round(item_stats["localization_hits"] / item_stats["positive_queries"], 6) if item_stats["positive_queries"] else None,
            "same_document_type_rate": round(item_stats["same_document_type"] / item_stats["positive_queries"], 6) if item_stats["positive_queries"] else None,
        }

    localization_rate = localization_hits / positive_queries if positive_queries else None
    auc = rank_auc(positive_scores, negative_scores)
    # This is a deliberately stringent *diagnostic* gate, not a production cutoff.
    successful = (
        positive_queries >= 12
        and localization_rate is not None and localization_rate >= 0.5
        and auc is not None and auc >= 0.65
    )
    decision = (
        "CONDITIONAL PROCEED: same-v teacher facts localize current source facts above the "
        "predeclared audit gate. Design a maximum-32-notice Luna-high coverage pilot next; do "
        "not inject into Gemma or expand to 20k yet."
        if successful else
        "STOP: the archived 64-record bank does not yet demonstrate a reliable inference-shaped "
        "source-fact retrieval signal. Do not spend Luna on a larger bank or run Gemma injection."
    )
    report = {
        "audit": "fact_precedent_s0c",
        "policy": {
            "ranking_excludes_dev_labels_and_evidence": True,
            "same_item_positive_teacher_records_only": True,
            "final_label_transfer_or_threshold": "prohibited",
            "archive_member": ARCHIVE_MEMBER,
        },
        "provenance": {
            "archive": str(archive_path), "archive_sha256": sha256(archive_path),
            "dev": str(dev_path), "dev_sha256": sha256(dev_path),
            "labels": str(labels_path), "labels_sha256": sha256(labels_path),
            "embedding_model": args.model, "candidate_embedding_usage": candidate_usage,
            "fragment_embedding_usage": fragment_usage,
        },
        "coverage": {
            "casebook_records": len(case_rows), "candidate_count": len(candidates),
            "covered_items": sorted(candidate_by_item), "covered_item_count": len(candidate_by_item),
            "fragment_count": len(fragments),
        },
        "evaluation": {
            "positive_queries": positive_queries,
            "oracle_mean_top_score": round(sum(oracle_scores) / len(oracle_scores), 6) if oracle_scores else None,
            "localization_hit_rate": round(localization_rate, 6) if localization_rate is not None else None,
            "same_document_type_rate": round(type_hits / positive_queries, 6) if positive_queries else None,
            "score_auc": round(auc, 6) if auc is not None else None,
            "positive_notice_item_scores": len(positive_scores), "negative_notice_item_scores": len(negative_scores),
        },
        "per_item": per_item, "selected_rows": selected_rows, "decision": decision,
    }
    report["provenance"]["oracle_embedding_usage"] = oracle_usage
    (output_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "report.md").write_text(write_markdown(report), encoding="utf-8")
    print(output_dir / "report.md")
    print(decision)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
