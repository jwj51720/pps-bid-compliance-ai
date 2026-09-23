#!/usr/bin/env python3
"""Run S005 v3 specialist removal replay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai.config import load_experiment_config
from src.pps_ai.v3_revert_replay import run_v3_revert


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="experiments/manifests/clean_exp_s005_v3_revert_ablation_v1.json",
    )
    args = parser.parse_args()
    config = load_experiment_config(ROOT / args.config, ROOT)
    report = run_v3_revert(config)
    print(json.dumps({
        "status": report["status"], "actual_macro": report["actual_macro"],
        "expected_macro": report["expected_macro"],
        "changed_cells": report["changed_cells"],
        "logical_initial_calls_dev200": report["logical_initial_calls_dev200"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
