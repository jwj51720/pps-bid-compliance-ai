#!/usr/bin/env python3
"""S0A: audit whether gold evidence can lexically reach 20k source documents.

This is a zero-cost feasibility audit, not a RAG implementation.  Gold dev
evidence is used only to measure an optimistic lexical upper bound.  No result
from this script is eligible to enter a prompt, a self-label pool, or a rule.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import heapq
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evidence_audit import locate_evidence
from src.precedent_audit import bm25_term_score, profile_compatibility, tokenize


PROFILE_FIELDS = ("적용계약법", "업무구분", "계약방법", "낙찰방법", "조달방식")
ITEMS = tuple(f"v{number}" for number in range(1, 25))


@dataclass(frozen=True)
class AuditQuery:
    notice_id: str
    item: str
    evidence: str
    source_document_type: str
    meta: dict[str, object]
    terms: tuple[str, ...]


def read_jsonl_gz(path: Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _summary(values: list[int]) -> dict[str, int | float]:
    if not values:
        return {"count": 0, "median": 0, "p90": 0, "max": 0}
    ordered = sorted(values)
    return {
        "count": len(values),
        "median": ordered[(len(ordered) - 1) // 2],
        "p90": ordered[min(len(ordered) - 1, int((len(ordered) - 1) * 0.9))],
        "max": ordered[-1],
    }


def build_queries(
    records: list[dict[str, Any]], labels: dict[str, dict[str, str]],
) -> list[AuditQuery]:
    queries: list[AuditQuery] = []
    for record in records:
        row = labels[record["id"]]
        for number, item in enumerate(ITEMS, 1):
            evidence = row[f"e{number}"].strip()
            if row[item] != "1" or not evidence:
                continue
            location = locate_evidence(record, evidence)
            if location is None:
                continue
            terms = tuple(sorted(set(tokenize(evidence))))
            if terms:
                queries.append(AuditQuery(
                    notice_id=record["id"], item=item, evidence=evidence,
                    source_document_type=location.document_type,
                    meta=record["meta"], terms=terms,
                ))
    return queries


def _snippet(text: str, matched_terms: list[str]) -> str:
    lowered = text.lower()
    positions = [lowered.find(term) for term in matched_terms if lowered.find(term) >= 0]
    if not positions:
        return ""
    start = max(0, min(positions) - 90)
    end = min(len(text), start + 360)
    return text[start:end]


def audit(
    dev_records: list[dict[str, Any]], labels: dict[str, dict[str, str]], train_path: Path,
) -> dict[str, Any]:
    queries = build_queries(dev_records, labels)
    query_by_term: dict[str, list[int]] = defaultdict(list)
    for query_index, query in enumerate(queries):
        for term in query.terms:
            query_by_term[term].append(query_index)
    relevant_terms = set(query_by_term)
    document_frequency: Counter[str] = Counter()
    document_type_counts: Counter[str] = Counter()
    document_lengths: list[int] = []
    profile_counts: Counter[str] = Counter()
    document_count = 0
    token_count = 0

    for record in read_jsonl_gz(train_path):
        meta = record["meta"]
        profile_counts[" | ".join(str(meta.get(field) or "미입력") for field in PROFILE_FIELDS)] += 1
        for document in record["docs"]:
            terms = tokenize(document["text"])
            document_count += 1
            token_count += len(terms)
            document_lengths.append(len(document["text"]))
            document_type_counts[document["type"]] += 1
            document_frequency.update(set(terms) & relevant_terms)

    average_length = token_count / max(document_count, 1)
    heaps: list[list[tuple[float, int, str, str, dict[str, Any]]]] = [[] for _ in queries]
    for record in read_jsonl_gz(train_path):
        for document in record["docs"]:
            tokens = tokenize(document["text"])
            counts = Counter(tokens)
            active_terms = set(counts) & relevant_terms
            if not active_terms:
                continue
            scores: defaultdict[int, float] = defaultdict(float)
            matched: defaultdict[int, list[str]] = defaultdict(list)
            for term in active_terms:
                contribution = bm25_term_score(
                    counts[term], document_frequency[term], document_count,
                    len(tokens), average_length,
                )
                for query_index in query_by_term[term]:
                    scores[query_index] += contribution
                    matched[query_index].append(term)
            for query_index, score in scores.items():
                if score <= 0:
                    continue
                matched_terms = sorted(matched[query_index])
                candidate = {
                    "notice_id": record["id"],
                    "doc_id": document["doc_id"],
                    "document_type": document["type"],
                    "score": round(score, 6),
                    "matched_terms": matched_terms,
                    "matched_query_term_rate": round(
                        len(matched_terms) / len(queries[query_index].terms), 6
                    ),
                    "profile_compatibility": profile_compatibility(
                        queries[query_index].meta, record["meta"], PROFILE_FIELDS
                    ),
                    "snippet": _snippet(document["text"], matched_terms),
                }
                entry = (
                    score, -len(candidate["snippet"]), record["id"], document["doc_id"], candidate
                )
                heap = heaps[query_index]
                if len(heap) < 3:
                    heapq.heappush(heap, entry)
                elif entry[:4] > heap[0][:4]:
                    heapq.heapreplace(heap, entry)

    rows: list[dict[str, Any]] = []
    per_item: dict[str, Counter[str]] = {item: Counter() for item in ITEMS}
    for query_index, query in enumerate(queries):
        candidates = [entry[4] for entry in sorted(heaps[query_index], reverse=True)]
        metrics = per_item[query.item]
        metrics["queries"] += 1
        if candidates:
            metrics["top1_same_document_type"] += int(
                candidates[0]["document_type"] == query.source_document_type
            )
            metrics["top3_same_document_type"] += int(any(
                candidate["document_type"] == query.source_document_type
                for candidate in candidates
            ))
            metrics["top1_high_overlap"] += int(candidates[0]["matched_query_term_rate"] >= 0.5)
        rows.append({
            "dev_notice_id": query.notice_id,
            "item": query.item,
            "gold_source_document_type": query.source_document_type,
            "gold_evidence": query.evidence,
            "query_terms": list(query.terms),
            "candidates": candidates,
        })

    return {
        "audit": "precedent_s0a_lexical_fit",
        "scope": {
            "dev_records": len(dev_records),
            "train_path": str(train_path),
            "gold_evidence_queries": len(queries),
            "warning": (
                "Gold evidence is an evaluation-only optimistic query. This report does not "
                "define an inference retrieval policy or a self-label pool."
            ),
            "dense_bge_status": "not_run: lexical feasibility gate must pass first",
        },
        "corpus": {
            "document_count": document_count,
            "document_types": dict(document_type_counts),
            "document_characters": _summary(document_lengths),
            "top_metadata_profiles": [
                {"profile": profile, "count": count}
                for profile, count in profile_counts.most_common(20)
            ],
        },
        "aggregate": {
            "top1_same_document_type_rate": round(sum(
                row["candidates"] and row["candidates"][0]["document_type"] == row["gold_source_document_type"]
                for row in rows
            ) / max(len(rows), 1), 6),
            "top3_same_document_type_rate": round(sum(any(
                candidate["document_type"] == row["gold_source_document_type"]
                for candidate in row["candidates"]
            ) for row in rows) / max(len(rows), 1), 6),
            "top1_high_overlap_rate": round(sum(
                bool(row["candidates"]) and row["candidates"][0]["matched_query_term_rate"] >= 0.5
                for row in rows
            ) / max(len(rows), 1), 6),
        },
        "per_item": {
            item: {
                **dict(counter),
                "top1_same_document_type_rate": round(
                    counter["top1_same_document_type"] / counter["queries"], 6
                ) if counter["queries"] else None,
                "top3_same_document_type_rate": round(
                    counter["top3_same_document_type"] / counter["queries"], 6
                ) if counter["queries"] else None,
            }
            for item, counter in per_item.items() if counter["queries"]
        },
        "rows": rows,
    }


def markdown(report: dict[str, Any]) -> str:
    aggregate = report["aggregate"]
    lines = [
        "# S0A — 무라벨 선례 lexical 적합성 audit",
        "",
        "gold evidence를 **평가 전용의 낙관적 lexical query**로 사용했다. 이 결과는 "
        "inference query·self-label pool·최종 판정에 사용하지 않는다.",
        "",
        "## 전체",
        "",
        f"- gold-evidence queries: {report['scope']['gold_evidence_queries']}",
        f"- unlabeled source documents: {report['corpus']['document_count']}",
        f"- top-1 same document type: {aggregate['top1_same_document_type_rate']}",
        f"- top-3 same document type: {aggregate['top3_same_document_type_rate']}",
        f"- top-1 matched query-term rate >= 0.5: {aggregate['top1_high_overlap_rate']}",
        f"- dense BGE: {report['scope']['dense_bge_status']}",
        "",
        "## 항목별",
        "",
        "| item | queries | top-1 same type | top-3 same type | top-1 high overlap |",
        "|---|---:|---:|---:|---:|",
    ]
    for item, row in report["per_item"].items():
        lines.append(
            f"| {item} | {row['queries']} | {row['top1_same_document_type_rate']} | "
            f"{row['top3_same_document_type_rate']} | {row.get('top1_high_overlap', 0)} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", default="data/raw/open/dev.jsonl.gz")
    parser.add_argument("--labels", default="data/raw/open/dev_labels.csv")
    parser.add_argument("--train", default="data/raw/open/train_unlabeled.jsonl.gz")
    parser.add_argument("--output-dir", default="outputs/precedent-s0a-lexical-fit")
    args = parser.parse_args()
    with Path(args.labels).open(encoding="utf-8", newline="") as handle:
        labels = {row["id"]: row for row in csv.DictReader(handle)}
    dev_records = list(read_jsonl_gz(Path(args.dev)))
    report = audit(dev_records, labels, Path(args.train))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "report.md").write_text(markdown(report), encoding="utf-8")
    print(output_dir / "report.md")
    print(json.dumps(report["aggregate"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
