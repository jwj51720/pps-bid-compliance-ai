#!/usr/bin/env python3
"""Replay C002R responses through the v24 code-provenance v2.1 reducer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai import load_experiment_config
from src.pps_ai.v24_replay import V24ReducerReplay


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = load_experiment_config(args.config, ROOT)
    report = V24ReducerReplay(config).run()
    print(json.dumps({
        "status": report["status"],
        "records": report["records"],
        "external_calls": report["external_calls"],
        "fallbacks": report["fallbacks"],
        "prediction_changes": report["prediction_changes"],
        "v24": report["metrics"]["per_item"]["v24"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
