"""Zero-call source-coverage audit for frozen direct Python owners."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import importlib
import json
from pathlib import Path
import time
from typing import Any, Callable, Mapping

from .python_policy_population import direct_owner_features
from .reference.frozen import FrozenL41Reference
from .runtime.openrouter import atomic_json


ITEMS = ("v1", "v2", "v5", "v6", "v7", "v8")
MODULE_PATHS = {
    "v1": "dev.run_v1_organization_capacity_experiment_v3",
    "v2": "dev.run_v2_notice_effect_experiment",
    "v5": "dev.run_v5_amount_region_experiment",
    "v5_hits": "dev.run_v5_amount_region_experiment_v2",
    "v6": "dev.run_v6_basic_region_experiment",
    "v7": "dev.run_v7_multi_province_experiment",
    "v8": "dev.run_v8_fact_intersection_experiment",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _flags(features: Mapping[str, bool]) -> dict[str, bool]:
    return {item: bool(features[f"{item}_final"]) for item in ITEMS}


def attachment_counterfactual(
    record: Mapping[str, Any],
    classifier: Callable[[Mapping[str, Any]], Mapping[str, bool]],
) -> tuple[dict[str, bool], list[dict[str, Any]]]:
    """Run the unchanged owner on each attachment as a diagnostic notice."""
    original = _flags(classifier(record))
    attachments: list[dict[str, Any]] = []
    for document_order, document in enumerate(record.get("docs") or []):
        if document.get("type") == "공고문":
            continue
        source_text = document.get("text")
        if not isinstance(source_text, str):
            raise ValueError("source attachment text missing")
        proxy_document = {**document, "type": "공고문"}
        proxy_record = {**record, "docs": [proxy_document]}
        attachments.append({
            "document_order": document_order,
            "doc_id": document["doc_id"],
            "type": document["type"],
            "sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
            "flags": _flags(classifier(proxy_record)),
        })
    return original, attachments


def _scan(
    path: Path, reference: FrozenL41Reference, modules: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    record_count = document_count = attachment_count = 0
    document_types: Counter[str] = Counter()
    original_counts: Counter[str] = Counter()
    attachment_pair_counts: Counter[str] = Counter()
    attachment_only_counts: Counter[str] = Counter()
    attachment_only_by_type: dict[str, Counter[str]] = defaultdict(Counter)
    sample_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)

    classifier = lambda record: direct_owner_features(record, modules)
    for record in reference.baseline.iter_records(str(path)):
        record_count += 1
        docs = record.get("docs") or []
        document_count += len(docs)
        document_types.update(str(doc["type"]) for doc in docs)
        original, attachments = attachment_counterfactual(record, classifier)
        attachment_count += len(attachments)
        for item in ITEMS:
            original_counts[item] += int(original[item])
            hit_docs = [row for row in attachments if row["flags"][item]]
            attachment_pair_counts[item] += int(bool(hit_docs))
            if original[item] or not hit_docs:
                continue
            attachment_only_counts[item] += 1
            for row in hit_docs:
                attachment_only_by_type[item][row["type"]] += 1
            sample_rows[item].append({
                "id": str(record["id"]),
                "original": original,
                "hit_docs": hit_docs,
                "source_docs": [{
                    "document_order": order,
                    "doc_id": doc["doc_id"], "type": doc["type"],
                    "text": doc["text"],
                    "sha256": hashlib.sha256(doc["text"].encode("utf-8")).hexdigest(),
                } for order, doc in enumerate(docs)],
            })
    summary = {
        "path": str(path), "sha256": _sha256(path),
        "records": record_count, "documents": document_count,
        "attachments": attachment_count,
        "document_types": dict(document_types),
        "original_final_counts": dict(original_counts),
        "attachment_hit_notice_pairs": dict(attachment_pair_counts),
        "attachment_only_notice_pairs": dict(attachment_only_counts),
        "attachment_only_hit_documents_by_type": {
            item: dict(counts) for item, counts in attachment_only_by_type.items()
        },
    }
    return summary, sample_rows


def _hash_sample(rows: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: hashlib.sha256(row["id"].encode("utf-8")).hexdigest(),
    )[:limit]


def run_audit(root: Path) -> dict[str, Any]:
    started = time.perf_counter()
    base = json.loads((root / "experiments/manifests/clean_exp_s001_integrated_v3_v19_v1.json").read_text())
    reference = FrozenL41Reference(
        root / base["reference"]["zip_path"], base["reference"]["zip_sha256"],
    )
    modules = {key: importlib.import_module(path) for key, path in MODULE_PATHS.items()}
    dev, dev_rows = _scan(root / "data/raw/open/dev.jsonl.gz", reference, modules)
    population, population_rows = _scan(
        root / "data/raw/open/train_unlabeled.jsonl.gz", reference, modules,
    )
    s019 = json.loads((root / "outputs/clean-exp-s019-python-policy-population-audit-v1/audit_report.json").read_text())
    checks = {
        "source_counts": (dev["records"], dev["documents"], population["records"], population["documents"])
        == (200, 374, 20000, 38862),
        "original_final_parity": all(
            summary["original_final_counts"].get(item, 0)
            == s019[cohort]["counts"].get(f"{item}_final", 0)
            for cohort, summary in (("dev", dev), ("population", population))
            for item in ITEMS
        ),
        "source_hash_parity": (
            dev["sha256"] == s019["dev"]["sha256"]
            and population["sha256"] == s019["population"]["sha256"]
        ),
    }
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "mode": "frozen-direct-owner-attachment-counterfactual",
        "base_manifest": "experiments/manifests/clean_exp_s001_integrated_v3_v19_v1.json",
        "allowed_policy_changes": [],
        "reference_zip_sha256": base["reference"]["zip_sha256"],
        "reference_script_sha256": reference.script_sha256,
        "s019_report_sha256": _sha256(root / "outputs/clean-exp-s019-python-policy-population-audit-v1/audit_report.json"),
        "checks": checks, "dev": dev, "population": population,
        "sample_ids": {
            cohort: {item: [row["id"] for row in _hash_sample(rows)] for item, rows in samples.items()}
            for cohort, samples in (("dev", dev_rows), ("population", population_rows))
        },
        "llm_calls": 0, "embedding_calls": 0,
        "final_prediction_changed": False,
        "runtime_seconds": time.perf_counter() - started,
        "limitations": [
            "Attachment-as-notice is a counterfactual candidate scan, not a legal label.",
            "Single-document probes cannot represent cross-document v8 relationships.",
            "Original frozen owner logic and S019 counts must match exactly.",
        ],
    }
    output = root / "outputs/clean-exp-s024-direct-attachment-coverage-v1"
    output.mkdir(parents=True, exist_ok=True)
    atomic_json(output / "audit_report.json", report)
    atomic_json(output / "source_samples.json", {
        cohort: {item: _hash_sample(rows) for item, rows in samples.items()}
        for cohort, samples in (("dev", dev_rows), ("population", population_rows))
    })
    if report["status"] != "PASS":
        raise ValueError(f"S024 source/parity checks failed: {checks}")
    return report
