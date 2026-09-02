from __future__ import annotations

from types import SimpleNamespace

from src.external.openai import OpenAIClient


def test_openai_client_uses_responses_strict_schema(monkeypatch) -> None:
    captured = {}

    def post(url, headers, json, timeout):
        captured.update(url=url, headers=headers, json=json, timeout=timeout)
        return SimpleNamespace(
            ok=True,
            status_code=200,
            json=lambda: {
                "model": "gpt-5.6-sol",
                "status": "completed",
                "output": [{"type": "message", "content": [{"type": "output_text", "text": "{}"}]}],
                "usage": {"input_tokens": 1},
            },
        )

    monkeypatch.setattr("src.external.openai.requests.post", post)
    client = OpenAIClient(
        api_key="test", api_url="https://api.openai.com/v1/responses",
        model="gpt-5.6-sol", max_tokens=2500, timeout_seconds=30,
        request_retries=0, min_request_interval_seconds=0,
    )
    completion = client.complete([{"role": "user", "content": "판정"}], {"type": "object"})

    assert completion.content == "{}"
    assert captured["json"]["model"] == "gpt-5.6-sol"
    assert captured["json"]["store"] is False
    assert captured["json"]["text"]["format"]["strict"] is True
