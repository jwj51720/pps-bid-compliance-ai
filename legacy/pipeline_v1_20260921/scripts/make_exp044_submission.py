#!/usr/bin/env python3
"""Build the diagnostic EXP044 four-group DACON submission archive.

EXP044 is intentionally separate from the root canonical EXP014 policy.  This
script makes that distinction explicit and refuses to stage an archive unless
the full-dev experiment configuration and offline runtime policy agree.
"""

from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "submission/build/exp044_four_group_no_law"
DIST_DIR = ROOT / "dist"
EXPERIMENT_CONFIG = ROOT / "configs/config.exp044-four-group-no-law-clean-prompt-full200.yaml"
RUNTIME_CONFIG = ROOT / "submission/runtime_config.exp044.json"


def submission_archive_path() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DIST_DIR / f"pps_{timestamp}.zip"


def verify_runtime_policy() -> tuple[dict, dict]:
    """Confirm that the staged offline policy is the evaluated EXP044 policy."""
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
        "layout",
        "max_model_len",
        "output_reserve_tokens",
        "notice_anchor_chars",
        "mode",
        "include_normalized_facts",
    )
    mismatches = [field for field in fields if prompt.get(field) != runtime_prompt.get(field)]
    if mismatches:
        raise ValueError("EXP044 config and runtime prompt differ for: " + ", ".join(mismatches))
    if runtime["runtime"].get("grouping") != "four_way":
        raise ValueError("EXP044 runtime must use grouping=four_way")
    if int(runtime["runtime"].get("batch_size", 0)) != 128:
        raise ValueError("EXP044 runtime batch_size must remain the verified value 128")
    if int(runtime["runtime"].get("batch_retries", -1)) != 2:
        raise ValueError("EXP044 runtime batch_retries must remain 2")
    cards_path = prompt.get("decision_cards_path")
    products_path = prompt.get("competition_products_path")
    if Path(str(cards_path)).name != runtime_prompt.get("decision_cards_file"):
        raise ValueError("EXP044 decision card asset does not match runtime_config")
    if Path(str(products_path)).name != runtime_prompt.get("competition_products_file"):
        raise ValueError("EXP044 competition-product asset does not match runtime_config")
    return experiment, runtime


def main() -> int:
    experiment, runtime = verify_runtime_policy()
    if STAGING.exists():
        shutil.rmtree(STAGING)
    STAGING.mkdir(parents=True)
    shutil.copy2(ROOT / "submission/script.py", STAGING / "script.py")
    shutil.copy2(RUNTIME_CONFIG, STAGING / "runtime_config.json")
    shutil.copy2(
        ROOT / str(experiment["prompt"]["decision_cards_path"]),
        STAGING / str(runtime["prompt"]["decision_cards_file"]),
    )
    shutil.copy2(
        ROOT / str(experiment["prompt"]["competition_products_path"]),
        STAGING / str(runtime["prompt"]["competition_products_file"]),
    )
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
