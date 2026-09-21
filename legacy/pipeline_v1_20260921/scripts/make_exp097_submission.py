#!/usr/bin/env python3
"""Package the evaluated EXP097 v-only policy as a DACON submission zip."""

from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "submission/build/exp097_vonly_three_group_full_split"
DIST_DIR = ROOT / "dist"
EXPERIMENT_CONFIG = ROOT / "configs/config.exp097-three-group-v5-fullsplit-2500-vonly-full200.yaml"
RUNTIME_CONFIG = ROOT / "submission/runtime_config.exp097.json"


def submission_archive_path() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DIST_DIR / f"pps_{timestamp}.zip"


def verify_runtime_policy() -> tuple[dict, dict]:
    """Refuse a package unless runtime has EXP097's effective policy."""
    experiment = yaml.safe_load(EXPERIMENT_CONFIG.read_text(encoding="utf-8"))
    runtime = json.loads(RUNTIME_CONFIG.read_text(encoding="utf-8"))
    prompt = experiment["prompt"]
    runtime_prompt = runtime["prompt"]
    fields = (
        "max_document_chars",
        "context_strategy",
        "overflow_split_enabled",
        "strict_document_evidence",
        "absence_detection_strategy",
        "output_mode",
        "profile",
        "max_model_len",
        "output_reserve_tokens",
        "notice_anchor_chars",
        "mode",
        "include_normalized_facts",
    )
    mismatches = [field for field in fields if prompt.get(field) != runtime_prompt.get(field)]
    if mismatches:
        raise ValueError("EXP097 config and runtime prompt differ for: " + ", ".join(mismatches))
    if runtime["runtime"].get("grouping") != experiment["grouped_run"]["grouping"]:
        raise ValueError("EXP097 runtime grouping differs from experiment")
    if int(runtime["runtime"].get("batch_size", 0)) != 64:
        raise ValueError("EXP097 runtime batch_size must be 64")
    if int(runtime["runtime"].get("batch_retries", -1)) != 2:
        raise ValueError("EXP097 runtime batch_retries must be 2")
    for config_key, runtime_key in (
        ("decision_cards_path", "decision_cards_file"),
        ("competition_products_path", "competition_products_file"),
    ):
        if Path(str(prompt.get(config_key))).name != runtime_prompt.get(runtime_key):
            raise ValueError(f"EXP097 {config_key} differs from runtime {runtime_key}")
    return experiment, runtime


def main() -> int:
    experiment, runtime = verify_runtime_policy()
    if STAGING.exists():
        shutil.rmtree(STAGING)
    STAGING.mkdir(parents=True)
    shutil.copy2(ROOT / "submission/script.py", STAGING / "script.py")
    shutil.copy2(RUNTIME_CONFIG, STAGING / "runtime_config.json")
    prompt = experiment["prompt"]
    runtime_prompt = runtime["prompt"]
    shutil.copy2(ROOT / str(prompt["decision_cards_path"]), STAGING / runtime_prompt["decision_cards_file"])
    shutil.copy2(ROOT / str(prompt["competition_products_path"]), STAGING / runtime_prompt["competition_products_file"])
    shutil.copytree(ROOT / "src", STAGING / "src", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(ROOT / "submission/requirements.txt", STAGING / "requirements.txt")

    destination = submission_archive_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(STAGING.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(STAGING))
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
