"""Strict effective-manifest diff for clean ablation control."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ALWAYS_ALLOWED = {
    "experiment_id", "pipeline_id", "output_dir", "experiment",
}


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            result.update(_flatten(child, path))
        return result
    return {prefix: value}


def _allowed(path: str, declarations: tuple[str, ...]) -> bool:
    top = path.split(".", 1)[0]
    if top in ALWAYS_ALLOWED:
        return True
    return any(path == item or path.startswith(item + ".") for item in declarations)


def compare_manifests(candidate_path: Path, repository_root: Path) -> dict[str, Any]:
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    experiment = candidate.get("experiment")
    if not isinstance(experiment, dict):
        raise ValueError("candidate requires experiment control object")
    base_value = experiment.get("base_config")
    allowed = experiment.get("allowed_policy_changes")
    if not isinstance(base_value, str) or not base_value:
        raise ValueError("experiment.base_config must be a path")
    if not isinstance(allowed, list) or any(not isinstance(item, str) for item in allowed):
        raise ValueError("experiment.allowed_policy_changes must be string paths")
    declarations = tuple(allowed)
    base_path = (repository_root / base_value).resolve()
    if not base_path.is_file():
        raise FileNotFoundError(f"base manifest not found: {base_path}")
    base = json.loads(base_path.read_text(encoding="utf-8"))
    base_flat = _flatten(base)
    candidate_flat = _flatten(candidate)
    differences: list[dict[str, Any]] = []
    undeclared: list[dict[str, Any]] = []
    for path in sorted(set(base_flat) | set(candidate_flat)):
        before = base_flat.get(path, "<MISSING>")
        after = candidate_flat.get(path, "<MISSING>")
        if before == after:
            continue
        row = {
            "path": path, "before": before, "after": after,
            "declared": _allowed(path, declarations),
        }
        differences.append(row)
        if not row["declared"]:
            undeclared.append(row)
    if not differences:
        raise ValueError("ablation has no effective manifest differences")
    declared_hits = {
        declaration: any(
            row["path"] == declaration or row["path"].startswith(declaration + ".")
            for row in differences
        )
        for declaration in declarations
    }
    unused = [key for key, hit in declared_hits.items() if not hit]
    status = "PASS" if not undeclared and not unused else "FAIL"
    return {
        "candidate": str(candidate_path.resolve()),
        "base": str(base_path),
        "allowed_policy_changes": list(declarations),
        "differences": differences,
        "undeclared_differences": undeclared,
        "unused_declarations": unused,
        "status": status,
    }
