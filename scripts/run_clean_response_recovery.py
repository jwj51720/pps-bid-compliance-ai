#!/usr/bin/env python3
"""Run a serialization-only clean response recovery experiment."""

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
from src.pps_ai.recovery_pipeline import CleanResponseRecoveryPipeline


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    config = load_experiment_config(args.config, ROOT)
    pipeline = CleanResponseRecoveryPipeline(config)
    if args.preflight_only:
        report = pipeline.preflight_only()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    if not os.environ.get(config.provider.api_key_env):
        parser.error(f"{config.provider.api_key_env} is required")
    report = pipeline.run()
    print(json.dumps({
        "status": report["status"],
        "target_count": report["target_count"],
        "recovered_usable": report["recovered_usable"],
        "metrics": {
            name: value["macro_positive_f1"]
            for name, value in report["metrics"].items()
        },
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
