#!/usr/bin/env python3
"""Create a portable project artifact archive with one top-level directory."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import tarfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DIST_ARCHIVES = ROOT / "dist" / "archives"
INCLUDE_PATHS = (
    "AGENTS.md",
    "README.md",
    "requirements.txt",
    "config.yaml",
    "configs",
    "docs",
    "src",
    "scripts",
    "submission",
    "tests",
    "data/raw",
    "data/derived",
    "outputs",
)
EXCLUDED_PARTS = {"__pycache__", ".DS_Store", ".git", ".venv", ".pytest_cache"}


def should_include(path: Path) -> bool:
    return not any(part in EXCLUDED_PARTS for part in path.parts) and path.suffix != ".pyc"


def files_to_archive() -> list[Path]:
    files: list[Path] = []
    for relative in INCLUDE_PATHS:
        source = ROOT / relative
        if source.is_file():
            files.append(source)
        elif source.is_dir():
            files.extend(path for path in source.rglob("*") if path.is_file() and should_include(path))
    # Submission zip files are untracked delivery artifacts. Include them, but
    # never include dist/archives: doing so would recursively archive archives.
    files.extend(path for path in (ROOT / "dist").glob("*.zip") if path.is_file())
    return sorted(files)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", help="archive stem; .tar.xz is added when omitted")
    args = parser.parse_args()
    stamp = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%dT%H%M%S%z")
    stem = args.name.removesuffix(".tar.xz") if args.name else f"pps-artifacts_{stamp}"
    destination = DIST_ARCHIVES / f"{stem}.tar.xz"
    top_level = stem
    files = files_to_archive()
    manifest = {
        "archive_format": "tar.xz",
        "top_level_directory": top_level,
        "created_at_kst": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
        "included_roots": list(INCLUDE_PATHS),
        "excluded": [
            ".env",
            ".git",
            ".venv",
            ".pytest_cache",
            "dist/archives (recursive archive exclusion)",
            "__pycache__",
            ".DS_Store",
        ],
        "files": [
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in files
        ],
    }
    DIST_ARCHIVES.mkdir(parents=True, exist_ok=True)
    with tarfile.open(destination, "w:xz") as archive:
        for path in files:
            archive.add(path, arcname=str(Path(top_level) / path.relative_to(ROOT)))
        payload = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
        info = tarfile.TarInfo(str(Path(top_level) / "manifest.json"))
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
