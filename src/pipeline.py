"""Shared notice-to-judgment baseline pipeline."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Protocol

from src.data import competition_product_fact, full_document_text
from src.context_budget import (
    DocumentContext,
    TokenCounter,
    pack_contexts_to_token_budget,
    pack_document_contexts_to_token_budget,
)
from src.prompt import (
    build_messages,
    build_split_document_contexts,
    build_system_prompt,
    format_competition_product_context,
)
from src.schema import ABSENCE_ITEMS, EVIDENCE_MAX_CHARS, ITEMS, judgment_schema

JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class CompletionClient(Protocol):
    def complete(
        self,
        messages: list[dict[str, str]],
        response_schema: dict[str, Any],
    ) -> Any: ...


class PredictionError(RuntimeError):
    """Raised when a model response cannot become a complete judgment."""

    def __init__(self, message: str, raw_response: str | None = None) -> None:
        super().__init__(message)
        self.raw_response = raw_response


def zero_judgment() -> dict[str, dict[str, Any]]:
    """Return a submission-safe judgment for a single unusable model pass."""
    return {
        item: {"위반여부": 0, "근거문구": None}
        for item in ITEMS
    }


@dataclass(frozen=True)
class Prediction:
    record_id: str
    judgment: dict[str, dict[str, Any]]
    raw_response: str
    model: str
    latency_seconds: float
    usage: dict[str, Any]
    finish_reason: str | None = None
    pass_judgments: tuple[dict[str, dict[str, Any]], ...] = ()
    parse_errors: tuple[dict[str, Any], ...] = ()


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
    source_text: str | None = None,
    require_evidence_for_positive: bool = False,
) -> dict[str, dict[str, Any]]:
    source = unicodedata.normalize("NFC", source_text or full_document_text(record))
    result: dict[str, dict[str, Any]] = {}
    for item in ITEMS:
        violation = judgment[item]["위반여부"]
        evidence = ""
        if violation == 1 and item not in ABSENCE_ITEMS:
            evidence = _clean_evidence(judgment[item]["근거문구"], source)
            if require_evidence_for_positive and not evidence:
                violation = 0
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
        context_strategy: str = "single",
        notice_anchor_chars: int = 4000,
        overflow_split_enabled: bool = True,
        count_tokens: TokenCounter | None = None,
        prompt_budget_tokens: int = 30268,
        reference_text: str | None = None,
        strict_document_evidence: bool = False,
        absence_detection_strategy: str = "per_pass_or",
        decision_cards: dict[str, dict[str, Any]] | None = None,
        competition_products: dict[str, dict[str, str]] | None = None,
    ) -> None:
        self.client = client
        self.max_document_chars = max_document_chars
        self.include_normalized_facts = include_normalized_facts
        self.context_strategy = context_strategy
        self.notice_anchor_chars = notice_anchor_chars
        self.overflow_split_enabled = overflow_split_enabled
        self.count_tokens = count_tokens
        self.prompt_budget_tokens = prompt_budget_tokens
        self.strict_document_evidence = strict_document_evidence
        self.absence_detection_strategy = absence_detection_strategy
        self.competition_products = competition_products
        self.system_prompt = build_system_prompt(
            item_table,
            mode=prompt_mode,
            reference_text=reference_text,
            document_scoped=strict_document_evidence,
            decision_cards=decision_cards,
        )
        self.response_schema = judgment_schema()

    def predict(self, record: dict[str, Any]) -> Prediction:
        contexts = self.contexts_for_record(record)
        completions: list[Any] = []
        for context in contexts:
            completion = self.client.complete(
                self.messages_for_context(record, context), self.response_schema
            )
            completions.append(completion)
        return self.finalize(record, completions, contexts)

    def contexts_for_record(
        self, record: dict[str, Any]
    ) -> list[str | DocumentContext | None]:
        if self.context_strategy == "full_split_merge":
            if self.count_tokens is None:
                raise ValueError("full_split_merge requires an exact tokenizer token counter")
            contexts = pack_document_contexts_to_token_budget(
                record,
                self.system_prompt,
                self.count_tokens,
                self.prompt_budget_tokens,
                self.notice_anchor_chars,
            )
            return contexts
        forced_contexts: list[str | None] = (
            build_split_document_contexts(
                record, self.max_document_chars or 0, self.notice_anchor_chars
            )
            if self.context_strategy == "split"
            else [None]
        )
        if self.context_strategy == "split":
            return forced_contexts
        elif (
            self.overflow_split_enabled
            and self.max_document_chars is None
            and self.count_tokens is not None
        ):
            return pack_contexts_to_token_budget(
                record,
                self.system_prompt,
                self.count_tokens,
                self.prompt_budget_tokens,
                self.notice_anchor_chars,
            )
        return forced_contexts

    def messages_for_context(
        self, record: dict[str, Any], context: str | DocumentContext | None
    ) -> list[dict[str, str]]:
        return build_messages(
            record, self.system_prompt, self.max_document_chars,
            include_normalized_facts=self.include_normalized_facts,
            document_context=context.text if isinstance(context, DocumentContext) else context,
            competition_product_context=(
                format_competition_product_context(
                    record, competition_product_fact(record, self.competition_products)
                )
                if self.competition_products is not None
                else None
            ),
        )

    def finalize(
        self,
        record: dict[str, Any],
        completions: list[Any],
        contexts: list[str | DocumentContext | None] | None = None,
    ) -> Prediction:
        if contexts is not None and len(contexts) != len(completions):
            raise ValueError("contexts and completions must have the same length")
        judgments: list[dict[str, dict[str, Any]]] = []
        parse_errors: list[dict[str, Any]] = []
        for pass_index, completion in enumerate(completions, 1):
            try:
                parsed = parse_judgment(completion.content)
            except PredictionError as exc:
                # Structured decoding is the normal path, but vLLM can still return
                # an empty/incomplete candidate. Never discard every completed notice
                # because one pass is unusable; it is equivalent to an all-negative
                # pass and is recorded for reproducibility.
                parsed = zero_judgment()
                parse_errors.append(
                    {
                        "pass_index": pass_index,
                        "error": str(exc),
                        "raw_response": completion.content,
                    }
                )
            context = contexts[pass_index - 1] if contexts is not None else None
            if self.strict_document_evidence and not isinstance(context, DocumentContext):
                raise ValueError("strict_document_evidence requires full_split_merge document contexts")
            processed = postprocess_judgment(
                    parsed,
                    record,
                    source_text=context.target_text if isinstance(context, DocumentContext) else None,
                    require_evidence_for_positive=self.strict_document_evidence,
                )
            judgments.append(processed)
        judgment = _combine_pass_judgments(judgments, self.absence_detection_strategy)
        completion = completions[0]
        return Prediction(
            record_id=record["id"],
            judgment=judgment,
            raw_response=completion.content,
            model=completion.model,
            latency_seconds=sum(value.latency_seconds for value in completions),
            usage=_combined_usage(completions),
            finish_reason=completion.finish_reason,
            pass_judgments=tuple(judgments),
            parse_errors=tuple(parse_errors),
        )


def _combined_usage(completions: list[Any]) -> dict[str, Any]:
    keys = {key for completion in completions for key in completion.usage}
    return {
        key: sum(_usage_number(completion.usage.get(key, 0)) for completion in completions)
        for key in keys
    }


def _usage_number(value: Any) -> float:
    """Normalize OpenRouter usage values, including nested cost objects."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, dict):
        for key in ("cost", "total_cost", "total"):
            nested = value.get(key)
            if isinstance(nested, (int, float)) and not isinstance(nested, bool):
                return float(nested)
    return 0.0


def _combine_pass_judgments(
    judgments: list[dict[str, dict[str, Any]]],
    absence_detection_strategy: str = "per_pass_or",
) -> dict[str, dict[str, Any]]:
    """OR pass decisions, retaining the earliest valid positive evidence.

    Fixed document ordering means the first positive is the memo's ``11`` case:
    a finding visible in both passes is attributed to the earlier pass. ``01``
    and ``10`` retain their sole positive pass; only ``00`` becomes negative.
    """
    if not judgments:
        raise ValueError("at least one pass judgment is required")
    combined: dict[str, dict[str, Any]] = {}
    for item in ITEMS:
        if item in ABSENCE_ITEMS and absence_detection_strategy == "per_pass_and":
            combined[item] = {
                "위반여부": int(all(judgment[item]["위반여부"] == 1 for judgment in judgments)),
                "근거문구": "",
            }
            continue
        positives = [judgment[item] for judgment in judgments if judgment[item]["위반여부"] == 1]
        if not positives:
            combined[item] = {"위반여부": 0, "근거문구": ""}
            continue
        selected = positives[0]
        combined[item] = {"위반여부": 1, "근거문구": selected["근거문구"]}
    return combined
