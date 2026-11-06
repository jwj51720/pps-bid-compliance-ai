#!/usr/bin/env python3
"""Run the zero-call S004 dev-versus-organizer-population shift audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai.config import load_experiment_config
from src.pps_ai.generalization_audit import compare_cohorts, summarize_records
from src.pps_ai.ingest import load_notice_records
from src.pps_ai.runtime.openrouter import atomic_json


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="experiments/manifests/clean_exp_s004_generalization_shift_audit_v1.json",
    )
    args = parser.parse_args()
    started = time.monotonic()
    config = load_experiment_config(ROOT / args.config, ROOT)
    policy = config.raw["generalization_audit"]
    population_path = ROOT / policy["population_input_path"]
    dev_records = load_notice_records(config.input_path)
    population_records = load_notice_records(population_path)
    dev = summarize_records(dev_records)
    population = summarize_records(population_records)
    comparison = compare_cohorts(
        dev, population,
        rate_difference_gate=float(policy["large_shift_rate_difference"]),
        risk_ratio_low=float(policy["large_shift_risk_ratio_low"]),
        risk_ratio_high=float(policy["large_shift_risk_ratio_high"]),
    )
    if dev["records"] != 200 or population["records"] != 20_000:
        raise ValueError("unexpected audit cohort size")
    report = {
        "status": "PASS",
        "experiment_id": config.experiment_id,
        "manifest_sha256": config.manifest_sha256,
        "inputs": {
            "dev": {"path": str(config.input_path), "sha256": _sha256(config.input_path)},
            "population": {"path": str(population_path), "sha256": _sha256(population_path)},
        },
        "coverage": {
            "dev_records": dev["records"], "dev_documents": dev["documents"],
            "population_records": population["records"],
            "population_documents": population["documents"],
        },
        "comparison": comparison,
        "calls": {"llm": 0, "embedding": 0},
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    config.output_dir.mkdir(parents=True, exist_ok=True)
    atomic_json(config.output_dir / "manifest.snapshot.json", config.raw)
    atomic_json(config.output_dir / "audit_report.json", report)
    summary = {
        "status": report["status"], "coverage": report["coverage"],
        "binary": comparison["binary"],
        "categorical_total_variation": {
            key: value["total_variation"]
            for key, value in comparison["categorical"].items()
        },
        "continuous_standardized_mean_difference": {
            key: value["standardized_mean_difference"]
            for key, value in comparison["continuous"].items()
        },
        "elapsed_seconds": report["elapsed_seconds"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
