"""Small OpenRouter chat-completions adapter with bounded retries."""

from __future__ import annotations

import time
from threading import Lock
from dataclasses import dataclass
from typing import Any

import requests


class OpenRouterError(RuntimeError):
    """Raised when a completion cannot be obtained safely."""


@dataclass(frozen=True)
class Completion:
    content: str
    model: str
    latency_seconds: float
    usage: dict[str, Any]
    finish_reason: str | None = None


class OpenRouterClient:
    def __init__(
        self,
        *,
        api_key: str,
        api_url: str,
        model: str,
        temperature: float,
        max_tokens: int,
        seed: int,
        timeout_seconds: float,
        request_retries: int,
        provider_sort: str,
        require_parameters: bool,
        min_request_interval_seconds: float,
    ) -> None:
        if not api_key:
            raise ValueError("OpenRouter API key is empty")
        self.api_url = api_url
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.seed = seed
        self.timeout_seconds = timeout_seconds
        self.request_retries = request_retries
        self.provider_sort = provider_sort
        self.require_parameters = require_parameters
        self.min_request_interval_seconds = min_request_interval_seconds
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
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "seed": self.seed,
            "stream": False,
            "provider": {
                "require_parameters": self.require_parameters,
                "sort": self.provider_sort,
            },
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "pps_compliance_judgment",
                    "strict": True,
                    "schema": response_schema,
                },
            },
        }
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
                        choice = body["choices"][0]
                        content = choice["message"]["content"]
                    except (ValueError, KeyError, IndexError, TypeError) as exc:
                        raise OpenRouterError(f"malformed OpenRouter response: {exc}") from exc
                    if not isinstance(content, str) or not content.strip():
                        raise OpenRouterError("OpenRouter returned empty content")
                    return Completion(
                        content=content,
                        model=str(body.get("model", self.model)),
                        latency_seconds=round(time.monotonic() - started, 3),
                        usage=body.get("usage") if isinstance(body.get("usage"), dict) else {},
                        finish_reason=str(choice.get("finish_reason"))
                        if choice.get("finish_reason") is not None
                        else None,
                    )
                try:
                    error_body = response.json()
                    error_message = error_body.get("error", {}).get("message", response.text)
                except ValueError:
                    error_message = response.text
                last_error = f"HTTP {response.status_code}: {str(error_message)[:500]}"
                if not retryable:
                    raise OpenRouterError(last_error)
            if attempt < self.request_retries and retryable:
                retry_after = 0.0
                if response is not None:
                    try:
                        retry_after = float(response.headers.get("Retry-After", 0))
                    except ValueError:
                        retry_after = 0.0
                time.sleep(min(60.0, max(retry_after, 2.0**attempt)))
        raise OpenRouterError(f"request failed after retries: {last_error}")


class MockClient:
    """Deterministic no-network client for pipeline and format smoke tests."""

    model = "mock"

    def complete(
        self,
        messages: list[dict[str, str]],
        response_schema: dict[str, Any],
    ) -> Completion:
        import json

        del messages
        properties = response_schema["properties"]
        fact_inventory = bool(properties) and all(
            isinstance(value, dict) and value.get("type") == "array"
            for value in properties.values()
        )
        if fact_inventory:
            content = json.dumps({item: [] for item in properties}, ensure_ascii=False)
            return Completion(content=content, model=self.model, latency_seconds=0.0, usage={})
        triage = bool(properties) and all(
            isinstance(value, dict)
            and value.get("type") == "string"
            and "enum" in value
            for value in properties.values()
        )
        if triage:
            payload = {item: "해당없음" for item in properties}
            content = json.dumps(payload, ensure_ascii=False)
            return Completion(content=content, model=self.model, latency_seconds=0.0, usage={})
        locator = bool(properties) and all(
            isinstance(value, dict) and value.get("type") == ["string", "null"]
            for value in properties.values()
        )
        if locator:
            content = json.dumps({item: None for item in properties}, ensure_ascii=False)
            return Completion(content=content, model=self.model, latency_seconds=0.0, usage={})
        if "판정" in properties and "종료일_역할" in properties:
            payload = {
                "지방협상_근거": None, "공고일_근거": None,
                "종료일_근거": None, "종료일_역할": "없음",
                "긴급재공고_근거": None,
                "판정": {"위반여부": 0, "근거문구": None},
            }
            content = json.dumps(payload, ensure_ascii=False)
            return Completion(content=content, model=self.model, latency_seconds=0.0, usage={})
        if "v23기간대조" in properties and "판정" in properties:
            decision_schema = properties["판정"]["properties"]["v23"]
            decision = (
                0
                if decision_schema.get("type") == "integer"
                else {"위반여부": 0, "근거문구": None}
            )
            payload = {
                "v23기간대조": {
                    "적용계약법": "불명", "계약방식": "불명",
                    "입찰추정가격": None, "금액구간": "불명",
                    "적용최소일수": None, "공고일근거": None,
                    "종료일근거": None, "종료일역할": "불명",
                    "계산일수": None, "긴급재공고": "불명",
                    "카드대조": "판단불가",
                },
                "판정": {"v23": decision},
            }
            content = json.dumps(payload, ensure_ascii=False)
            return Completion(content=content, model=self.model, latency_seconds=0.0, usage={})
        if "v19역할대조" in properties and "판정" in properties:
            decision_schema = properties["판정"]["properties"]["v19"]
            decision = (
                0
                if decision_schema.get("type") == "integer"
                else {"위반여부": 0, "근거문구": None}
            )
            payload = {
                "v19역할대조": {
                    "후보원문": None,
                    "서류종류": "불명",
                    "요구행위": "불명",
                    "기준시점": "불명",
                    "입찰효과": "불명",
                    "카드대조": "판단불가",
                },
                "판정": {"v19": decision},
            }
            content = json.dumps(payload, ensure_ascii=False)
            return Completion(content=content, model=self.model, latency_seconds=0.0, usage={})
        if "v24대조" in properties and "판정" in properties:
            label_properties = properties["판정"]["properties"]
            payload = {
                "v24대조": [],
                "판정": {
                    item: {"위반여부": 0, "근거문구": None}
                    for item in label_properties
                },
            }
            content = json.dumps(payload, ensure_ascii=False)
            return Completion(content=content, model=self.model, latency_seconds=0.0, usage={})
        if "v10제품검토" in properties and "판정" in properties:
            payload = {
                "v10제품검토": {
                    "실제구매대상": None,
                    "고시후보세부품명": None,
                    "적용조건상태": "불명",
                    "경쟁제품적용": "불명",
                    "직접생산요구": "불명",
                    "직접생산요구원문": None,
                },
                "판정": {"v10": 0},
            }
            content = json.dumps(payload, ensure_ascii=False)
            return Completion(content=content, model=self.model, latency_seconds=0.0, usage={})
        if "v12제품대상검토" in properties and "판정" in properties:
            decision_schema = properties["판정"]["properties"]["v12"]
            decision = (
                0
                if decision_schema.get("type") == "integer"
                else {"위반여부": 0, "근거문구": None}
            )
            payload = {
                "v12제품대상검토": {
                    "실제구매대상원문": None,
                    "고시후보세부품명": None,
                    "고시후보출처": "불명",
                    "구매대상관계": "불명",
                    "적용조건상태": "불명",
                    "경쟁제품적용": "불명",
                    "직접생산요구원문": None,
                    "직접생산요구역할": "불명",
                    "허용사유": "불명",
                    "카드대조": "판단불가",
                },
                "판정": {"v12": decision},
            }
            content = json.dumps(payload, ensure_ascii=False)
            return Completion(content=content, model=self.model, latency_seconds=0.0, usage={})
        if "v13제품기업검토" in properties and "판정" in properties:
            payload = {
                "v13제품기업검토": {
                    "실제구매대상": None,
                    "고시후보세부품명": None,
                    "적용조건상태": "불명",
                    "경쟁제품적용": "불명",
                    "기업제한원문": None,
                    "기업제한역할": "불명",
                    "일반중기업참가": "불명",
                    "허용사유": "불명",
                    "카드대조": "판단불가",
                },
                "판정": {"v13": {"위반여부": 0, "근거문구": None}},
            }
            content = json.dumps(payload, ensure_ascii=False)
            return Completion(content=content, model=self.model, latency_seconds=0.0, usage={})
        if "사실목록" in properties and "판정" in properties:
            fact_properties = properties["사실목록"]["properties"]
            label_properties = properties["판정"]["properties"]
            payload = {
                "사실목록": {category: [] for category in fact_properties},
                "판정": {
                    item: {"위반여부": 0, "근거문구": None}
                    for item in label_properties
                },
            }
            content = json.dumps(payload, ensure_ascii=False)
            return Completion(content=content, model=self.model, latency_seconds=0.0, usage={})
        if "v4검토" in properties and "판정" in properties:
            label_properties = properties["판정"]["properties"]
            payload = {
                "v4검토": {
                    "참가자격실적근거": None,
                    "금액구간": "불명",
                    "특정발주기관한정": "불명",
                    "특정실적종류한정": "불명",
                    "구체적필요사유": "불명",
                    "카드대조": "판단불가",
                },
                "판정": {
                    item: {"위반여부": 0, "근거문구": None}
                    for item in label_properties
                },
            }
            content = json.dumps(payload, ensure_ascii=False)
            return Completion(content=content, model=self.model, latency_seconds=0.0, usage={})
        if "v4역할검토" in properties and "판정" in properties:
            label_properties = properties["판정"]["properties"]
            payload = {
                "v4역할검토": {
                    "실적요구원문": None,
                    "조항역할": "불명",
                    "과거계약실적요구": "불명",
                    "발주기관범위": "불명",
                    "실적종류범위": "불명",
                    "유사동등실적인정": "불명",
                    "구체적필요사유": "불명",
                    "카드대조": "판단불가",
                },
                "판정": {
                    item: {"위반여부": 0, "근거문구": None}
                    for item in label_properties
                },
            }
            content = json.dumps(payload, ensure_ascii=False)
            return Completion(content=content, model=self.model, latency_seconds=0.0, usage={})
        if "v5수치대조" in properties and "판정" in properties:
            payload = {
                "v5수치대조": {
                    "적용분기": "불명",
                    "입찰추정가격": None,
                    "적용임계값": None,
                    "금액관계": "불명",
                    "지역문구역할": "불명",
                    "허용사유": "불명",
                },
                "판정": {"v5": {"위반여부": 0, "근거문구": None}},
            }
            content = json.dumps(payload, ensure_ascii=False)
            return Completion(content=content, model=self.model, latency_seconds=0.0, usage={})
        if "v6지역대조" in properties and "판정" in properties:
            payload = {
                "v6지역대조": {
                    "금액구간": "불명",
                    "지역참가자격원문": None,
                    "지역문구역할": "불명",
                    "기초지역참가제한": "불명",
                    "계약절차": "불명",
                    "허용요건": "불명",
                    "카드대조": "판단불가",
                },
                "판정": {"v6": {"위반여부": 0, "근거문구": None}},
            }
            content = json.dumps(payload, ensure_ascii=False)
            return Completion(content=content, model=self.model, latency_seconds=0.0, usage={})
        sparse = "판정" in properties and "발췌" in properties
        label_properties = properties["판정"]["properties"] if sparse else properties
        first_item = next(iter(label_properties))
        labels_only = label_properties[first_item]["type"] == "integer"
        anchor_mode = not labels_only and "판단어구" in label_properties[first_item]["properties"]
        payload = (
            {"판정": {item: 0 for item in label_properties}, "발췌": [], "부재검토": {item: "필수조건_확인" for item in label_properties if item in {"v10", "v11", "v16", "v18", "v20"}}}
            if sparse
            else {item: 0 for item in label_properties}
            if labels_only
            else {item: {"위반여부": 0, "판단어구": None} for item in label_properties}
            if anchor_mode
            else {item: {"위반여부": 0, "근거문구": None} for item in label_properties}
        )
        if "v8병합관찰" in response_schema.get("properties", {}):
            payload["v8병합관찰"] = {"상태": "검토", "관찰근거문구": None}
        content = json.dumps(payload, ensure_ascii=False)
        return Completion(content=content, model=self.model, latency_seconds=0.0, usage={})
