#!/usr/bin/env python3
"""Run the zero-call C007 v4 provenance replay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai.audits import run_v4_provenance_audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reference-manifest",
        default="experiments/manifests/reference_l41_openrouter_dev200_v1.json",
    )
    parser.add_argument("--labels", default="data/raw/open/dev_labels.csv")
    parser.add_argument(
        "--baseline",
        default="outputs/clean-exp-c005d-v19-dev200-promotion-v1/dev200/submission.csv",
    )
    parser.add_argument(
        "--responses",
        default="outputs/clean-reference-l41-openrouter-dev200-v1/responses/r10",
    )
    parser.add_argument(
        "--output", default="outputs/clean-exp-c007-v4-requirement-relation-phase-a",
    )
    args = parser.parse_args()
    report = run_v4_provenance_audit(
        repository_root=ROOT,
        reference_manifest_path=(ROOT / args.reference_manifest).resolve(),
        labels_path=(ROOT / args.labels).resolve(),
        baseline_path=(ROOT / args.baseline).resolve(),
        response_dir=(ROOT / args.responses).resolve(),
        output_dir=(ROOT / args.output).resolve(),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
