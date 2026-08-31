from pathlib import Path

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
