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
