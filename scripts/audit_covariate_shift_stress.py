#!/usr/bin/env python3
"""Run the fixed-strata covariate-shift stress audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai import load_experiment_config
from src.pps_ai.covariate_shift_audit import CovariateShiftStressAudit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="experiments/manifests/clean_exp_s014_covariate_shift_stress_v1.json",
    )
    args = parser.parse_args()
    config = load_experiment_config(args.config, ROOT)
    report = CovariateShiftStressAudit(config).run()
    print(json.dumps({
        "status": report["status"],
        "raw_macro": report["metrics"]["raw_macro"],
        "weighted_macro": report["metrics"]["weighted_macro"],
        "effective_sample_size": report["support"]["effective_sample_size"],
        "unsupported_population_mass": report["support"]["unsupported_population_mass"],
        "largest_negative_item_shifts": report["largest_negative_item_shifts"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
