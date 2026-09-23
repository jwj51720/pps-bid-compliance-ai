#!/usr/bin/env python3
"""Run the isolated S003 source-role micro probe."""

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

from src.pps_ai.config import load_experiment_config
from src.pps_ai.region_role_micro import run_micro


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="experiments/manifests/clean_exp_s003_region_role_micro_v1.json")
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    config = load_experiment_config(ROOT / args.config, ROOT)
    if not args.mock and not os.environ.get(config.provider.api_key_env):
        parser.error(f"{config.provider.api_key_env} is required")
    report = run_micro(config, mock=args.mock, api_key=os.environ.get(config.provider.api_key_env, ""))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] in {"PASS", "COMPLETE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
