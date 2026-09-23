"""Label-blind exposure audit of frozen direct Python item owners."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import importlib
import json
from math import sqrt
from pathlib import Path
import time
from typing import Any, Mapping

from .reference.frozen import FrozenL41Reference
from .runtime.openrouter import atomic_json


def wilson_interval(positive: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total <= 0:
        raise ValueError("total must be positive")
    proportion = positive / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = z * sqrt(
        proportion * (1 - proportion) / total + z * z / (4 * total * total)
    ) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def direct_owner_features(record: Mapping[str, Any], modules: Mapping[str, Any]) -> dict[str, bool]:
    meta = record.get("meta") or {}
    amount = meta.get("입찰추정가격")
    valid_amount = isinstance(amount, (int, float)) and not isinstance(amount, bool)
    v2_hits = modules["v2"].notice_hits(record)
    v2_exception = modules["v2"].is_local_small_quote(record)
    v6_hits = modules["v6"].region_hits(record)
    v6_exception = modules["v6"].is_local_small_quote_exception(record)
    v7_hits = modules["v7"].multi_province_hits(record)
    v7_exception = modules["v7"].is_local_small_quote_exception(record)
    v8_value, _, _ = modules["v8"].predict(record, use_quote_exception=True)
    v5_hits = modules["v5_hits"].strict_region_hits(record)
    v5_amount = bool(
        valid_amount and "공사" not in str(meta.get("업무구분") or "")
        and amount >= modules["v5"].amount_cap(record)
    )
    v1_hits = modules["v1"].same_line_candidate_hits(
        record, "plus_all_manufacturer_registration",
    )
    return {
        "v1_final": bool(v1_hits),
        "v2_raw_hits": bool(v2_hits),
        "v2_exception_on_hit": bool(v2_hits and v2_exception),
        "v2_final": bool(v2_hits and not v2_exception),
        "v5_raw_region_hits": bool(v5_hits),
        "v5_amount_gate": v5_amount,
        "v5_final": bool(v5_hits and v5_amount),
        "v6_raw_hits": bool(v6_hits),
        "v6_exception_on_hit": bool(v6_hits and v6_exception),
        "v6_final": bool(v6_hits and not v6_exception),
        "v7_raw_hits": bool(v7_hits),
        "v7_exception_on_hit": bool(v7_hits and v7_exception),
        "v7_final": bool(v7_hits and not v7_exception),
        "v8_final": bool(v8_value),
    }


def _scan(path: Path, reference: FrozenL41Reference, modules: Mapping[str, Any]) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    ids: dict[str, list[str]] = defaultdict(list)
    records = documents = 0
    for record in reference.baseline.iter_records(str(path)):
        records += 1
        documents += len(record.get("docs") or [])
        for key, active in direct_owner_features(record, modules).items():
            if active:
                counts[key] += 1
                ids[key].append(str(record["id"]))
    return {
        "path": str(path), "sha256": _sha256(path), "records": records,
        "documents": documents, "counts": dict(counts), "ids": ids,
    }


def _sample_ids(values: list[str], limit: int = 12) -> list[str]:
    return sorted(values, key=lambda value: hashlib.sha256(value.encode()).hexdigest())[:limit]


def run_audit(root: Path) -> dict[str, Any]:
    started = time.perf_counter()
    manifest = json.loads((root / "experiments/manifests/clean_exp_s001_integrated_v3_v19_v1.json").read_text())
    reference_path = root / manifest["reference"]["zip_path"]
    reference = FrozenL41Reference(reference_path, manifest["reference"]["zip_sha256"])
    module_paths = {
        "v1": "dev.run_v1_organization_capacity_experiment_v3",
        "v2": "dev.run_v2_notice_effect_experiment",
        "v5": "dev.run_v5_amount_region_experiment",
        "v5_hits": "dev.run_v5_amount_region_experiment_v2",
        "v6": "dev.run_v6_basic_region_experiment",
        "v7": "dev.run_v7_multi_province_experiment",
        "v8": "dev.run_v8_fact_intersection_experiment",
    }
    modules = {key: importlib.import_module(name) for key, name in module_paths.items()}
    dev = _scan(root / "data/raw/open/dev.jsonl.gz", reference, modules)
    population = _scan(root / "data/raw/open/train_unlabeled.jsonl.gz", reference, modules)
    comparisons = {}
    for key in sorted(set(dev["counts"]) | set(population["counts"])):
        dev_count = dev["counts"].get(key, 0)
        pop_count = population["counts"].get(key, 0)
        dev_rate = dev_count / dev["records"]
        pop_rate = pop_count / population["records"]
        comparisons[key] = {
            "dev_count": dev_count, "dev_rate": dev_rate,
            "dev_wilson_95": wilson_interval(dev_count, dev["records"]),
            "population_count": pop_count, "population_rate": pop_rate,
            "population_wilson_95": wilson_interval(pop_count, population["records"]),
            "risk_ratio_dev_over_population": dev_rate / pop_rate if pop_rate else None,
            "rate_difference_dev_minus_population": dev_rate - pop_rate,
            "dev_hash_sample_ids": _sample_ids(dev["ids"].get(key, [])),
            "population_hash_sample_ids": _sample_ids(population["ids"].get(key, [])),
        }
    report = {
        "status": "PASS" if (dev["records"], population["records"]) == (200, 20000) else "FAIL",
        "mode": "label-blind-frozen-direct-python-owner-exposure",
        "base_manifest": "experiments/manifests/clean_exp_s001_integrated_v3_v19_v1.json",
        "allowed_policy_changes": [],
        "reference_zip_sha256": manifest["reference"]["zip_sha256"],
        "reference_script_sha256": reference.script_sha256,
        "modules": module_paths,
        "dev": {key: value for key, value in dev.items() if key != "ids"},
        "population": {key: value for key, value in population.items() if key != "ids"},
        "comparisons": comparisons,
        "llm_calls": 0, "embedding_calls": 0, "final_prediction": False,
        "runtime_seconds": time.perf_counter() - started,
        "limitations": [
            "Unlabeled population rates cannot identify precision, recall, or public F1.",
            "This covers direct frozen Python owners, not BGE- or Gemma-dependent final labels.",
            "Wilson intervals describe sampling variation, not adaptive-selection uncertainty.",
        ],
    }
    output = root / "outputs/clean-exp-s019-python-policy-population-audit-v1"
    output.mkdir(parents=True, exist_ok=True)
    atomic_json(output / "audit_report.json", report)
    return report
