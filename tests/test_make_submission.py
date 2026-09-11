from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

import scripts.make_submission as make_submission


@pytest.mark.parametrize(
    ("field", "canonical_value", "runtime_value"),
    [
        ("competition_product_context_mode", "conditions_and_provenance_v2", "names_only_v1"),
        ("organizer_input_semantics_mode", "anonymization_v1", "off"),
    ],
)
def test_packaging_rejects_semantic_input_mode_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    canonical_value: str,
    runtime_value: str,
) -> None:
    submission_dir = tmp_path / "submission"
    submission_dir.mkdir()
    (tmp_path / "config.yaml").write_text(
        yaml.safe_dump({
            "prompt": {field: canonical_value, "output_reserve_tokens": 100},
            "llm": {"seed": 1, "temperature": 0.0, "max_tokens": 100},
        }, allow_unicode=True),
        encoding="utf-8",
    )
    (submission_dir / "runtime_config.json").write_text(
        json.dumps({
            "prompt": {field: runtime_value},
            "runtime": {
                "seed": 1, "batch_size": 128, "batch_retries": 2,
                "gpu_memory_utilization": 0.92,
                "quantization_env": "PPS_QUANT",
                "default_quantization": "int8_per_channel_weight_only",
            },
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(make_submission, "ROOT", tmp_path)

    with pytest.raises(ValueError, match=field):
        make_submission.verify_runtime_policy()


def test_packaging_rejects_runtime_seed_drift(tmp_path: Path, monkeypatch) -> None:
    submission_dir = tmp_path / "submission"
    submission_dir.mkdir()
    (tmp_path / "config.yaml").write_text(
        yaml.safe_dump({
            "prompt": {"output_reserve_tokens": 100},
            "llm": {"seed": 7, "temperature": 0.0, "max_tokens": 100},
        }),
        encoding="utf-8",
    )
    (submission_dir / "runtime_config.json").write_text(
        json.dumps({
            "prompt": {"output_reserve_tokens": 100},
            "runtime": {
                "seed": 8, "batch_size": 128, "batch_retries": 2,
                "gpu_memory_utilization": 0.92,
                "quantization_env": "PPS_QUANT",
                "default_quantization": "int8_per_channel_weight_only",
            },
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(make_submission, "ROOT", tmp_path)

    with pytest.raises(ValueError, match="seed"):
        make_submission.verify_runtime_policy()
