#!/usr/bin/env python3
"""Audit frozen product/SME Python predicate funnels on dev and unlabeled population."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai import load_experiment_config
from src.pps_ai.python_owner_audit import PythonOwnerPopulationAudit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = load_experiment_config(args.config, ROOT)
    report = PythonOwnerPopulationAudit(config).run()
    print(json.dumps({
        "status": report["status"],
        "dev_records": report["dev"]["records"],
        "population_records": report["population"]["records"],
        "large_shift_predicates": report["large_shift_predicates"],
        "output_dir": str(config.output_dir),
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
