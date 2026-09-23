"""Run the S021 existing-role-view counterfactual."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pps_ai.v5_role_guard_diagnostic import run_audit


if __name__ == "__main__":
    result = run_audit(Path(__file__).resolve().parents[1])
    print(result["status"], result["dev"]["removed_count"], result["population"]["removed_count"])
