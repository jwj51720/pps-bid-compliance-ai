#!/usr/bin/env python3
"""Package the isolated EXP-123 card-v6 plus frozen-rule candidate."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "incubator/submission_candidates/exp123_card_v6_frozen_rules"
REQUIRED = ("script.py", "requirements.txt", "runtime_config.json", "decision_cards_v6.json")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    missing = [name for name in REQUIRED if not (CANDIDATE / name).is_file()]
    if missing:
        raise RuntimeError(f"candidate missing: {missing}")
    sources = sorted(path for path in (CANDIDATE / "src").rglob("*.py") if "__pycache__" not in path.parts)
    if not any(path.name == "frozen_rules.py" for path in sources):
        raise RuntimeError("frozen rules are not packaged")
    destination = ROOT / "dist" / f"pps_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    manifest = {
        "candidate": "exp123_card_v6_frozen_rules",
        "policy": "EXP-120 + source-complete frozen v2/v3/v21 overrides",
        "files": {name: sha256(CANDIDATE / name) for name in REQUIRED},
        "source_files": [str(path.relative_to(CANDIDATE)) for path in sources],
    }
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in REQUIRED:
            archive.write(CANDIDATE / name, name)
        for path in sources:
            archive.write(path, str(path.relative_to(CANDIDATE)))
        archive.writestr("MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip():
            raise RuntimeError("zip integrity failure")
        names = archive.namelist()
    if any("__pycache__" in name or name.endswith(".pyc") for name in names):
        raise RuntimeError("cache file in archive")
    print(destination)
    print(f"members={len(names)} bytes={destination.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
