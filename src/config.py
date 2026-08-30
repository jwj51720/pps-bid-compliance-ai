"""Typed loading and validation for the experiment YAML file."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class DataConfig:
    root: Path
    input_path: Path
    labels_path: Path | None
    item_table_path: Path


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    api_key_env: str
    api_url: str
    temperature: float
    max_tokens: int
    seed: int
    timeout_seconds: float
    request_retries: int
    prediction_attempts: int
    provider_sort: str
    require_parameters: bool
    min_request_interval_seconds: float


@dataclass(frozen=True)
class ExperimentConfig:
    path: Path
    raw: dict[str, Any]
    experiment_id: str
    derived_data: tuple[str, ...]
    data: DataConfig
    output_dir: Path
    max_document_chars: int | None
    prompt_mode: str
    include_normalized_facts: bool
    llm: LLMConfig
    resume: bool
    concurrency: int
    local_limit: int | None


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a mapping")
    return value


def load_config(path: str | Path) -> ExperimentConfig:
    config_path = Path(path).resolve()
    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    raw = _mapping(raw, "config")
    experiment = _mapping(raw.get("experiment"), "experiment")
    data = _mapping(raw.get("data"), "data")
    output = _mapping(raw.get("output"), "output")
    prompt = _mapping(raw.get("prompt"), "prompt")
    llm = _mapping(raw.get("llm"), "llm")
    run = _mapping(raw.get("run", {}), "run")

    base = config_path.parent
    root = (base / str(data["root"])).resolve()
    labels_value = data.get("labels")
    config = ExperimentConfig(
        path=config_path,
        raw=raw,
        experiment_id=str(experiment["id"]),
        derived_data=tuple(str(value) for value in experiment.get("derived_data", [])),
        data=DataConfig(
            root=root,
            input_path=root / str(data["input"]),
            labels_path=(root / str(labels_value)) if labels_value else None,
            item_table_path=root / str(data["item_table"]),
        ),
        output_dir=(base / str(output["dir"])).resolve(),
        max_document_chars=(
            int(prompt["max_document_chars"])
            if prompt.get("max_document_chars") is not None
            else None
        ),
        prompt_mode=str(prompt.get("mode", "baseline")),
        include_normalized_facts=bool(prompt.get("include_normalized_facts", False)),
        llm=LLMConfig(
            provider=str(llm["provider"]),
            model=str(llm["model"]),
            api_key_env=str(llm["api_key_env"]),
            api_url=str(llm["api_url"]),
            temperature=float(llm["temperature"]),
            max_tokens=int(llm["max_tokens"]),
            seed=int(llm["seed"]),
            timeout_seconds=float(llm["timeout_seconds"]),
            request_retries=int(llm["request_retries"]),
            prediction_attempts=int(llm["prediction_attempts"]),
            provider_sort=str(llm.get("provider_sort", "price")),
            require_parameters=bool(llm.get("require_parameters", True)),
            min_request_interval_seconds=float(llm.get("min_request_interval_seconds", 0)),
        ),
        resume=bool(run.get("resume", True)),
        concurrency=int(run.get("concurrency", 1)),
        local_limit=int(run["local_limit"]) if run.get("local_limit") is not None else None,
    )
    if config.llm.provider != "openrouter":
        raise ValueError(f"unsupported local provider: {config.llm.provider}")
    if config.max_document_chars is not None and config.max_document_chars < 1:
        raise ValueError("prompt.max_document_chars must be positive")
    if config.prompt_mode not in {"baseline", "structured", "guided"}:
        raise ValueError("prompt.mode must be baseline, structured, or guided")
    if config.concurrency < 1:
        raise ValueError("run.concurrency must be positive")
    if config.local_limit is not None and config.local_limit < 1:
        raise ValueError("run.local_limit must be positive")
    if config.llm.provider_sort not in {"price", "throughput", "latency"}:
        raise ValueError("llm.provider_sort must be price, throughput, or latency")
    if config.llm.min_request_interval_seconds < 0:
        raise ValueError("llm.min_request_interval_seconds must be non-negative")
    return config
