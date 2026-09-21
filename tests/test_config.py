from pathlib import Path

import pytest

from src.config import load_config


def test_model_is_owned_by_config_not_environment(monkeypatch, tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text(
        """
experiment: {id: test}
data: {root: data, input: input.jsonl, item_table: items.json}
output: {dir: outputs/test}
prompt: {max_document_chars: 4000}
llm:
  provider: openrouter
  model: google/gemma-4-26b-a4b-it:free
  api_key_env: OPENROUTER_API_KEY
  api_url: https://openrouter.ai/api/v1/chat/completions
  temperature: 0
  max_tokens: 100
  seed: 1
  timeout_seconds: 10
  request_retries: 1
  prediction_attempts: 1
  provider_sort: throughput
  require_parameters: false
run: {resume: true, concurrency: 1}
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENROUTER_MODEL", "paid-model")

    loaded = load_config(config)

    assert loaded.llm.model == "google/gemma-4-26b-a4b-it:free"
    assert loaded.llm.min_request_interval_seconds == 0
    assert loaded.local_limit is None


def test_explicit_staged_run_off_is_disabled(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text(
        """
experiment: {id: test}
data: {root: data, input: input.jsonl, item_table: items.json}
output: {dir: outputs/test}
prompt: {max_document_chars: 4000}
llm:
  provider: openrouter
  model: google/gemma-4-26b-a4b-it
  api_key_env: OPENROUTER_API_KEY
  api_url: https://openrouter.ai/api/v1/chat/completions
  temperature: 0
  max_tokens: 100
  seed: 1
  timeout_seconds: 10
  request_retries: 1
  prediction_attempts: 1
staged_run: {mode: "off"}
""",
        encoding="utf-8",
    )

    loaded = load_config(config)

    assert loaded.staged_run is None


def test_canonical_config_loads_with_staging_disabled() -> None:
    loaded = load_config(Path("config.yaml"))

    assert loaded.staged_run is None


def test_null_document_limit_and_local_limit_are_configured(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text(
        """
experiment: {id: test}
data: {root: data, input: input.jsonl, item_table: items.json}
output: {dir: outputs/test}
prompt: {max_document_chars: null}
llm:
  provider: openrouter
  model: google/gemma-4-26b-a4b-it:free
  api_key_env: OPENROUTER_API_KEY
  api_url: https://openrouter.ai/api/v1/chat/completions
  temperature: 0
  max_tokens: 100
  seed: 1
  timeout_seconds: 10
  request_retries: 1
  prediction_attempts: 1
  provider_sort: throughput
  require_parameters: false
run: {resume: true, concurrency: 1, local_limit: 20}
""",
        encoding="utf-8",
    )

    loaded = load_config(config)

    assert loaded.max_document_chars is None
    assert loaded.local_limit == 20
    assert loaded.overflow_split_enabled is True
    assert loaded.max_model_len == 32768
    assert loaded.output_reserve_tokens == 2500
    assert loaded.competition_product_context_mode == "names_only_v1"
    assert loaded.organizer_input_semantics_mode == "off"


def test_config_inheritance_resolves_complete_parent_chain(tmp_path: Path) -> None:
    base = tmp_path / "base.yaml"
    base.write_text(
        """
experiment: {id: base}
data: {root: data, input: input.jsonl, item_table: items.json}
output: {dir: outputs/base}
prompt: {max_document_chars: null, output_mode: labels_and_evidence}
llm:
  provider: openrouter
  model: google/gemma-4-26b-a4b-it
  api_key_env: OPENROUTER_API_KEY
  api_url: https://openrouter.ai/api/v1/chat/completions
  temperature: 0
  max_tokens: 100
  seed: 1
  timeout_seconds: 10
  request_retries: 1
  prediction_attempts: 1
  provider_sort: throughput
  require_parameters: true
run: {resume: true, concurrency: 1}
""",
        encoding="utf-8",
    )
    middle = tmp_path / "middle.yaml"
    middle.write_text(
        """
inherits: base.yaml
experiment: {id: middle}
prompt: {output_mode: labels_only}
""",
        encoding="utf-8",
    )
    leaf = tmp_path / "leaf.yaml"
    leaf.write_text(
        """
inherits: middle.yaml
experiment: {id: leaf}
output: {dir: outputs/leaf}
""",
        encoding="utf-8",
    )

    loaded = load_config(leaf)

    assert loaded.experiment_id == "leaf"
    assert loaded.data.input_path == tmp_path / "data/input.jsonl"
    assert loaded.output_dir == tmp_path / "outputs/leaf"
    assert loaded.output_mode == "labels_only"
    assert loaded.llm.model == "google/gemma-4-26b-a4b-it"


def test_vonly_draft_stage_allows_vonly_final_owner() -> None:
    loaded = load_config(
        Path("configs/config.exp251-v10-vonly-draft-verify-fast-panel-c4.yaml")
    )

    assert loaded.output_mode == "labels_only"
    assert loaded.staged_run is not None
    assert loaded.staged_run.mode == "vonly_draft_full_final_v1"


def test_v13_product_scope_experiment_loads_as_v13_ve() -> None:
    loaded = load_config(
        Path("configs/config.exp254-v13-product-scope-review-fast-panel-c4.yaml")
    )

    assert loaded.prompt_mode == "v13_product_scope_review_v1"
    assert loaded.active_items == ("v13",)
    assert loaded.output_mode == "labels_and_evidence"


def test_v12_product_target_experiments_load_as_paired_output_modes() -> None:
    ve = load_config(
        Path("configs/config.exp299-v12-product-target-review-ve-fast-panel-c4.yaml")
    )
    vonly = load_config(
        Path("configs/config.exp300-v12-product-target-review-vonly-fast-panel-c4.yaml")
    )

    assert ve.prompt_mode == vonly.prompt_mode == "v12_product_target_review_v1"
    assert ve.active_items == vonly.active_items == ("v12",)
    assert ve.output_mode == "labels_and_evidence"
    assert vonly.output_mode == "labels_only"


def test_v6_geography_stage_is_v6_only_full_source_ve() -> None:
    loaded = load_config(
        Path("configs/config.exp267-v6-geography-inventory-full-final-fast-panel-c4.yaml")
    )

    assert loaded.staged_run is not None
    assert loaded.staged_run.mode == "v6_geography_inventory_full_final_v1"
    assert loaded.active_items == ("v6",)
    assert loaded.output_mode == "labels_and_evidence"
    assert loaded.max_document_chars is None
    assert loaded.overflow_split_enabled


def test_v6_geography_proof_experiment_loads_as_v6_only_ve() -> None:
    loaded = load_config(
        Path("configs/config.exp268-v6-geography-proof-fast-panel-c4.yaml")
    )

    assert loaded.prompt_mode == "v6_geography_proof_v1"
    assert loaded.active_items == ("v6",)
    assert loaded.output_mode == "labels_and_evidence"


def test_v23_quantitative_proof_experiments_load_as_paired_output_modes() -> None:
    ve = load_config(
        Path("configs/config.exp273-v23-quantitative-proof-ve-fast-panel-c4.yaml")
    )
    vonly = load_config(
        Path("configs/config.exp274-v23-quantitative-proof-vonly-fast-panel-c4.yaml")
    )

    assert ve.prompt_mode == vonly.prompt_mode == "v23_quantitative_proof_v1"
    assert ve.active_items == vonly.active_items == ("v23",)
    assert ve.output_mode == "labels_and_evidence"
    assert vonly.output_mode == "labels_only"


def test_v19_role_proof_experiments_load_as_paired_output_modes() -> None:
    ve = load_config(Path("configs/config.exp285-v19-role-proof-ve-fast-panel-c4.yaml"))
    vonly = load_config(Path("configs/config.exp286-v19-role-proof-vonly-fast-panel-c4.yaml"))

    assert ve.prompt_mode == vonly.prompt_mode == "v19_role_proof_v1"
    assert ve.active_items == vonly.active_items == ("v19",)
    assert ve.output_mode == "labels_and_evidence"
    assert vonly.output_mode == "labels_only"


def test_v8_operational_card_experiments_load_as_paired_output_modes() -> None:
    ve = load_config(
        Path("configs/config.exp291-v8-operational-card-ve-fast-panel-c4.yaml")
    )
    vonly = load_config(
        Path("configs/config.exp292-v8-operational-card-vonly-fast-panel-c4.yaml")
    )

    assert ve.prompt_mode == vonly.prompt_mode == "baseline"
    assert ve.active_items == vonly.active_items == ("v8",)
    assert ve.output_mode == "labels_and_evidence"
    assert vonly.output_mode == "labels_only"
    assert ve.decision_cards_path == vonly.decision_cards_path


def test_config_inheritance_cycle_is_rejected(tmp_path: Path) -> None:
    first = tmp_path / "first.yaml"
    second = tmp_path / "second.yaml"
    first.write_text("inherits: second.yaml\n", encoding="utf-8")
    second.write_text("inherits: first.yaml\n", encoding="utf-8")

    with pytest.raises(ValueError, match="inheritance cycle"):
        load_config(first)


def test_complete_fact_profile_rejects_a_character_prefix(tmp_path: Path) -> None:
    """A full-fact candidate cannot quietly become the historical 4k control."""
    config = tmp_path / "config.yaml"
    config.write_text(
        """
experiment: {id: test}
data: {root: data, input: input.jsonl, item_table: items.json}
output: {dir: outputs/test}
prompt: {max_document_chars: 4000, profile: complete_fact_v1}
llm:
  provider: openrouter
  model: google/gemma-4-26b-a4b-it:free
  api_key_env: OPENROUTER_API_KEY
  api_url: https://openrouter.ai/api/v1/chat/completions
  temperature: 0
  max_tokens: 100
  seed: 1
  timeout_seconds: 10
  request_retries: 1
  prediction_attempts: 1
  provider_sort: throughput
  require_parameters: false
run: {resume: true, concurrency: 1}
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="complete_fact profiles require"):
        load_config(config)


def test_configs_directory_keeps_repository_relative_paths(tmp_path: Path) -> None:
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    reference = tmp_path / "data" / "derived" / "reference.txt"
    reference.parent.mkdir(parents=True)
    reference.write_text("official reference", encoding="utf-8")
    config = config_dir / "probe.yaml"
    config.write_text(
        """
experiment: {id: test}
data: {root: data, input: input.jsonl, item_table: items.json}
output: {dir: outputs/test}
prompt: {max_document_chars: null, reference_path: data/derived/reference.txt}
llm:
  provider: openrouter
  model: google/gemma-4-26b-a4b-it
  api_key_env: OPENROUTER_API_KEY
  api_url: https://openrouter.ai/api/v1/chat/completions
  temperature: 0
  max_tokens: 100
  seed: 1
  timeout_seconds: 10
  request_retries: 1
  prediction_attempts: 1
  provider_sort: throughput
  require_parameters: true
run: {resume: true, concurrency: 1}
""",
        encoding="utf-8",
    )

    loaded = load_config(config)

    assert loaded.data.root == tmp_path / "data"
    assert loaded.output_dir == tmp_path / "outputs/test"
    assert loaded.reference_path == reference


def test_fast_panel_path_is_resolved_from_configs_directory(tmp_path: Path) -> None:
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    panel = config_dir / "panel.json"
    panel.write_text('{"ids": ["PPS-1"]}', encoding="utf-8")
    config = config_dir / "probe.yaml"
    config.write_text(
        """
experiment: {id: test}
data: {root: data, input: input.jsonl, item_table: items.json, fast_panel_ids_path: configs/panel.json}
output: {dir: outputs/test}
prompt: {max_document_chars: null}
llm:
  provider: openrouter
  model: google/gemma-4-26b-a4b-it
  api_key_env: OPENROUTER_API_KEY
  api_url: https://openrouter.ai/api/v1/chat/completions
  temperature: 0
  max_tokens: 100
  seed: 1
  timeout_seconds: 10
  request_retries: 1
  prediction_attempts: 1
  provider_sort: throughput
  require_parameters: true
run: {resume: true, concurrency: 1}
""",
        encoding="utf-8",
    )

    assert load_config(config).data.fast_panel_ids_path == panel


def test_full_split_merge_requires_full_document_token_mode(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text(
        """
experiment: {id: test}
data: {root: data, input: input.jsonl, item_table: items.json}
output: {dir: outputs/test}
prompt: {max_document_chars: null, context_strategy: full_split_merge}
llm:
  provider: openrouter
  model: google/gemma-4-26b-a4b-it:free
  api_key_env: OPENROUTER_API_KEY
  api_url: https://openrouter.ai/api/v1/chat/completions
  temperature: 0
  max_tokens: 100
  seed: 1
  timeout_seconds: 10
  request_retries: 1
  prediction_attempts: 1
  provider_sort: throughput
  require_parameters: false
run: {resume: true, concurrency: 1}
""",
        encoding="utf-8",
    )

    assert load_config(config).context_strategy == "full_split_merge"


def test_strict_document_evidence_rejects_non_document_split_mode(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text(
        """
experiment: {id: test}
data: {root: data, input: input.jsonl, item_table: items.json}
output: {dir: outputs/test}
prompt: {max_document_chars: null, strict_document_evidence: true}
llm:
  provider: openrouter
  model: google/gemma-4-26b-a4b-it:free
  api_key_env: OPENROUTER_API_KEY
  api_url: https://openrouter.ai/api/v1/chat/completions
  temperature: 0
  max_tokens: 100
  seed: 1
  timeout_seconds: 10
  request_retries: 1
  prediction_attempts: 1
  provider_sort: throughput
  require_parameters: false
run: {resume: true, concurrency: 1}
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="strict_document_evidence"):
        load_config(config)
