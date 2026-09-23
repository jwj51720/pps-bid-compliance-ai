#!/usr/bin/env python3
"""Audit v3 source-view morphology on dev and organizer unlabeled population."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai import load_experiment_config
from src.pps_ai.v3_population_audit import V3PopulationMorphologyAudit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default=(
            "experiments/manifests/"
            "clean_exp_s010_v3_population_morphology_audit_v1.json"
        ),
    )
    args = parser.parse_args()
    config = load_experiment_config(args.config, ROOT)
    report = V3PopulationMorphologyAudit(config).run()
    print(json.dumps({
        "status": report["status"],
        "dev_records": report["dev"]["records"],
        "population_records": report["population"]["records"],
        "dev_candidates": report["dev"]["candidates"],
        "population_candidates": report["population"]["candidates"],
        "large_shift_notice_features": report["large_shift_notice_features"],
        "output_dir": str(config.output_dir),
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
