#!/usr/bin/env python3
"""Build a minimal, self-contained archive for the isolated EXP-120 candidate."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = REPO_ROOT / "incubator/submission_candidates/exp120_card_v6"
REQUIRED = (
    "script.py",
    "requirements.txt",
    "runtime_config.json",
    "decision_cards_v6.json",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    missing = [name for name in REQUIRED if not (CANDIDATE / name).is_file()]
    if missing:
        raise RuntimeError(f"candidate missing required files: {missing}")

    source_files = sorted(
        path for path in (CANDIDATE / "src").rglob("*.py") if "__pycache__" not in path.parts
    )
    if not source_files:
        raise RuntimeError("candidate has no Python source files")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = REPO_ROOT / "dist" / f"pps_{timestamp}.zip"
    manifest = {
        "candidate": "exp120_card_v6",
        "policy": "EXP-120: 4000-char single context + decision cards v6",
        "files": {name: sha256(CANDIDATE / name) for name in REQUIRED},
        "source_files": [str(path.relative_to(CANDIDATE)) for path in source_files],
    }
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in REQUIRED:
            archive.write(CANDIDATE / name, name)
        for path in source_files:
            archive.write(path, str(path.relative_to(CANDIDATE)))
        archive.writestr("MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(destination) as archive:
        bad_member = archive.testzip()
        names = archive.namelist()
    if bad_member:
        raise RuntimeError(f"corrupt archive member: {bad_member}")
    if any("__pycache__" in name or name.endswith(".pyc") for name in names):
        raise RuntimeError("archive contains cache files")
    print(destination)
    print(f"members={len(names)} bytes={destination.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
