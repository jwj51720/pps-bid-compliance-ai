"""Counterfactual audit of an existing source-role guard on frozen v5 positives."""

from __future__ import annotations

from collections import Counter
import csv
import hashlib
import importlib
import json
from pathlib import Path
from typing import Any, Mapping

from .reference.frozen import FrozenL41Reference
from .runtime.openrouter import atomic_json
from .views.regional_participation import build_regional_participation_candidates


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def frozen_v5_positive(record: Mapping[str, Any], hits_module: Any, gate_module: Any) -> bool:
    meta = record.get("meta") or {}
    estimate = meta.get("입찰추정가격")
    return bool(
        isinstance(estimate, (int, float)) and not isinstance(estimate, bool)
        and "공사" not in str(meta.get("업무구분") or "")
        and estimate >= gate_module.amount_cap(record)
        and hits_module.strict_region_hits(record)
    )


def _scan(path: Path, reference: FrozenL41Reference, hits_module: Any, gate_module: Any) -> dict[str, Any]:
    original: set[str] = set()
    retained: set[str] = set()
    removed: set[str] = set()
    records = 0
    for record in reference.baseline.iter_records(str(path)):
        records += 1
        if not frozen_v5_positive(record, hits_module, gate_module):
            continue
        notice_id = str(record["id"])
        original.add(notice_id)
        if build_regional_participation_candidates(record):
            retained.add(notice_id)
        else:
            removed.add(notice_id)
    if original != retained | removed or retained & removed:
        raise ValueError("v5 guard partition differs")
    return {
        "input_path": str(path), "input_sha256": _sha256(path), "records": records,
        "original_count": len(original), "retained_count": len(retained),
        "removed_count": len(removed),
        "original_ids": sorted(original), "retained_ids": sorted(retained),
        "removed_ids": sorted(removed),
    }


def _csv_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["id"]: row for row in csv.DictReader(handle)}


def _confusion(predictions: Mapping[str, int], labels: Mapping[str, dict[str, str]]) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    for notice_id, actual in labels.items():
        truth = int(actual["v5"])
        predicted = predictions[notice_id]
        counts["tp" if truth and predicted else "fp" if predicted else "fn" if truth else "tn"] += 1
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    denominator = 2 * tp + fp + fn
    return {**dict(counts), "f1": 2 * tp / denominator if denominator else 0.0}


def run_audit(root: Path) -> dict[str, Any]:
    manifest_path = root / "experiments/manifests/clean_exp_s001_integrated_v3_v19_v1.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    reference = FrozenL41Reference(
        root / manifest["reference"]["zip_path"], manifest["reference"]["zip_sha256"],
    )
    hits = importlib.import_module("dev.run_v5_amount_region_experiment_v2")
    gate = importlib.import_module("dev.run_v5_amount_region_experiment")
    dev = _scan(root / "data/raw/open/dev.jsonl.gz", reference, hits, gate)
    population = _scan(root / "data/raw/open/train_unlabeled.jsonl.gz", reference, hits, gate)
    final_path = root / "outputs/clean-exp-s001-integrated-v3-v19-v1/submission.csv"
    labels_path = root / "data/raw/open/dev_labels.csv"
    final = _csv_rows(final_path)
    labels = _csv_rows(labels_path)
    if set(final) != set(labels) or dev["original_ids"] != sorted(
        notice_id for notice_id, row in final.items() if int(row["v5"]) == 1
    ):
        raise ValueError("frozen v5 reproduction differs from S001")
    before = {notice_id: int(row["v5"]) for notice_id, row in final.items()}
    after = {notice_id: value if notice_id not in dev["removed_ids"] else 0
             for notice_id, value in before.items()}
    report = {
        "status": "PASS" if (dev["records"], population["records"]) == (200, 20000) else "FAIL",
        "base_manifest": str(manifest_path.relative_to(root)),
        "allowed_policy_changes": [], "candidate_policy_change": "v5-positive-only-existing-role-guard",
        "reference_zip_sha256": manifest["reference"]["zip_sha256"],
        "source_view_path": "src/pps_ai/views/regional_participation.py",
        "source_view_sha256": _sha256(root / "src/pps_ai/views/regional_participation.py"),
        "submission_sha256": _sha256(final_path), "labels_sha256": _sha256(labels_path),
        "dev": dev, "population": population,
        "dev_confusion_before": _confusion(before, labels),
        "dev_confusion_after": _confusion(after, labels),
        "llm_calls": 0, "embedding_calls": 0, "public_f1_estimate": None,
        "limitations": [
            "Unlabeled removals are not proven false positives.",
            "The reused dev200 labels are adaptive development evidence.",
        ],
    }
    output = root / "outputs/clean-exp-s021-v5-existing-role-guard-v1"
    output.mkdir(parents=True, exist_ok=True)
    atomic_json(output / "audit_report.json", report)
    return report
