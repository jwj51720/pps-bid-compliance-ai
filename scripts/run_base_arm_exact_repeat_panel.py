#!/usr/bin/env python3
"""Run the S017 frozen base-arm exact-repeat micro panel."""

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
from src.pps_ai.base_repeat_panel import BaseArmExactRepeatPanel


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    config = load_experiment_config(args.config, ROOT)
    panel = BaseArmExactRepeatPanel(config)
    if args.preflight_only:
        report = panel.preflight_only()
    else:
        is_zero_call_replay = isinstance(
            config.raw.get("base_repeat_json_fence_replay"), dict,
        )
        if (
            not args.mock
            and not is_zero_call_replay
            and not os.environ.get(config.provider.api_key_env)
        ):
            parser.error(f"{config.provider.api_key_env} is required")
        report = panel.run(mock=args.mock)
    print(json.dumps({
        "status": report["status"],
        "joint_macro_delta": (report.get("joint") or {}).get("macro_delta"),
        "output_dir": str(config.output_dir),
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
