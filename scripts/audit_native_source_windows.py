"""Zero-call full-index and bounded-view gold-evidence coverage audit."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai.ingest.jsonl import load_notice_records
from src.pps_ai.runtime.tokenizer import GemmaTokenCounter
from src.pps_ai.views.native_source_windows import (
    build_source_windows, evidence_covered, render_source_view,
    select_bounded_source_view,
)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--tokenizer-dir", type=Path, required=True)
    parser.add_argument("--char-cap", type=int, default=18000)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    records = load_notice_records(args.input)
    with args.labels.open(encoding="utf-8", newline="") as handle:
        labels = {row["id"]: row for row in csv.DictReader(handle)}
    if set(labels) != {record.notice_id for record in records}:
        raise ValueError("label and input IDs differ")
    counter = GemmaTokenCounter(args.tokenizer_dir.expanduser())
    all_documents = 0
    all_windows = 0
    selected_windows = 0
    omitted_windows = 0
    exact_evidence = 0
    full_covered = 0
    bounded_covered = 0
    bounded_misses: list[dict[str, str]] = []
    by_item: dict[str, Counter[str]] = {}
    by_doc_type: dict[str, Counter[str]] = {}
    notice_audit: dict[str, Any] = {}
    pack_tokens: list[int] = []
    for record in records:
        windows = build_source_windows(record)
        view = select_bounded_source_view(record, windows, character_cap=args.char_cap)
        all_documents += len(record.documents)
        all_windows += len(windows)
        selected_windows += len(view.selected)
        omitted_windows += len(view.omitted)
        pack_token_count = counter.count([{
            "role": "user", "content": render_source_view(view),
        }])
        pack_tokens.append(pack_token_count)
        notice_audit[record.notice_id] = {
            "documents": len(record.documents),
            "indexed_windows": len(windows),
            "selected_windows": len(view.selected),
            "omitted_windows": len(view.omitted),
            "selected_characters": view.selected_characters,
            "source_pack_tokens_alone": pack_token_count,
            "selected_source_spans": [
                {"doc_id": window.span.document_id,
                 "type": window.span.document_type,
                 "start": window.span.start, "end": window.span.end,
                 "document_sha256": window.span.document_sha256}
                for window in view.selected
            ],
        }
        row = labels[record.notice_id]
        for index in range(1, 25):
            evidence = row[f"e{index}"]
            if not evidence:
                continue
            exact_evidence += 1
            item = f"v{index}"
            source_types = {
                document.document_type for document in record.documents
                if evidence in document.text
            }
            if not source_types:
                raise ValueError(f"{record.notice_id}/{item}: gold evidence not exact")
            source_type = sorted(source_types)[0]
            by_item.setdefault(item, Counter())["total"] += 1
            by_doc_type.setdefault(source_type, Counter())["total"] += 1
            if evidence_covered(windows, evidence):
                full_covered += 1
            if evidence_covered(view.selected, evidence):
                bounded_covered += 1
                by_item[item]["covered"] += 1
                by_doc_type[source_type]["covered"] += 1
            else:
                bounded_misses.append({"id": record.notice_id,
                                       "item": item, "document_type": source_type})
    report = {
        "kind": "zero_call_source_coverage_probe",
        "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "labels_sha256": hashlib.sha256(args.labels.read_bytes()).hexdigest(),
        "records": len(records),
        "all_documents": all_documents,
        "all_windows": all_windows,
        "selected_windows": selected_windows,
        "omitted_windows": omitted_windows,
        "character_cap_per_notice": args.char_cap,
        "exact_gold_evidence": exact_evidence,
        "full_index_evidence_covered": full_covered,
        "bounded_evidence_covered": bounded_covered,
        "bounded_evidence_missed": bounded_misses,
        "by_item": {key: dict(value) for key, value in sorted(by_item.items())},
        "by_document_type": {
            key: dict(value) for key, value in sorted(by_doc_type.items())
        },
        "source_pack_token_min": min(pack_tokens),
        "source_pack_token_max": max(pack_tokens),
        "source_pack_token_sum": sum(pack_tokens),
        "by_notice": notice_audit,
        "model_calls": 0,
    }
    _write_json(args.output_dir / "audit.json", report)
    print(json.dumps({
        key: report[key] for key in (
            "records", "all_documents", "all_windows", "selected_windows",
            "omitted_windows", "exact_gold_evidence",
            "full_index_evidence_covered", "bounded_evidence_covered",
            "source_pack_token_min", "source_pack_token_max",
            "source_pack_token_sum", "model_calls",
        )
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
