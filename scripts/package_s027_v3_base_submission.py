"""Package the single-change v3 base-owner ablation for offline submission."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import zipfile

from package_integrated_submission import ROOT, staged_mock


SOURCE = ROOT / "dist/pps_20260922_153225.zip"
SOURCE_SHA256 = "72e3c1d65ec342b3d58e1cc5f99ee0c4a9ccfb1972d111df0fa488a5a0fce4df"
OLD = """    views, specialist_tasks, routing = integration.build_specialist_tasks(
        records, measured.count_tokens, baseline.PROMPT_BUDGET)
    selected_base = {
"""
NEW = """    views, specialist_tasks, routing = integration.build_specialist_tasks(
        records, measured.count_tokens, baseline.PROMPT_BUDGET)
    specialist_tasks = {
        key: task for key, task in specialist_tasks.items()
        if not key.startswith('V3/')
    }
    for route in routing.values():
        route['v3'] = []
    selected_base = {
"""


def package(output: Path) -> dict[str, object]:
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("source archive hash differs")
    with zipfile.ZipFile(SOURCE) as archive:
        names = archive.namelist()
        members = {name: archive.read(name) for name in names}
    original_members = members.copy()
    original = members["script.py"].decode("utf-8")
    if original.count(OLD) != 1:
        raise ValueError("submission routing insertion point differs")
    modified = original.replace(OLD, NEW, 1)
    compile(modified, "script.py", "exec")
    members["script.py"] = modified.encode("utf-8")
    runtime = json.loads(members["runtime_config.json"])
    runtime["candidate"] = "integrated-v19-v3-base-retry2-v1"
    members["runtime_config.json"] = (
        json.dumps(runtime, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    if len(output.name) > 30:
        raise ValueError("ZIP filename exceeds 30 characters")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in names:
            archive.writestr(name, members[name])
    changed = [name for name in names if members[name] != original_members[name]]
    if changed != ["script.py", "runtime_config.json"]:
        raise ValueError(f"unexpected package member changes: {changed}")
    return {
        "path": str(output),
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "changed_members": changed,
        "compressed_bytes": output.stat().st_size,
        "staged_mock": staged_mock(output),
    }


def main() -> int:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = ROOT / "dist" / f"pps_{timestamp}.zip"
    print(json.dumps(package(output), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
