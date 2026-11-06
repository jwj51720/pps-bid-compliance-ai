"""Inspect frozen direct-owner candidate coverage outside the announcement."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai.direct_attachment_coverage_audit import run_audit  # noqa: E402


if __name__ == "__main__":
    report = run_audit(ROOT)
    print(json.dumps({
        "status": report["status"], "checks": report["checks"],
        "dev": report["dev"]["attachment_only_notice_pairs"],
        "population": report["population"]["attachment_only_notice_pairs"],
        "runtime_seconds": report["runtime_seconds"],
    }, ensure_ascii=False, indent=2))
