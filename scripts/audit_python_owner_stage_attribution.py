#!/usr/bin/env python3
"""Attribute frozen Python owner stage transitions on dev200."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai import load_experiment_config
from src.pps_ai.owner_stage_attribution import PythonOwnerStageAttributionAudit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default=(
            "experiments/manifests/"
            "clean_exp_s011_python_owner_stage_attribution_v1.json"
        ),
    )
    args = parser.parse_args()
    config = load_experiment_config(args.config, ROOT)
    report = PythonOwnerStageAttributionAudit(config).run()
    print(json.dumps({
        "status": report["status"],
        "records": report["records"],
        "items": {
            item: {
                "initial_f1": value["initial"]["f1"],
                "final_f1": value["final"]["f1"],
                "expansion_precision": value["expansion_precision"],
                "threshold": value["f1_improvement_precision_threshold"],
            }
            for item, value in report["initial_to_final_attribution"].items()
        },
        "output_dir": str(config.output_dir),
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
