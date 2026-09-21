#!/usr/bin/env python3
"""Fail closed on undeclared clean-manifest differences."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai.preflight import compare_manifests
from src.pps_ai.runtime.openrouter import atomic_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    report = compare_manifests(Path(args.config).resolve(), ROOT)
    if args.output:
        atomic_json(Path(args.output).resolve(), report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
