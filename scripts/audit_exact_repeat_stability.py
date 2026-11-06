#!/usr/bin/env python3
"""Audit independent responses for identical stored tasks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai import load_experiment_config
from src.pps_ai.exact_repeat_audit import ExactRepeatStabilityAudit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="experiments/manifests/clean_exp_s015_exact_repeat_stability_audit_v1.json",
    )
    args = parser.parse_args()
    config = load_experiment_config(args.config, ROOT)
    report = ExactRepeatStabilityAudit(config).run()
    print(json.dumps({
        "status": report["status"],
        "v3": {key: report["v3"][key] for key in (
            "identical_task_pairs", "exact_content_different", "final_value_disagreements",
        )},
        "v19": {key: report["v19"][key] for key in (
            "identical_task_pairs", "exact_content_different", "final_value_disagreements",
        )},
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
