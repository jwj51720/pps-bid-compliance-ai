#!/usr/bin/env python3
"""Run S008 v16 full-source verifier preflight, micro, or dev200."""

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
from src.pps_ai.v16_full_source_verifier import run_v16_verifier


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--mode", choices=("micro", "dev200"), required=True)
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    config = load_experiment_config(args.config, ROOT)
    api_key = os.environ.get(config.provider.api_key_env, "")
    if not args.mock and not api_key:
        parser.error(f"{config.provider.api_key_env} is required")
    report = run_v16_verifier(config, mode=args.mode, mock=args.mock, api_key=api_key)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
