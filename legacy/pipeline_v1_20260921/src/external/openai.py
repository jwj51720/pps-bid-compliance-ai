"""OpenAI Responses API adapter with strict JSON-schema output."""

from __future__ import annotations

from dataclasses import dataclass
import time
from threading import Lock
from typing import Any

import requests


class OpenAIError(RuntimeError):
    """Raised when a Responses API completion cannot be recovered."""


@dataclass(frozen=True)
class Completion:
    content: str
    model: str
    latency_seconds: float
    usage: dict[str, Any]
    finish_reason: str | None = None


def _output_text(body: dict[str, Any]) -> str:
    """Extract text from both SDK-style and raw Responses API payloads."""
    direct = body.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct
    texts: list[str] = []
    for item in body.get("output", []):
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") == "output_text":
                text = content.get("text")
                if isinstance(text, str):
                    texts.append(text)
    result = "".join(texts)
    if not result.strip():
        raise OpenAIError("Responses API returned no output_text")
    return result


class OpenAIClient:
    """Minimal direct Responses API client; no SDK dependency is required."""

    def __init__(
        self,
        *,
        api_key: str,
        api_url: str,
        model: str,
        max_tokens: int,
        timeout_seconds: float,
        request_retries: int,
        min_request_interval_seconds: float,
        reasoning_effort: str | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI API key is empty")
        self.api_url = api_url
        self.model = model
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
        self.request_retries = request_retries
        self.min_request_interval_seconds = min_request_interval_seconds
        self.reasoning_effort = reasoning_effort
        self._request_lock = Lock()
        self._last_request_started = 0.0
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _wait_for_request_slot(self) -> None:
        with self._request_lock:
            elapsed = time.monotonic() - self._last_request_started
            delay = self.min_request_interval_seconds - elapsed
            if delay > 0:
                time.sleep(delay)
            self._last_request_started = time.monotonic()

    def complete(
        self,
        messages: list[dict[str, str]],
        response_schema: dict[str, Any],
    ) -> Completion:
        payload: dict[str, Any] = {
            "model": self.model,
            "input": messages,
            "max_output_tokens": self.max_tokens,
            "store": False,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "pps_compliance_judgment",
                    "strict": True,
                    "schema": response_schema,
                },
            },
        }
        if self.reasoning_effort:
            payload["reasoning"] = {"effort": self.reasoning_effort}
        last_error = "unknown error"
        for attempt in range(self.request_retries + 1):
            started = time.monotonic()
            response: requests.Response | None = None
            try:
                self._wait_for_request_slot()
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=self.timeout_seconds,
                )
            except requests.RequestException as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                retryable = True
            else:
                retryable = response.status_code in {408, 409, 429} or response.status_code >= 500
                if response.ok:
                    try:
                        body = response.json()
                        if not isinstance(body, dict):
                            raise ValueError("response body is not an object")
                        content = _output_text(body)
                    except (ValueError, TypeError, KeyError, IndexError) as exc:
                        raise OpenAIError(f"malformed Responses API response: {exc}") from exc
                    return Completion(
                        content=content,
                        model=str(body.get("model", self.model)),
                        latency_seconds=round(time.monotonic() - started, 3),
                        usage=body.get("usage") if isinstance(body.get("usage"), dict) else {},
                        finish_reason=str(body.get("status")) if body.get("status") else None,
                    )
                try:
                    error_body = response.json()
                    error_message = error_body.get("error", {}).get("message", response.text)
                except ValueError:
                    error_message = response.text
                last_error = f"HTTP {response.status_code}: {str(error_message)[:500]}"
                if not retryable:
                    raise OpenAIError(last_error)
            if attempt < self.request_retries and retryable:
                retry_after = 0.0
                if response is not None:
                    try:
                        retry_after = float(response.headers.get("Retry-After", 0))
                    except ValueError:
                        retry_after = 0.0
                time.sleep(min(60.0, max(retry_after, 2.0**attempt)))
        raise OpenAIError(f"request failed after retries: {last_error}")
