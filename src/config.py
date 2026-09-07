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
    fast_panel_ids_path: Path | None


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
    tokenizer_source: str | None
    reasoning_effort: str | None


@dataclass(frozen=True)
class ReviewRunConfig:
    """Declared two-pass review operation for an experiment or submission."""

    mode: str
    final_judgment_source: str


@dataclass(frozen=True)
class ExperimentConfig:
    path: Path
    raw: dict[str, Any]
    experiment_id: str
    derived_data: tuple[str, ...]
    data: DataConfig
    output_dir: Path
    max_document_chars: int | None
    visible_document_types: tuple[str, ...] | None
    context_strategy: str
    overflow_split_enabled: bool
    strict_document_evidence: bool
    absence_detection_strategy: str
    max_model_len: int
    output_reserve_tokens: int
    notice_anchor_chars: int
    reference_path: Path | None
    reference_bundle_dir: Path | None
    reference_routing: str | None
    decision_cards_path: Path | None
    competition_products_path: Path | None
    prompt_mode: str
    include_normalized_facts: bool
    v8_composite_merge_enabled: bool
    v8_composite_merge_mode: str
    candidate_detection: bool
    active_items: tuple[str, ...]
    prompt_layout: str
    prompt_profile: str
    role_directive: str
    item_catalog_style: str
    metadata_style: str
    output_mode: str
    llm: LLMConfig
    review_run: ReviewRunConfig | None
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
    if experiment.get("lifecycle") == "invalidated":
        raise ValueError(
            "experiment is marked invalidated and must not be rerun; "
            "see docs/experiment_control.md"
        )
    data = _mapping(raw.get("data"), "data")
    output = _mapping(raw.get("output"), "output")
    prompt = _mapping(raw.get("prompt"), "prompt")
    llm = _mapping(raw.get("llm"), "llm")
    run = _mapping(raw.get("run", {}), "run")
    review_run = _mapping(raw["review_run"], "review_run") if raw.get("review_run") else None
    v8_composite_merge = _mapping(raw.get("v8_composite_merge", {}), "v8_composite_merge")

    # Root config lives at the repository root, while historical/experimental
    # configs live directly below configs/.  Both retain repository-relative
    # data and output paths.
    base = config_path.parent.parent if config_path.parent.name == "configs" else config_path.parent
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
            fast_panel_ids_path=(base / str(data["fast_panel_ids_path"])).resolve()
            if data.get("fast_panel_ids_path")
            else None,
        ),
        output_dir=(base / str(output["dir"])).resolve(),
        max_document_chars=(
            int(prompt["max_document_chars"])
            if prompt.get("max_document_chars") is not None
            else None
        ),
        visible_document_types=(
            tuple(str(value) for value in prompt["visible_document_types"])
            if prompt.get("visible_document_types") is not None
            else None
        ),
        context_strategy=str(prompt.get("context_strategy", "single")),
        overflow_split_enabled=bool(prompt.get("overflow_split_enabled", True)),
        strict_document_evidence=bool(prompt.get("strict_document_evidence", False)),
        absence_detection_strategy=str(prompt.get("absence_detection_strategy", "per_pass_or")),
        max_model_len=int(prompt.get("max_model_len", 32768)),
        output_reserve_tokens=int(prompt.get("output_reserve_tokens", 2500)),
        notice_anchor_chars=int(prompt.get("notice_anchor_chars", 4000)),
        reference_path=(base / str(prompt["reference_path"])).resolve()
        if prompt.get("reference_path")
        else None,
        reference_bundle_dir=(base / str(prompt["reference_bundle_dir"])).resolve()
        if prompt.get("reference_bundle_dir")
        else None,
        reference_routing=(str(prompt["reference_routing"])
                           if prompt.get("reference_routing") else None),
        decision_cards_path=(base / str(prompt["decision_cards_path"])).resolve()
        if prompt.get("decision_cards_path")
        else None,
        competition_products_path=(base / str(prompt["competition_products_path"])).resolve()
        if prompt.get("competition_products_path")
        else None,
        prompt_mode=str(prompt.get("mode", "baseline")),
        include_normalized_facts=bool(prompt.get("include_normalized_facts", False)),
        v8_composite_merge_enabled=bool(v8_composite_merge.get("enabled", False)),
        v8_composite_merge_mode=str(v8_composite_merge.get("mode", "fallback_or")),
        candidate_detection=bool(prompt.get("candidate_detection", False)),
        active_items=tuple(str(item) for item in prompt.get("active_items", (f"v{i}" for i in range(1, 25)))),
        prompt_layout=str(prompt.get("layout", "plain")),
        prompt_profile=str(prompt.get("profile", "default")),
        role_directive=str(prompt.get("role_directive", "standard")),
        item_catalog_style=str(prompt.get("item_catalog_style", "minimal")),
        metadata_style=str(prompt.get("metadata_style", "full_json")),
        output_mode=str(prompt.get("output_mode", "labels_and_evidence")),
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
            tokenizer_source=(str(llm["tokenizer_source"])
                              if llm.get("tokenizer_source") else None),
            reasoning_effort=(str(llm["reasoning_effort"])
                              if llm.get("reasoning_effort") else None),
        ),
        review_run=(
            ReviewRunConfig(
                mode=str(review_run["mode"]),
                final_judgment_source=str(review_run["final_judgment_source"]),
            )
            if review_run is not None
            else None
        ),
        resume=bool(run.get("resume", True)),
        concurrency=int(run.get("concurrency", 1)),
        local_limit=int(run["local_limit"]) if run.get("local_limit") is not None else None,
    )
    if config.llm.provider not in {"openrouter", "openai"}:
        raise ValueError(f"unsupported local provider: {config.llm.provider}")
    if config.max_document_chars is not None and config.max_document_chars < 1:
        raise ValueError("prompt.max_document_chars must be positive")
    if config.visible_document_types is not None:
        allowed_document_types = {"공고문", "규격서", "과업지시서", "제안요청서", "예외공표서", "기타"}
        if not config.visible_document_types:
            raise ValueError("prompt.visible_document_types must not be empty")
        if "공고문" not in config.visible_document_types:
            raise ValueError("prompt.visible_document_types must include 공고문")
        if len(config.visible_document_types) != len(set(config.visible_document_types)):
            raise ValueError("prompt.visible_document_types must not contain duplicates")
        if any(value not in allowed_document_types for value in config.visible_document_types):
            raise ValueError("prompt.visible_document_types contains an unsupported type")
    if config.data.fast_panel_ids_path and not config.data.fast_panel_ids_path.is_file():
        raise ValueError("data.fast_panel_ids_path must point to an existing file")
    if config.prompt_mode not in {"baseline", "structured", "guided"}:
        raise ValueError("prompt.mode must be baseline, structured, or guided")
    if config.prompt_layout not in {"plain", "markdown", "markdown_v2"}:
        raise ValueError("prompt.layout must be plain, markdown, or markdown_v2")
    if config.prompt_profile not in {
        "default", "official_baseline_v1", "official_baseline_subset_v1",
    }:
        raise ValueError(
            "prompt.profile must be default, official_baseline_v1, or "
            "official_baseline_subset_v1"
        )
    if config.role_directive not in {
        "standard", "compliance_expert_v1", "source_first_v1"
    }:
        raise ValueError(
            "prompt.role_directive must be standard, compliance_expert_v1, or source_first_v1"
        )
    if config.item_catalog_style not in {"minimal", "official_references"}:
        raise ValueError("prompt.item_catalog_style must be minimal or official_references")
    if config.metadata_style not in {"full_json", "official_lines"}:
        raise ValueError("prompt.metadata_style must be full_json or official_lines")
    if config.output_mode not in {"labels_and_evidence", "labels_only", "labels_and_anchor", "labels_and_sparse_evidence"}:
        raise ValueError("invalid prompt.output_mode")
    if config.output_mode == "labels_only" and config.strict_document_evidence:
        raise ValueError("labels_only cannot use strict_document_evidence")
    if config.output_mode in {"labels_and_anchor", "labels_and_sparse_evidence"} and not config.strict_document_evidence:
        raise ValueError("labels_and_anchor requires strict_document_evidence")
    expected_items = {f"v{i}" for i in range(1, 25)}
    if not config.active_items or any(item not in expected_items for item in config.active_items):
        raise ValueError("prompt.active_items must be a non-empty subset of v1..v24")
    if len(config.active_items) != len(set(config.active_items)):
        raise ValueError("prompt.active_items must not contain duplicates")
    if config.context_strategy not in {"single", "single_no_split", "split", "full_split_merge"}:
        raise ValueError("prompt.context_strategy must be single, single_no_split, split, or full_split_merge")
    if config.context_strategy == "split" and config.max_document_chars is None:
        raise ValueError("split context strategy requires prompt.max_document_chars")
    if config.context_strategy == "full_split_merge" and config.max_document_chars is not None:
        raise ValueError("full_split_merge requires prompt.max_document_chars: null")
    if config.reference_path and config.reference_bundle_dir:
        raise ValueError("reference_path and reference_bundle_dir are mutually exclusive")
    if config.reference_bundle_dir and config.reference_routing not in {
        "metadata_v1", "metadata_profile_group_v2"
    }:
        raise ValueError(
            "reference_bundle_dir requires prompt.reference_routing: metadata_v1 or metadata_profile_group_v2"
        )
    if config.reference_routing and not config.reference_bundle_dir:
        raise ValueError("prompt.reference_routing requires reference_bundle_dir")
    if config.strict_document_evidence and config.context_strategy != "full_split_merge":
        raise ValueError("strict_document_evidence requires full_split_merge context strategy")
    if config.absence_detection_strategy not in {"per_pass_or", "per_pass_and"}:
        raise ValueError("absence_detection_strategy must be per_pass_or or per_pass_and")
    if config.absence_detection_strategy == "per_pass_and" and config.context_strategy != "full_split_merge":
        raise ValueError("per_pass_and absence detection requires full_split_merge context strategy")
    if config.v8_composite_merge_enabled and "v8" not in config.active_items:
        raise ValueError("v8_composite_merge.enabled requires prompt.active_items to include v8")
    if config.output_mode == "labels_only" and config.v8_composite_merge_enabled:
        raise ValueError("labels_only cannot use v8_composite_merge")
    if config.v8_composite_merge_mode not in {"fallback_or", "strict_conjunction"}:
        raise ValueError("v8_composite_merge.mode must be fallback_or or strict_conjunction")
    if config.notice_anchor_chars < 0:
        raise ValueError("prompt.notice_anchor_chars must be non-negative")
    if not 0 < config.output_reserve_tokens < config.max_model_len:
        raise ValueError("prompt.output_reserve_tokens must be within prompt.max_model_len")
    if config.concurrency < 1:
        raise ValueError("run.concurrency must be positive")
    if config.local_limit is not None and config.local_limit < 1:
        raise ValueError("run.local_limit must be positive")
    if config.llm.provider_sort not in {"price", "throughput", "latency"}:
        raise ValueError("llm.provider_sort must be price, throughput, or latency")
    if config.llm.min_request_interval_seconds < 0:
        raise ValueError("llm.min_request_interval_seconds must be non-negative")
    if config.llm.reasoning_effort and config.llm.reasoning_effort not in {
        "none", "low", "medium", "high", "xhigh", "max"
    }:
        raise ValueError("llm.reasoning_effort must be a supported GPT-5.6 effort")
    if config.review_run is not None:
        if config.review_run.mode != "untrusted_label_only_adjudication_v1":
            raise ValueError("review_run.mode is unsupported")
        if config.review_run.final_judgment_source != "pass_b":
            raise ValueError("review_run.final_judgment_source must be pass_b")
        if config.context_strategy != "single" or config.overflow_split_enabled:
            raise ValueError("two-pass adjudication requires one fixed single context")
        if config.active_items != tuple(f"v{index}" for index in range(1, 25)):
            raise ValueError("two-pass adjudication requires all v1..v24 items")
    return config
