#!/usr/bin/env python3
"""Freeze a diverse unlabeled-teacher pilot without consulting dev labels."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common


ROOT = Path(__file__).resolve().parents[2]
PILOT_SIZE = 256
COMMON_STRATA = 128
SEED = "inc080-teacher-pilot-v1"


def stable_rank(record_id: str) -> str:
    return hashlib.sha256(f"{SEED}:{record_id}".encode()).hexdigest()


def signature(record: dict[str, Any]) -> str:
    counts = Counter(document["type"] for document in record["docs"])
    return "+".join(f"{name}x{counts[name]}" for name in sorted(counts))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-id", default="inc080_teacher_pilot_manifest")
    args = parser.parse_args()
    source = ROOT / "data/raw/open/train_unlabeled.jsonl.gz"
    output = ROOT / "incubator/runs" / args.experiment_id
    output.mkdir(parents=True, exist_ok=True)
    records = common.read_jsonl_gz(source)
    ordered_lengths = sorted(
        (sum(len(document["text"]) for document in record["docs"]), record["id"])
        for record in records
    )
    decile_by_id = {
        record_id: min(9, position * 10 // len(ordered_lengths))
        for position, (_, record_id) in enumerate(ordered_lengths)
    }
    groups: dict[tuple[str, str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        meta = record["meta"]
        key = (
            str(meta.get("업무구분")),
            str(meta.get("계약방법")),
            signature(record),
            decile_by_id[record["id"]],
        )
        groups[key].append(record)
    ranked_groups = sorted(
        groups.items(),
        key=lambda pair: (-len(pair[1]), pair[0]),
    )[:COMMON_STRATA]
    queues = {
        key: sorted(rows, key=lambda record: stable_rank(record["id"]))
        for key, rows in ranked_groups
    }
    selected: list[tuple[tuple[str, str, str, int], dict[str, Any]]] = []
    # Round-robin produces one representative of each common observable stratum
    # before taking a second example from any of them.
    while len(selected) < PILOT_SIZE:
        advanced = False
        for key, _ in ranked_groups:
            queue = queues[key]
            if not queue or len(selected) >= PILOT_SIZE:
                continue
            selected.append((key, queue.pop(0)))
            advanced = True
        if not advanced:
            raise RuntimeError("insufficient records for frozen pilot")
    manifest = []
    for order, (key, record) in enumerate(selected, start=1):
        source_characters = sum(len(document["text"]) for document in record["docs"])
        manifest.append(
            {
                "order": order,
                "id": record["id"],
                "input_sha256": common.sha256_text(json.dumps(record, ensure_ascii=False, sort_keys=True)),
                "source_characters": source_characters,
                "업무구분": key[0],
                "계약방법": key[1],
                "document_signature": key[2],
                "length_decile": key[3],
            }
        )
    report = {
        "experiment_id": args.experiment_id,
        "purpose": "frozen label-free unlabeled teacher pilot for casebook construction",
        "selection": {
            "size": PILOT_SIZE,
            "seed": SEED,
            "stratum": "업무구분 × 계약방법 × document-type multiplicity × corpus length decile",
            "common_strata": COMMON_STRATA,
            "algorithm": "one deterministic record per common stratum, then deterministic round-robin",
            "dev_labels_read": False,
        },
        "source_sha256": common.sha256_file(source),
        "selected_id_sha256": common.sha256_text("\n".join(row["id"] for row in manifest)),
        "coverage": {
            "업무구분": dict(Counter(row["업무구분"] for row in manifest)),
            "계약방법": dict(Counter(row["계약방법"] for row in manifest)),
            "length_decile": dict(sorted(Counter(row["length_decile"] for row in manifest).items())),
            "document_signature_count": len({row["document_signature"] for row in manifest}),
        },
    }
    common.write_jsonl(output / "manifest.jsonl", manifest)
    common.write_json(output / "report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
