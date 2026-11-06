#!/usr/bin/env python3
"""Audit v19 morphology and stored owner utility on dev/population."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai import load_experiment_config
from src.pps_ai.v19_population_audit import V19PopulationMorphologyAudit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default=(
            "experiments/manifests/"
            "clean_exp_s012_v19_population_morphology_audit_v1.json"
        ),
    )
    args = parser.parse_args()
    config = load_experiment_config(args.config, ROOT)
    report = V19PopulationMorphologyAudit(config).run()
    print(json.dumps({
        "status": report["status"],
        "dev_records": report["dev"]["records"],
        "population_records": report["population"]["records"],
        "dev_candidates": report["dev"]["candidates"],
        "population_candidates": report["population"]["candidates"],
        "large_shift_notice_features": report["large_shift_notice_features"],
        "owner_f1": {
            "base": report["base_to_native_owner_transition"]["initial"]["f1"],
            "native": report["base_to_native_owner_transition"]["final"]["f1"],
        },
        "output_dir": str(config.output_dir),
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
