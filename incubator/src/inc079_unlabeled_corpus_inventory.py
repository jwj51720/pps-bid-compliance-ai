#!/usr/bin/env python3
"""Describe the permitted 20k corpus before any teacher-label spend.

This is intentionally label-free: its strata are observable organizer fields,
document availability, and source size.  It writes only incubator artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common


ROOT = Path(__file__).resolve().parents[2]


def percentile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * fraction)]


def digest_ids(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256("\n".join(row["id"] for row in rows).encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-id", default="inc079_unlabeled_corpus_inventory")
    args = parser.parse_args()

    source = ROOT / "data/raw/open/train_unlabeled.jsonl.gz"
    output = ROOT / "incubator/runs" / args.experiment_id
    output.mkdir(parents=True, exist_ok=True)
    rows = common.read_jsonl_gz(source)

    document_patterns: Counter[str] = Counter()
    completeness_patterns: Counter[str] = Counter()
    contract_law: Counter[str] = Counter()
    work_type: Counter[str] = Counter()
    contract_method: Counter[str] = Counter()
    award_method: Counter[str] = Counter()
    procurement_method: Counter[str] = Counter()
    information_project: Counter[str] = Counter()
    lengths: list[int] = []
    doc_counts: list[int] = []
    strata: Counter[tuple[str, str, str, str]] = Counter()

    for row in rows:
        meta = row["meta"]
        types = "+".join(sorted(doc["type"] for doc in row["docs"]))
        incomplete = "+".join(
            f"{key}:{value}" for key, value in sorted((row.get("dropped_doc_counts") or {}).items()) if value
        ) or "complete"
        length = sum(len(doc["text"]) for doc in row["docs"])
        document_patterns[types] += 1
        completeness_patterns[incomplete] += 1
        contract_law[str(meta.get("적용계약법"))] += 1
        work_type[str(meta.get("업무구분"))] += 1
        contract_method[str(meta.get("계약방법"))] += 1
        award_method[str(meta.get("낙찰방법"))] += 1
        procurement_method[str(meta.get("조달방식"))] += 1
        information_project[str(meta.get("정보화사업여부"))] += 1
        lengths.append(length)
        doc_counts.append(len(row["docs"]))
        strata[(str(meta.get("업무구분")), str(meta.get("계약방법")), types, incomplete)] += 1

    report = {
        "experiment_id": args.experiment_id,
        "purpose": "label-free observable-corpus inventory for teacher-pilot stratification",
        "record_count": len(rows),
        "id_sha256": digest_ids(rows),
        "source_sha256": common.sha256_file(source),
        "source_characters": {
            "min": min(lengths),
            "p50": percentile(lengths, 0.50),
            "p90": percentile(lengths, 0.90),
            "p95": percentile(lengths, 0.95),
            "max": max(lengths),
            "mean": sum(lengths) / len(lengths),
        },
        "documents_per_notice": {
            "min": min(doc_counts),
            "p50": percentile(doc_counts, 0.50),
            "p90": percentile(doc_counts, 0.90),
            "max": max(doc_counts),
            "mean": sum(doc_counts) / len(doc_counts),
        },
        "document_type_patterns": document_patterns.most_common(),
        "input_completeness_patterns": completeness_patterns.most_common(),
        "metadata": {
            "적용계약법": contract_law.most_common(),
            "업무구분": work_type.most_common(),
            "계약방법": contract_method.most_common(),
            "낙찰방법": award_method.most_common(),
            "조달방식": procurement_method.most_common(),
            "정보화사업여부": information_project.most_common(),
        },
        "largest_observable_strata": [
            {"업무구분": key[0], "계약방법": key[1], "문서유형": key[2], "누락문서": key[3], "count": count}
            for key, count in strata.most_common(100)
        ],
    }
    common.write_json(output / "report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
