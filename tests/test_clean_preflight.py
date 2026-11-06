from __future__ import annotations

import json
from pathlib import Path

from src.pps_ai.preflight import compare_manifests


def _write(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_preflight_accepts_only_declared_difference(tmp_path: Path) -> None:
    base = {"experiment_id": "base", "output_dir": "a", "policy": {"v24": "old"}}
    candidate = {
        "experiment_id": "candidate", "output_dir": "b",
        "experiment": {
            "base_config": "base.json",
            "allowed_policy_changes": ["policy.v24"],
        },
        "policy": {"v24": "new"},
    }
    _write(tmp_path / "base.json", base)
    _write(tmp_path / "candidate.json", candidate)
    report = compare_manifests(tmp_path / "candidate.json", tmp_path)
    assert report["status"] == "PASS"
    assert report["undeclared_differences"] == []


def test_preflight_rejects_undeclared_difference(tmp_path: Path) -> None:
    base = {"experiment_id": "base", "output_dir": "a", "policy": {"v24": "old", "v3": "same"}}
    candidate = {
        "experiment_id": "candidate", "output_dir": "b",
        "experiment": {
            "base_config": "base.json",
            "allowed_policy_changes": ["policy.v24"],
        },
        "policy": {"v24": "new", "v3": "changed"},
    }
    _write(tmp_path / "base.json", base)
    _write(tmp_path / "candidate.json", candidate)
    report = compare_manifests(tmp_path / "candidate.json", tmp_path)
    assert report["status"] == "FAIL"
    assert [row["path"] for row in report["undeclared_differences"]] == ["policy.v3"]
