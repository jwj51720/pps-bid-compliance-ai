"""Immutable configuration for the clean-room reference baseline."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProviderConfig:
    model: str
    embedding_model: str
    api_url: str
    embedding_url: str
    api_key_env: str
    temperature: float
    max_tokens: int
    seed: int
    timeout_seconds: float
    request_retries: int
    concurrency: int
    min_request_interval_seconds: float
    provider_sort: str
    require_parameters: bool


@dataclass(frozen=True)
class CleanExperimentConfig:
    path: Path
    experiment_id: str
    pipeline_id: str
    reference_zip: Path
    reference_zip_sha256: str
    input_path: Path
    labels_path: Path
    data_dir: Path
    item_table_path: Path
    fast_panel_path: Path
    holdout_panel_path: Path
    tokenizer_dir: Path
    output_dir: Path
    prompt_budget: int
    batch_size: int
    retrieval_top_k: int
    retrieval_batch_size: int
    provider: ProviderConfig
    raw: dict[str, Any]

    @property
    def manifest_sha256(self) -> str:
        encoded = json.dumps(self.raw, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def _path(root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else root / path


def load_experiment_config(path: str | Path, root: str | Path) -> CleanExperimentConfig:
    root_path = Path(root).resolve()
    config_path = Path(path).resolve()
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != "clean-experiment-v1":
        raise ValueError("unsupported clean experiment schema")
    if raw.get("base_config") is not None:
        raise ValueError("clean baseline manifests are fully resolved and cannot inherit")
    provider_raw = raw["provider"]
    provider = ProviderConfig(
        model=str(provider_raw["model"]),
        embedding_model=str(provider_raw["embedding_model"]),
        api_url=str(provider_raw["api_url"]),
        embedding_url=str(provider_raw["embedding_url"]),
        api_key_env=str(provider_raw["api_key_env"]),
        temperature=float(provider_raw["temperature"]),
        max_tokens=int(provider_raw["max_tokens"]),
        seed=int(provider_raw["seed"]),
        timeout_seconds=float(provider_raw["timeout_seconds"]),
        request_retries=int(provider_raw["request_retries"]),
        concurrency=int(provider_raw["concurrency"]),
        min_request_interval_seconds=float(provider_raw["min_request_interval_seconds"]),
        provider_sort=str(provider_raw["provider_sort"]),
        require_parameters=bool(provider_raw["require_parameters"]),
    )
    if provider.max_tokens != 1536 or provider.temperature != 0:
        raise ValueError("reference baseline requires max_tokens=1536 and temperature=0")
    if provider.concurrency < 1 or provider.request_retries < 0:
        raise ValueError("invalid provider concurrency or retry count")
    config = CleanExperimentConfig(
        path=config_path,
        experiment_id=str(raw["experiment_id"]),
        pipeline_id=str(raw["pipeline_id"]),
        reference_zip=_path(root_path, raw["reference"]["zip_path"]),
        reference_zip_sha256=str(raw["reference"]["zip_sha256"]),
        input_path=_path(root_path, raw["data"]["input_path"]),
        labels_path=_path(root_path, raw["data"]["labels_path"]),
        data_dir=_path(root_path, raw["data"]["organizer_data_dir"]),
        item_table_path=_path(root_path, raw["data"]["item_table_path"]),
        fast_panel_path=_path(root_path, raw["evaluation"]["fast_panel_path"]),
        holdout_panel_path=_path(root_path, raw["evaluation"]["holdout_panel_path"]),
        tokenizer_dir=_path(root_path, raw["runtime"]["tokenizer_dir"]),
        output_dir=_path(root_path, raw["output_dir"]),
        prompt_budget=int(raw["runtime"]["prompt_budget"]),
        batch_size=int(raw["runtime"]["batch_size"]),
        retrieval_top_k=int(raw["retrieval"]["top_k"]),
        retrieval_batch_size=int(raw["retrieval"]["batch_size"]),
        provider=provider,
        raw=raw,
    )
    required = (
        config.reference_zip, config.input_path, config.labels_path,
        config.data_dir, config.item_table_path, config.fast_panel_path,
        config.holdout_panel_path, config.tokenizer_dir,
    )
    missing = [str(value) for value in required if not value.exists()]
    if missing:
        raise FileNotFoundError("missing clean baseline inputs: " + ", ".join(missing))
    if config.prompt_budget != 14848 or config.retrieval_top_k != 10:
        raise ValueError("reference baseline token/retrieval policy differs")
    return config
