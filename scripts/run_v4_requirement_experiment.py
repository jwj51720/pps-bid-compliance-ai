#!/usr/bin/env python3
"""Run the clean C007B v4 requirement-instance experiment."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai import load_experiment_config
from src.pps_ai.v4_requirement_experiment import V4RequirementExperiment


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--cohort", choices=("fast20", "holdout20", "dev200"), required=True)
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    config = load_experiment_config(args.config, ROOT)
    output = config.output_dir / (f"{args.cohort}-mock" if args.mock else args.cohort)
    experiment = V4RequirementExperiment(config, cohort=args.cohort, output_dir=output)
    if args.preflight_only:
        report = experiment.preflight_only()
    else:
        replay = config.raw.get("v4_quote_resolution") or {}
        if not args.mock and "response_dir" not in replay and not os.environ.get(config.provider.api_key_env):
            parser.error(f"{config.provider.api_key_env} is required")
        report = experiment.run(mock=args.mock)
    print(json.dumps({
        "status": report["status"],
        "cohort": args.cohort,
        "records": report["records"],
        "metrics": report.get("metrics"),
        "output_dir": str(output),
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
