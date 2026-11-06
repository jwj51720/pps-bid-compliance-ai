from src.external.openrouter import OpenRouterClient


class _Response:
    ok = True
    status_code = 200
    headers: dict[str, str] = {}

    @staticmethod
    def json():
        return {
            "model": "free-model",
            "choices": [{"finish_reason": "stop", "message": {"content": "{}"}}],
            "usage": {"completion_tokens": 2},
        }


def test_client_can_route_without_parameter_filter_and_records_finish_reason(monkeypatch) -> None:
    captured = {}

    def fake_post(url, *, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return _Response()

    monkeypatch.setattr("src.external.openrouter.requests.post", fake_post)
    client = OpenRouterClient(
        api_key="secret",
        api_url="https://example.invalid/chat",
        model="free-model",
        temperature=0,
        max_tokens=100,
        seed=1,
        timeout_seconds=10,
        request_retries=0,
        provider_sort="throughput",
        require_parameters=False,
        min_request_interval_seconds=0,
    )

    completion = client.complete([], {"type": "object"})

    assert captured["json"]["provider"]["require_parameters"] is False
    assert completion.finish_reason == "stop"


def test_runner_passes_configured_generation_limit_unchanged(monkeypatch) -> None:
    from scripts.run_experiment import _make_client
    from src.config import load_config

    captured = {}

    def fake_post(url, *, headers, json, timeout):
        captured.update(json)
        return _Response()

    config = load_config("configs/config.exp314-v18-only-existing-card-ve-fast-panel-c4.yaml")
    monkeypatch.setenv(config.llm.api_key_env, "test-not-a-real-key")
    monkeypatch.setattr("src.external.openrouter.requests.post", fake_post)
    client = _make_client(config, mock=False)
    client.complete([{"role": "user", "content": "actual notice placeholder"}],
                    {"type": "object"})
    assert config.llm.max_tokens == 2500
    assert captured["max_tokens"] == 2500
    assert captured["provider"]["require_parameters"] is True
    assert captured["temperature"] == config.llm.temperature
    assert captured["seed"] == config.llm.seed


def test_reported_over_limit_usage_is_preserved_without_content_override(monkeypatch) -> None:
    class OverLimitResponse(_Response):
        @staticmethod
        def json():
            return {
                "model": "test-model",
                "choices": [{"finish_reason": "length", "message": {"content": "{\"v18\": 0"}}],
                "usage": {"completion_tokens": 8192},
            }

    monkeypatch.setattr("src.external.openrouter.requests.post", lambda *a, **kw: OverLimitResponse())
    client = OpenRouterClient(
        api_key="test-not-a-real-key", api_url="https://example.invalid/chat",
        model="test-model", temperature=0, max_tokens=2500, seed=1,
        timeout_seconds=10, request_retries=0, provider_sort="price",
        require_parameters=True, min_request_interval_seconds=0,
    )
    result = client.complete([], {"type": "object"})
    assert result.usage["completion_tokens"] == 8192
    assert result.finish_reason == "length"
    assert result.content == '{"v18": 0'
