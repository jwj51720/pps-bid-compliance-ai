#!/usr/bin/env python3
"""Run the N007 clean v2-only fixed-panel diagnostic."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai.native_v2_diagnostic import (
    load_native_v2_config, prepare_native_v2_panel, run_native_v2_panel,
)
from src.pps_ai.runtime.openrouter import atomic_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    config = load_native_v2_config(args.config, ROOT)
    if args.preflight_only:
        _, _, report = prepare_native_v2_panel(config)
        atomic_json(config.output_dir / f"{config.cohort}-preflight" / "preflight.json", report)
    else:
        report = run_native_v2_panel(config, mock=args.mock)
    print(json.dumps({key: report.get(key) for key in (
        "status", "records", "logical_calls", "new_calls", "counts",
        "precision", "recall", "f1", "seconds",
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
