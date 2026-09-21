"""OpenRouter transport only; it cannot alter prompts, schemas, or judgments."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
import time
from typing import Any

import requests

from ..config import ProviderConfig


class OpenRouterRuntime:
    def __init__(self, config: ProviderConfig, api_key: str) -> None:
        if not api_key:
            raise ValueError("OpenRouter API key is empty")
        self.config = config
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self._lock = Lock()
        self._last_started = 0.0

    def _slot(self) -> None:
        with self._lock:
            delay = self.config.min_request_interval_seconds - (time.monotonic() - self._last_started)
            if delay > 0:
                time.sleep(delay)
            self._last_started = time.monotonic()

    def complete(self, task: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "model": self.config.model,
            "messages": task["messages"],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "seed": self.config.seed,
            "stream": False,
            "provider": {
                "require_parameters": self.config.require_parameters,
                "sort": self.config.provider_sort,
            },
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": f"pps_{task['arm'].lower()}_judgment",
                    "strict": True,
                    "schema": task["schema"],
                },
            },
        }
        last_error = "unknown"
        for attempt in range(self.config.request_retries + 1):
            started = time.monotonic()
            response = None
            try:
                self._slot()
                response = requests.post(
                    self.config.api_url, headers=self.headers, json=payload,
                    timeout=self.config.timeout_seconds,
                )
                if response.ok:
                    body = response.json()
                    choice = body["choices"][0]
                    content = choice["message"]["content"]
                    if not isinstance(content, str) or not content.strip():
                        raise RuntimeError("empty completion")
                    return {
                        "content": content,
                        "finish_reason": choice.get("finish_reason"),
                        "invalid": False,
                        "model": body.get("model", self.config.model),
                        "usage": body.get("usage") or {},
                        "latency_seconds": round(time.monotonic() - started, 3),
                        "attempts": attempt + 1,
                    }
                last_error = f"HTTP {response.status_code}: {response.text[:500]}"
                in_flight_budget = (
                    response.status_code == 402
                    and "in_flight_budget_exhausted" in response.text
                )
                retryable = (
                    response.status_code in {408, 409, 429}
                    or response.status_code >= 500
                    or in_flight_budget
                )
                if not retryable:
                    raise RuntimeError(last_error)
            except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as error:
                last_error = f"{type(error).__name__}: {error}"
            if attempt < self.config.request_retries:
                retry_after = 0.0
                if response is not None:
                    try:
                        retry_after = float(response.headers.get("Retry-After", 0))
                    except ValueError:
                        pass
                time.sleep(min(120.0, max(retry_after, 2.0**attempt)))
        raise RuntimeError(f"OpenRouter completion failed: {last_error}")


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
