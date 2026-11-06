#!/usr/bin/env python3
"""Run the zero-call v24 operational surface audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai import load_experiment_config
from src.pps_ai.v24_operational_audit import V24OperationalSurfaceAudit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    report = V24OperationalSurfaceAudit(
        load_experiment_config(args.config, ROOT)
    ).run()
    print(json.dumps({
        "status": report["status"],
        "dev_records": report["dev"]["records"],
        "population_records": report["population"]["records"],
        "error_counts": report["dev_error_strata"]["counts"],
        "large_shift_features": report["large_shift_features"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
