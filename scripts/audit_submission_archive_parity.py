#!/usr/bin/env python3
"""Run the S001 submission archive with stored dev200 responses."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai import load_experiment_config
from src.pps_ai.archive_parity import ArchiveStoredResponseParity


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = load_experiment_config(args.config, ROOT)
    report = ArchiveStoredResponseParity(config).run()
    print(json.dumps({
        "status": report["status"],
        "records": report["records"],
        "cell_difference_count": report["cell_difference_count"],
        "metrics": report["metrics"],
        "output_dir": str(config.output_dir),
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
