#!/usr/bin/env python3
"""Run an isolated clean native v1 fast-panel diagnostic."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai.native_v1_diagnostic import (
    load_native_v1_config, prepare_native_v1_fast, run_native_v1_fast,
)
from src.pps_ai.runtime.openrouter import atomic_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    config = load_native_v1_config(args.config, ROOT)
    if args.preflight_only:
        _, _, report = prepare_native_v1_fast(config)
        atomic_json(config.output_dir / "fast20" / "preflight.json", report)
    else:
        report = run_native_v1_fast(config, mock=args.mock)
    print(json.dumps({
        "status": report["status"], "records": report["records"],
        "logical_calls": report["logical_calls"],
        "counts": report.get("counts"),
        "f1_if_unknown_zero_diagnostic": report.get("f1_if_unknown_zero_diagnostic"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
