"""Run S022 full-source v5 role diagnostic."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.pps_ai import load_experiment_config
from src.pps_ai.v5_full_source_role_probe import run_probe


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    config = load_experiment_config(args.config, ROOT)
    api_key = os.environ.get(config.provider.api_key_env, "")
    if not args.mock and not api_key:
        parser.error(f"{config.provider.api_key_env} is required")
    report = run_probe(config, mock=args.mock, api_key=api_key)
    print(json.dumps({key: value for key, value in report.items() if key != "per_notice"}, ensure_ascii=False, indent=2))
    return 0 if report["status"] in {"PASS", "COMPLETE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
