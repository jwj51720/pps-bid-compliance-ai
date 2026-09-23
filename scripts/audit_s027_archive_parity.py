"""Replay the staged v3-base archive against the S005 dev200 counterfactual."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.pps_ai import load_experiment_config  # noqa: E402
from src.pps_ai.archive_parity import ArchiveStoredResponseParity  # noqa: E402
from src.pps_ai.preflight import compare_manifests  # noqa: E402


def main() -> int:
    s005 = ROOT / "experiments/manifests/clean_exp_s005_v3_revert_ablation_v1.json"
    if compare_manifests(s005, ROOT)["status"] != "PASS":
        raise ValueError("S005 policy preflight failed")
    s006 = ROOT / "experiments/manifests/clean_exp_s006_archive_stored_response_parity_v1.json"
    audit = ArchiveStoredResponseParity(load_experiment_config(s006, ROOT))
    audit.archive_path = ROOT / "dist/pps_20260923_163852.zip"
    audit.expected_path = ROOT / "outputs/clean-exp-s005-v3-revert-ablation-v1/submission.csv"
    audit.output_dir = ROOT / "outputs/clean-exp-s027-v3-base-archive-parity-v1"
    report = audit.run()
    print(json.dumps({
        "status": report["status"], "records": report["records"],
        "cell_difference_count": report["cell_difference_count"],
        "stored_response_requests": report["stored_response_requests"],
        "metrics": report["metrics"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
