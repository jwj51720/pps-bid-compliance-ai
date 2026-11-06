#!/usr/bin/env python3
"""Zero-call source audit of the frozen S001 v17 owner and unlabeled population."""

from __future__ import annotations

from collections import Counter, defaultdict
import argparse
import csv
import hashlib
import importlib
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.pps_ai.facts.document_product_codes import collect_document_product_mentions
from src.pps_ai.facts.product_codes import build_product_facts, load_product_index
from src.pps_ai.ingest import load_notice_records
from src.pps_ai.reference.frozen import FrozenL41Reference
from src.pps_ai.runtime.openrouter import atomic_json


PRODUCT_CODE = re.compile(r"(?<![0-9])[0-9]{10}(?![0-9])")
EXCEPTION = re.compile(r"제2조의3|우선조달.{0,15}예외|3인\s*이하|적격자가\s*없어\s*유찰")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = {row["id"]: row for row in csv.DictReader(handle)}
    if len(rows) != 200:
        raise ValueError(f"expected 200 dev rows: {path}")
    return rows


def source_hits(record, pattern: re.Pattern[str], *, limit: int = 8) -> list[dict]:
    hits: list[dict] = []
    for document in record.documents:
        for match in pattern.finditer(document.text):
            start, end = max(0, match.start() - 80), min(len(document.text), match.end() + 140)
            hits.append({
                "doc_id": document.doc_id,
                "document_type": document.document_type,
                "document_sha256": document.sha256,
                "start": start,
                "end": end,
                "exact_text": document.text[start:end],
            })
            if len(hits) >= limit:
                return hits
    return hits


def locate_scope_hits(record, phrases: list[str]) -> list[dict]:
    locations = []
    for phrase in phrases:
        found = False
        for document in record.documents:
            start = document.text.find(phrase)
            if start < 0:
                continue
            locations.append({
                "doc_id": document.doc_id,
                "document_type": document.document_type,
                "document_sha256": document.sha256,
                "start": start,
                "end": start + len(phrase),
                "exact_text": phrase,
            })
            found = True
            break
        if not found:
            raise ValueError(f"{record.notice_id}: frozen scope hit lacks source provenance")
    return locations


def population_bucket(raw: dict, catalog_codes: set[str], scope_hits_v2) -> str | None:
    meta = raw.get("meta") or {}
    amount = meta.get("입찰추정가격")
    if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount >= 100_000_000:
        return None
    if "공사" in str(meta.get("업무구분") or ""):
        return None
    scope = scope_hits_v2(raw)
    if not scope["broad"] or scope["small"]:
        return None
    direct = "direct" if "수의" in str(meta.get("계약방법") or "") else "competitive"
    attachment = "attachment" if len(raw.get("docs") or []) > 1 else "notice_only"
    codes = {
        match.group() for doc in raw.get("docs") or []
        for match in PRODUCT_CODE.finditer(str(doc.get("text") or ""))
    } & catalog_codes
    return f"{direct}|{attachment}|{'csv_code' if codes else 'no_csv_code'}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="experiments/manifests/clean_exp_s018_v17_source_relations_v1.json",
    )
    args = parser.parse_args()
    config_path = (ROOT / args.config).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config["schema_version"] != "clean-zero-call-source-audit-v1":
        raise ValueError("unexpected S018 manifest schema")
    if config["calls"] != {"llm": 0, "embedding": 0} or config["final_prediction"]:
        raise ValueError("S018 must remain a zero-call diagnostic")
    if config["experiment"]["allowed_policy_changes"]:
        raise ValueError("S018 cannot change the submitted policy")
    started = time.perf_counter()
    reference_path = ROOT / config["reference"]["zip_path"]
    dev_path = ROOT / config["data"]["dev_input_path"]
    population_path = ROOT / config["data"]["population_input_path"]
    truth_path = ROOT / config["data"]["dev_labels_path"]
    submission_path = ROOT / config["data"]["final_submission_path"]
    index_path = ROOT / config["data"]["product_index_path"]
    output_path = ROOT / config["output_dir"] / "audit_report.json"

    reference = FrozenL41Reference(reference_path, config["reference"]["zip_sha256"])
    frozen = importlib.import_module("dev.final_tqec_pipeline")
    truth, submission = csv_rows(truth_path), csv_rows(submission_path)
    if set(truth) != set(submission):
        raise ValueError("truth/submission ID coverage mismatch")
    index = load_product_index(index_path)
    raw_dev = {row["id"]: row for row in reference.baseline.iter_records(str(dev_path))}
    records = list(load_notice_records(dev_path))
    if {row.notice_id for row in records} != set(truth) or set(raw_dev) != set(truth):
        raise ValueError("dev source/label/submission ID coverage mismatch")

    positive = []
    for record in records:
        notice_id = record.notice_id
        if int(submission[notice_id]["v17"]) != 1:
            continue
        frozen_scope = frozen.scope_hits_v2(raw_dev[notice_id])
        metadata_products = build_product_facts(record.metadata, index)
        mentions = collect_document_product_mentions(record, index)
        positive.append({
            "id": notice_id,
            "truth_v17": int(truth[notice_id]["v17"]),
            "final_v10": int(submission[notice_id]["v10"]),
            "final_v11": int(submission[notice_id]["v11"]),
            "contract": record.metadata.get("계약방법"),
            "business": record.metadata.get("업무구분"),
            "estimated_price": record.metadata.get("입찰추정가격"),
            "organizer_clause": record.metadata.get("조항호내용"),
            "document_types": [doc.document_type for doc in record.documents],
            "frozen_scope_broad": frozen_scope["broad"],
            "frozen_scope_small": frozen_scope["small"],
            "frozen_scope_broad_source_locations": locate_scope_hits(
                record, frozen_scope["broad"]
            ),
            "frozen_scope_small_source_locations": locate_scope_hits(
                record, frozen_scope["small"]
            ),
            "metadata_product_facts": [vars(row) for row in metadata_products],
            "csv_matched_document_codes": sorted({row.code for row in mentions if row.csv_name}),
            "document_product_contexts": [
                {
                    "code": row.code,
                    "csv_name": row.csv_name,
                    "special_note": row.special_note,
                    "doc_id": row.code_span.document_id,
                    "document_type": row.code_span.document_type,
                    "start": row.context_span.start,
                    "end": row.context_span.end,
                    "exact_text": row.context_span.exact_text,
                }
                for row in mentions if row.csv_name
            ][:12],
            "exception_source_hits": source_hits(record, EXCEPTION),
        })
    if len(positive) != 13:
        raise ValueError(f"S001 v17 positive count drift: {len(positive)}")

    shared_scope_error_overlap = {}
    for item in ("v16", "v18"):
        error_rows = []
        for notice_id in sorted(truth):
            actual = int(truth[notice_id][item])
            predicted = int(submission[notice_id][item])
            if actual == predicted:
                continue
            scope = frozen.scope_hits_v2(raw_dev[notice_id])
            error_rows.append({
                "id": notice_id,
                "type": "FP" if predicted else "FN",
                "frozen_broad_present": bool(scope["broad"]),
                "frozen_small_present": bool(scope["small"]),
            })
        shared_scope_error_overlap[item] = {
            "errors": error_rows,
            "errors_with_broad_hit": sum(
                row["frozen_broad_present"] for row in error_rows
            ),
        }

    population_counts: Counter[str] = Counter()
    sample: defaultdict[str, list[tuple[str, str]]] = defaultdict(list)
    for raw in reference.baseline.iter_records(str(population_path)):
        bucket = population_bucket(raw, set(index), frozen.scope_hits_v2)
        if bucket is None:
            continue
        population_counts[bucket] += 1
        notice_id = str(raw["id"])
        score = hashlib.sha256(
            (config["population_sample"]["hash_prefix"] + notice_id).encode()
        ).hexdigest()
        sample[bucket].append((score, notice_id))
    selected = {
        bucket: [
            notice_id for _, notice_id in sorted(rows)[
                : config["population_sample"]["per_bucket"]
            ]
        ]
        for bucket, rows in sorted(sample.items())
    }
    selected_ids = {
        notice_id for ids in selected.values() for notice_id in ids
    }
    raw_sample = {
        row["id"]: row
        for row in reference.baseline.iter_records(str(population_path))
        if row["id"] in selected_ids
    }
    sample_review = []
    for record in load_notice_records(population_path):
        if record.notice_id not in selected_ids:
            continue
        scope = frozen.scope_hits_v2(raw_sample[record.notice_id])
        mentions = collect_document_product_mentions(record, index)
        sample_review.append({
            "id": record.notice_id,
            "bucket": next(
                key for key, ids in selected.items() if record.notice_id in ids
            ),
            "document_types": [doc.document_type for doc in record.documents],
            "frozen_broad_source_locations": locate_scope_hits(record, scope["broad"]),
            "frozen_small_source_locations": locate_scope_hits(record, scope["small"]),
            "csv_matched_document_codes": sorted({
                row.code for row in mentions if row.csv_name
            }),
            "csv_code_source_locations": [
                {
                    "code": row.code,
                    "csv_name": row.csv_name,
                    "special_note": row.special_note,
                    "doc_id": row.context_span.document_id,
                    "document_type": row.context_span.document_type,
                    "start": row.context_span.start,
                    "end": row.context_span.end,
                    "exact_text": row.context_span.exact_text,
                }
                for row in mentions if row.csv_name
            ][:12],
            "exception_source_hits": source_hits(record, EXCEPTION),
        })
    if {row["id"] for row in sample_review} != selected_ids:
        raise ValueError("population sample source coverage mismatch")
    report = {
        "status": "PASS",
        "mode": "zero-call-adaptive-dev-source-audit-plus-label-blind-population-morphology",
        "config": {"path": str(config_path), "sha256": sha256(config_path)},
        "inputs": {
            "reference": {"path": str(reference_path), "sha256": sha256(reference_path)},
            "dev": {"path": str(dev_path), "sha256": sha256(dev_path)},
            "population": {"path": str(population_path), "sha256": sha256(population_path)},
            "truth": {"path": str(truth_path), "sha256": sha256(truth_path)},
            "submission": {"path": str(submission_path), "sha256": sha256(submission_path)},
            "product_index": {"path": str(index_path), "sha256": sha256(index_path)},
        },
        "dev_positive": positive,
        "shared_scope_error_overlap": shared_scope_error_overlap,
        "population_broad_no_small_candidate_counts": dict(sorted(population_counts.items())),
        "population_hash_selected_sample_ids": selected,
        "population_sample_source_review": sample_review,
        "calls": {"llm": 0, "embedding": 0},
        "final_prediction": False,
        "runtime_seconds": time.perf_counter() - started,
    }
    atomic_json(output_path, report)
    print(json.dumps({
        "status": report["status"],
        "dev_v17_positives": len(positive),
        "dev_fp": sum(row["truth_v17"] == 0 for row in positive),
        "population_candidates": sum(population_counts.values()),
        "population_counts": report["population_broad_no_small_candidate_counts"],
        "output": str(output_path),
        "runtime_seconds": report["runtime_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
