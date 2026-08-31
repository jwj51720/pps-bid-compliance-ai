#!/usr/bin/env python3
"""Build the canonical full-context adaptive DACON submission archive."""

from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "submission/build/final_full_context_adaptive"
DIST_DIR = ROOT / "dist"


def submission_archive_path() -> Path:
    """Return a DACON-safe, timestamped archive name (well below 30 chars)."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DIST_DIR / f"pps_{timestamp}.zip"


def verify_runtime_policy() -> None:
    """Refuse to package if experiment and submission prompt policies diverge."""
    canonical = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    runtime = json.loads(
        (ROOT / "submission/runtime_config.json").read_text(encoding="utf-8")
    )
    canonical_prompt = canonical["prompt"]
    runtime_prompt = runtime["prompt"]
    fields = (
        "max_document_chars",
        "overflow_split_enabled",
        "max_model_len",
        "output_reserve_tokens",
        "notice_anchor_chars",
    )
    mismatches = [
        field
        for field in fields
        if canonical_prompt.get(field) != runtime_prompt.get(field)
    ]
    if mismatches:
        raise ValueError(
            "config.yaml and submission/runtime_config.json differ for: "
            + ", ".join(mismatches)
        )


def main() -> int:
    verify_runtime_policy()
    destination = submission_archive_path()
    if STAGING.exists():
        shutil.rmtree(STAGING)
    STAGING.mkdir(parents=True)
    shutil.copy2(ROOT / "submission/script.py", STAGING / "script.py")
    shutil.copy2(ROOT / "submission/runtime_config.json", STAGING / "runtime_config.json")
    shutil.copytree(ROOT / "src", STAGING / "src", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(ROOT / "submission/requirements.txt", STAGING / "requirements.txt")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(STAGING.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(STAGING))
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
