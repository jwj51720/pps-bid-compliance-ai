#!/usr/bin/env python3
"""Validate an experiment config and its declared controlled differences.

This command is intentionally read-only.  Run it before a paid experiment;
then run the same config with ``--mock`` before making provider calls.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import ExperimentConfig, load_config


def _policy(config: ExperimentConfig) -> dict[str, Any]:
    """Return effective model-policy fields, excluding ID/output/cohort only."""
    return {
        "prompt": {
            "max_document_chars": config.max_document_chars,
            "context_strategy": config.context_strategy,
            "overflow_split_enabled": config.overflow_split_enabled,
            "strict_document_evidence": config.strict_document_evidence,
            "absence_detection_strategy": config.absence_detection_strategy,
            "max_model_len": config.max_model_len,
            "output_reserve_tokens": config.output_reserve_tokens,
            "notice_anchor_chars": config.notice_anchor_chars,
            "reference_path": str(config.reference_path) if config.reference_path else None,
            "reference_bundle_dir": str(config.reference_bundle_dir) if config.reference_bundle_dir else None,
            "reference_routing": config.reference_routing,
            "decision_cards_path": str(config.decision_cards_path) if config.decision_cards_path else None,
            "competition_products_path": str(config.competition_products_path) if config.competition_products_path else None,
            "mode": config.prompt_mode,
            "include_normalized_facts": config.include_normalized_facts,
            "v8_composite_merge": {
                "enabled": config.v8_composite_merge_enabled,
                "mode": config.v8_composite_merge_mode,
            },
            "candidate_detection": config.candidate_detection,
            "active_items": list(config.active_items),
            "layout": config.prompt_layout,
            "output_mode": config.output_mode,
        },
        "llm": {
            "provider": config.llm.provider,
            "model": config.llm.model,
            "temperature": config.llm.temperature,
            "max_tokens": config.llm.max_tokens,
            "seed": config.llm.seed,
            "timeout_seconds": config.llm.timeout_seconds,
            "request_retries": config.llm.request_retries,
            "prediction_attempts": config.llm.prediction_attempts,
            "provider_sort": config.llm.provider_sort,
            "require_parameters": config.llm.require_parameters,
            "min_request_interval_seconds": config.llm.min_request_interval_seconds,
            # None means the model ID itself; compare effective source.
            "tokenizer_source": config.llm.tokenizer_source or config.llm.model,
        },
        "grouped_run": config.raw.get("grouped_run", {}),
    }


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, child in value.items():
            result.update(_flatten(child, f"{prefix}.{key}" if prefix else key))
        return result
    return {prefix: value}


def controlled_differences(
    base: ExperimentConfig, candidate: ExperimentConfig
) -> dict[str, dict[str, Any]]:
    before, after = _flatten(_policy(base)), _flatten(_policy(candidate))
    return {
        key: {"base": before.get(key), "candidate": after.get(key)}
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    candidate = load_config(args.config)
    for artifact in (
        candidate.data.input_path,
        candidate.data.item_table_path,
        candidate.decision_cards_path,
        candidate.competition_products_path,
        candidate.reference_path,
        candidate.reference_bundle_dir,
        candidate.data.fast_panel_ids_path,
    ):
        if artifact is not None and not artifact.exists():
            raise FileNotFoundError(f"required artifact does not exist: {artifact}")

    experiment = candidate.raw["experiment"]
    base_value = experiment.get("base_config")
    allowed = set(experiment.get("allowed_policy_changes", []))
    report: dict[str, Any] = {
        "experiment_id": candidate.experiment_id,
        "config": str(candidate.path.relative_to(ROOT)),
        "artifacts": "present",
        "controlled_differences": {},
    }
    if base_value:
        base_path = ROOT / str(base_value)
        base = load_config(base_path)
        differences = controlled_differences(base, candidate)
        report["base_config"] = str(base.path.relative_to(ROOT))
        report["controlled_differences"] = differences
        unexpected = sorted(set(differences) - allowed)
        if unexpected:
            print(json.dumps(report, ensure_ascii=False, indent=2))
            raise ValueError(
                "undeclared policy differences: " + ", ".join(unexpected)
            )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
