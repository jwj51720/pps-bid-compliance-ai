"""Run the S019 frozen direct-Python-owner population audit."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pps_ai.python_policy_population import run_audit


if __name__ == "__main__":
    result = run_audit(Path(__file__).resolve().parents[1])
    print(result["status"], result["runtime_seconds"], len(result["comparisons"]))
