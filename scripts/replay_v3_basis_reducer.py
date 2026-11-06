#!/usr/bin/env python3
"""Replay stored keyed observations with the v3 basis-v2 reducer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai import load_experiment_config
from src.pps_ai.v3_basis_replay import V3BasisReducerReplay


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = load_experiment_config(args.config, ROOT)
    report = V3BasisReducerReplay(config).run()
    print(json.dumps({
        "status": report["status"],
        "calls": report["calls"],
        "v3_changes": report["v3_changes"],
        "metrics": report["metrics"],
        "output_dir": str(config.output_dir),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

