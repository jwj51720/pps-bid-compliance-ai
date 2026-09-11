#!/usr/bin/env python3
"""Build the canonical policy's DACON submission archive."""

from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "submission/build/exp200_corrected_input_source_first_v1"
DIST_DIR = ROOT / "dist"


def submission_archive_path() -> Path:
    """Return a DACON-safe, timestamped archive name (well below 30 chars)."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DIST_DIR / f"pps_{timestamp}.zip"


def verify_runtime_policy() -> tuple[dict, dict]:
    """Refuse to package if experiment and submission prompt policies diverge."""
    canonical = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    runtime = json.loads(
        (ROOT / "submission/runtime_config.json").read_text(encoding="utf-8")
    )
    canonical_prompt = canonical["prompt"]
    runtime_prompt = runtime["prompt"]
    canonical_cards = canonical_prompt.get("decision_cards_path")
    runtime_cards = runtime_prompt.get("decision_cards_file")
    canonical_products = canonical_prompt.get("competition_products_path")
    runtime_products = runtime_prompt.get("competition_products_file")
    fields = (
        "max_document_chars",
        "context_strategy",
        "overflow_split_enabled",
        "strict_document_evidence",
        "absence_detection_strategy",
        "max_model_len",
        "output_reserve_tokens",
        "notice_anchor_chars",
        "profile",
        "layout",
        "role_directive",
        "item_catalog_style",
        "metadata_style",
        "output_mode",
        "competition_product_context_mode",
        "organizer_input_semantics_mode",
        "mode",
        "include_normalized_facts",
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
    if bool(canonical_cards) != bool(runtime_cards):
        raise ValueError("config.yaml and submission/runtime_config.json differ for decision cards")
    if canonical_cards and Path(str(canonical_cards)).name != runtime_cards:
        raise ValueError("submission decision_cards_file must equal config decision_cards_path basename")
    if bool(canonical_products) != bool(runtime_products):
        raise ValueError("config.yaml and submission/runtime_config.json differ for competition products")
    if canonical_products and Path(str(canonical_products)).name != runtime_products:
        raise ValueError(
            "submission competition_products_file must equal config competition_products_path basename"
        )
    canonical_grouped_run = canonical.get("grouped_run", {})
    if not isinstance(canonical_grouped_run, dict):
        raise ValueError("config.yaml grouped_run must be a mapping")
    canonical_grouping = str(canonical_grouped_run.get("grouping", "all"))
    runtime_grouping = str(runtime["runtime"].get("grouping", "all"))
    if canonical_grouping != runtime_grouping:
        raise ValueError(
            "config.yaml grouped_run.grouping and submission runtime grouping differ"
        )
    if canonical.get("staged_run", {}) != runtime.get("staged_run", {}):
        raise ValueError("config.yaml and submission runtime staged_run differ")
    if canonical.get("postprocess", {}) != runtime.get("postprocess", {}):
        raise ValueError("config.yaml and submission runtime postprocess differ")
    canonical_llm = canonical.get("llm", {})
    runtime_values = runtime.get("runtime", {})
    if runtime_values.get("seed") != canonical_llm.get("seed"):
        raise ValueError("config llm.seed and submission runtime seed differ")
    if canonical_llm.get("temperature") != 0.0:
        raise ValueError("submission script requires canonical llm.temperature=0")
    if canonical_llm.get("max_tokens") != canonical_prompt.get("output_reserve_tokens"):
        raise ValueError(
            "canonical llm.max_tokens must equal prompt.output_reserve_tokens"
        )
    required_runtime = {
        "seed", "batch_size", "batch_retries", "gpu_memory_utilization",
        "quantization_env", "default_quantization",
    }
    if set(runtime_values) - {"grouping"} != required_runtime:
        raise ValueError("submission runtime fields are incomplete or unexpected")
    if not isinstance(runtime_values["batch_size"], int) or runtime_values["batch_size"] < 1:
        raise ValueError("submission runtime batch_size must be a positive integer")
    if not isinstance(runtime_values["batch_retries"], int) or runtime_values["batch_retries"] < 0:
        raise ValueError("submission runtime batch_retries must be a non-negative integer")
    gpu_memory = runtime_values["gpu_memory_utilization"]
    if not isinstance(gpu_memory, (int, float)) or not 0 < gpu_memory <= 1:
        raise ValueError("submission runtime gpu_memory_utilization must be in (0, 1]")
    if runtime_values["quantization_env"] != "PPS_QUANT":
        raise ValueError("submission quantization environment must be PPS_QUANT")
    if runtime_values["default_quantization"] != "int8_per_channel_weight_only":
        raise ValueError("submission default quantization differs from organizer baseline")
    return canonical, runtime


def main() -> int:
    canonical, runtime = verify_runtime_policy()
    destination = submission_archive_path()
    if STAGING.exists():
        shutil.rmtree(STAGING)
    STAGING.mkdir(parents=True)
    shutil.copy2(ROOT / "submission/script.py", STAGING / "script.py")
    shutil.copy2(ROOT / "submission/runtime_config.json", STAGING / "runtime_config.json")
    cards_file = runtime["prompt"].get("decision_cards_file")
    if cards_file:
        shutil.copy2(ROOT / str(canonical["prompt"]["decision_cards_path"]), STAGING / str(cards_file))
    products_file = runtime["prompt"].get("competition_products_file")
    if products_file:
        shutil.copy2(
            ROOT / str(canonical["prompt"]["competition_products_path"]),
            STAGING / str(products_file),
        )
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
