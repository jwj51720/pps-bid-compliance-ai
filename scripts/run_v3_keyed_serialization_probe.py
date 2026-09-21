#!/usr/bin/env python3
"""Run the two-record v3 keyed serialization probe."""

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
from src.pps_ai.v3_keyed_probe import V3KeyedSerializationProbe


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    config = load_experiment_config(args.config, ROOT)
    probe = V3KeyedSerializationProbe(config)
    if args.preflight_only:
        report = probe.preflight_only()
    else:
        if not os.environ.get(config.provider.api_key_env):
            parser.error(f"{config.provider.api_key_env} is required")
        report = probe.run()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

