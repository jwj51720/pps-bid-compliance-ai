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
