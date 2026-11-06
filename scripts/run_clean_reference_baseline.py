#!/usr/bin/env python3
"""Run the hash-pinned L41 baseline through the clean-room layered pipeline."""

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
from src.pps_ai.pipeline import CleanReferencePipeline


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("limit must be positive")
    load_dotenv(ROOT / ".env")
    config = load_experiment_config(args.config, ROOT)
    if not args.mock and not os.environ.get(config.provider.api_key_env):
        parser.error(f"{config.provider.api_key_env} is required for a paid run")
    output_dir = config.output_dir
    if args.mock:
        output_dir = output_dir.with_name(output_dir.name + "-mock")
    report = CleanReferencePipeline(config, output_dir=output_dir).run(
        mock=args.mock, limit=args.limit,
    )
    print(json.dumps({
        "status": report["status"], "records": report["records"],
        "metrics": report["metrics"], "output_dir": str(output_dir),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
