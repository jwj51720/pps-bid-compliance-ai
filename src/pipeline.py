"""Shared notice-to-judgment baseline pipeline."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Protocol

from src.data import full_document_text
from src.external.openrouter import Completion
from src.prompt import build_messages, build_system_prompt
from src.schema import ABSENCE_ITEMS, EVIDENCE_MAX_CHARS, ITEMS, judgment_schema

JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class CompletionClient(Protocol):
    def complete(
        self,
        messages: list[dict[str, str]],
        response_schema: dict[str, Any],
    ) -> Completion: ...


class PredictionError(RuntimeError):
    """Raised when a model response cannot become a complete judgment."""

    def __init__(self, message: str, raw_response: str | None = None) -> None:
        super().__init__(message)
        self.raw_response = raw_response


@dataclass(frozen=True)
class Prediction:
    record_id: str
    judgment: dict[str, dict[str, Any]]
    raw_response: str
    model: str
    latency_seconds: float
    usage: dict[str, Any]
    finish_reason: str | None = None


def extract_json(text: str) -> Any:
    candidates = [text.strip(), *(match.group(1) for match in JSON_FENCE.finditer(text))]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    raise PredictionError("model response is not valid JSON")


def parse_judgment(text: str) -> dict[str, dict[str, Any]]:
    payload = extract_json(text)
    if isinstance(payload, dict) and isinstance(payload.get("판정"), dict):
        payload = payload["판정"]
    if not isinstance(payload, dict):
        raise PredictionError("model response must be a JSON object")
    missing = [item for item in ITEMS if item not in payload]
    if missing:
        raise PredictionError(f"model response missing items: {missing}")
    judgment: dict[str, dict[str, Any]] = {}
    for item in ITEMS:
        cell = payload[item]
        if not isinstance(cell, dict):
            raise PredictionError(f"{item} must be an object")
        violation = cell.get("위반여부")
        if isinstance(violation, bool):
            violation = int(violation)
        if violation not in (0, 1):
            raise PredictionError(f"{item}.위반여부 must be 0 or 1")
        evidence = cell.get("근거문구")
        if evidence is not None and not isinstance(evidence, str):
            raise PredictionError(f"{item}.근거문구 must be a string or null")
        judgment[item] = {"위반여부": int(violation), "근거문구": evidence}
    return judgment


def _collapse_whitespace_with_spans(text: str) -> tuple[str, list[tuple[int, int]]]:
    collapsed: list[str] = []
    spans: list[tuple[int, int]] = []
    index = 0
    while index < len(text):
        if text[index].isspace():
            end = index + 1
            while end < len(text) and text[end].isspace():
                end += 1
            collapsed.append(" ")
            spans.append((index, end))
            index = end
        else:
            collapsed.append(text[index])
            spans.append((index, index + 1))
            index += 1
    return "".join(collapsed), spans


def _resolve_whitespace_variant(candidate: str, source: str) -> str:
    normalized_candidate = " ".join(candidate.split())
    normalized_source, spans = _collapse_whitespace_with_spans(source)
    start = normalized_source.find(normalized_candidate)
    if start < 0:
        return ""
    end = start + len(normalized_candidate)
    return source[spans[start][0] : spans[end - 1][1]].strip()


def _clean_evidence(value: str | None, source: str) -> str:
    if not value:
        return ""
    evidence = unicodedata.normalize("NFC", value).replace("\r", "").strip()
    if not evidence or evidence.startswith(("=", "+", "@")):
        return ""
    if evidence in source:
        resolved = evidence
    else:
        resolved = _resolve_whitespace_variant(evidence, source)
    return resolved[:EVIDENCE_MAX_CHARS] if resolved else ""


def postprocess_judgment(
    judgment: dict[str, dict[str, Any]],
    record: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    source = unicodedata.normalize("NFC", full_document_text(record))
    result: dict[str, dict[str, Any]] = {}
    for item in ITEMS:
        violation = judgment[item]["위반여부"]
        evidence = ""
        if violation == 1 and item not in ABSENCE_ITEMS:
            evidence = _clean_evidence(judgment[item]["근거문구"], source)
        result[item] = {"위반여부": violation, "근거문구": evidence}
    return result


def judgment_to_row(record_id: str, judgment: dict[str, dict[str, Any]]) -> dict[str, Any]:
    row: dict[str, Any] = {"id": record_id}
    for index, item in enumerate(ITEMS, 1):
        row[item] = judgment[item]["위반여부"]
        row[f"e{index}"] = judgment[item]["근거문구"]
    return row


class BaselinePipeline:
    def __init__(
        self,
        *,
        item_table: dict[str, dict[str, Any]],
        client: CompletionClient,
        max_document_chars: int | None,
        prompt_mode: str = "baseline",
        include_normalized_facts: bool = False,
    ) -> None:
        self.client = client
        self.max_document_chars = max_document_chars
        self.include_normalized_facts = include_normalized_facts
        self.system_prompt = build_system_prompt(item_table, mode=prompt_mode)
        self.response_schema = judgment_schema()

    def predict(self, record: dict[str, Any]) -> Prediction:
        messages = build_messages(
            record,
            self.system_prompt,
            self.max_document_chars,
            include_normalized_facts=self.include_normalized_facts,
        )
        completion = self.client.complete(messages, self.response_schema)
        try:
            parsed = parse_judgment(completion.content)
        except PredictionError as exc:
            raise PredictionError(str(exc), raw_response=completion.content) from exc
        judgment = postprocess_judgment(parsed, record)
        return Prediction(
            record_id=record["id"],
            judgment=judgment,
            raw_response=completion.content,
            model=completion.model,
            latency_seconds=completion.latency_seconds,
            usage=completion.usage,
            finish_reason=completion.finish_reason,
        )
