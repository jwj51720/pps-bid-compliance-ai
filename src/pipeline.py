"""Shared notice-to-judgment baseline pipeline."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Protocol

from src.data import competition_product_fact, full_document_text
from src.law_bundles import MetadataLawBundleRouter
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
    format_v24_comparison_context,
)
from src.schema import (
    ABSENCE_ITEMS,
    EVIDENCE_MAX_CHARS,
    ITEMS,
    V8_COMPOSITE_STATES,
    judgment_schema,
)

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


def zero_judgment(items: tuple[str, ...] = ITEMS) -> dict[str, dict[str, Any]]:
    """Return a submission-safe judgment for a single unusable model pass."""
    return {
        item: {"위반여부": 0, "근거문구": None}
        for item in items
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
    v8_observations: tuple[dict[str, Any], ...] = ()
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


def _parse_judgment_payload(
    payload: Any, items: tuple[str, ...] = ITEMS
) -> dict[str, dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("판정"), dict):
        payload = payload["판정"]
    if not isinstance(payload, dict):
        raise PredictionError("model response must be a JSON object")
    missing = [item for item in items if item not in payload]
    if missing:
        raise PredictionError(f"model response missing items: {missing}")
    judgment: dict[str, dict[str, Any]] = {}
    for item in items:
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


def _parse_labels_payload(
    payload: Any, items: tuple[str, ...] = ITEMS
) -> dict[str, dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("판정"), dict):
        payload = payload["판정"]
    if not isinstance(payload, dict):
        raise PredictionError("model response must be a JSON object")
    missing = [item for item in items if item not in payload]
    if missing:
        raise PredictionError(f"model response missing items: {missing}")
    judgment: dict[str, dict[str, Any]] = {}
    for item in items:
        violation = payload[item]
        if isinstance(violation, bool):
            violation = int(violation)
        if violation not in (0, 1):
            raise PredictionError(f"{item} must be 0 or 1")
        judgment[item] = {"위반여부": int(violation), "근거문구": None}
    return judgment


def _parse_anchor_payload(payload: Any, items: tuple[str, ...] = ITEMS) -> dict[str, dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("판정"), dict):
        payload = payload["판정"]
    if not isinstance(payload, dict):
        raise PredictionError("model response must be a JSON object")
    missing = [item for item in items if item not in payload]
    if missing:
        raise PredictionError(f"model response missing items: {missing}")
    judgment: dict[str, dict[str, Any]] = {}
    for item in items:
        cell = payload[item]
        if not isinstance(cell, dict):
            raise PredictionError(f"{item} must be an object")
        violation = cell.get("위반여부")
        if isinstance(violation, bool):
            violation = int(violation)
        if violation not in (0, 1):
            raise PredictionError(f"{item}.위반여부 must be 0 or 1")
        anchor = cell.get("판단어구")
        if anchor is not None and not isinstance(anchor, str):
            raise PredictionError(f"{item}.판단어구 must be a string or null")
        if item in ABSENCE_ITEMS and anchor is not None:
            raise PredictionError(f"{item}.판단어구 must be null")
        judgment[item] = {"위반여부": int(violation), "근거문구": anchor}
    return judgment


def _parse_sparse_anchor_payload(payload: Any, items: tuple[str, ...] = ITEMS) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, dict):
        raise PredictionError("model response must be a JSON object")
    excerpts = payload.get("발췌")
    reviews = payload.get("부재검토")
    if not isinstance(excerpts, list) or not isinstance(reviews, dict):
        raise PredictionError("발췌 and 부재검토 are required")
    judgment = _parse_labels_payload(payload, items)
    seen: set[str] = set()
    for entry in excerpts:
        if not isinstance(entry, dict) or entry.get("항목") not in items or entry["항목"] in ABSENCE_ITEMS or not isinstance(entry.get("근거문구"), str) or entry["항목"] in seen:
            raise PredictionError("invalid sparse 발췌")
        seen.add(entry["항목"])
        judgment[entry["항목"]]["근거문구"] = entry["근거문구"]
    # 부재검토 is intentionally parsed/required by the schema but does not
    # alter a model's final label.  That would make this an algorithm change,
    # not an output-serialization experiment.
    for item in items:
        if item in ABSENCE_ITEMS and reviews.get(item) not in {"필수조건_확인", "미확인", "비적용_또는_불명"}:
            raise PredictionError("invalid sparse 부재검토")
    return judgment


def parse_judgment(
    text: str, items: tuple[str, ...] = ITEMS, output_mode: str = "labels_and_evidence"
) -> dict[str, dict[str, Any]]:
    payload = extract_json(text)
    if output_mode == "labels_only":
        return _parse_labels_payload(payload, items)
    if output_mode == "labels_and_anchor":
        return _parse_anchor_payload(payload, items)
    if output_mode == "labels_and_sparse_evidence":
        return _parse_sparse_anchor_payload(payload, items)
    return _parse_judgment_payload(payload, items)


def parse_pass_response(
    text: str, v8_composite_enabled: bool, items: tuple[str, ...] = ITEMS,
    output_mode: str = "labels_and_evidence",
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    payload = extract_json(text)
    judgment = _parse_labels_payload(payload, items) if output_mode == "labels_only" else _parse_anchor_payload(payload, items) if output_mode == "labels_and_anchor" else _parse_sparse_anchor_payload(payload, items) if output_mode == "labels_and_sparse_evidence" else _parse_judgment_payload(payload, items)
    if not v8_composite_enabled or "v8" not in items:
        return judgment, {}
    observation = payload.get("v8병합관찰") if isinstance(payload, dict) else None
    if not isinstance(observation, dict) or observation.get("상태") not in V8_COMPOSITE_STATES:
        raise PredictionError("invalid v8병합관찰 state")
    evidence = observation.get("관찰근거문구")
    if evidence is not None and not isinstance(evidence, str):
        raise PredictionError("v8병합관찰.관찰근거문구 must be a string or null")
    return judgment, {"상태": observation["상태"], "관찰근거문구": evidence}


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
    items: tuple[str, ...] = ITEMS,
    output_mode: str = "labels_and_evidence",
) -> dict[str, dict[str, Any]]:
    if output_mode == "labels_only":
        return {
            item: {"위반여부": judgment[item]["위반여부"], "근거문구": ""}
            for item in items
        }
    source = unicodedata.normalize("NFC", source_text or full_document_text(record))
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        violation = judgment[item]["위반여부"]
        evidence = ""
        if violation == 1 and item not in ABSENCE_ITEMS:
            evidence = _clean_evidence(judgment[item]["근거문구"], source)
            if require_evidence_for_positive and not evidence:
                violation = 0
        if output_mode == "labels_and_anchor":
            evidence = ""
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
        reference_navigation: str | None = None,
        law_bundle_router: MetadataLawBundleRouter | None = None,
        strict_document_evidence: bool = False,
        absence_detection_strategy: str = "per_pass_or",
        decision_cards: dict[str, dict[str, Any]] | None = None,
        competition_products: dict[str, dict[str, str]] | None = None,
        v8_composite_merge_enabled: bool = False,
        v8_composite_merge_mode: str = "fallback_or",
        candidate_detection: bool = False,
        active_items: tuple[str, ...] = ITEMS,
        prompt_layout: str = "plain",
        output_mode: str = "labels_and_evidence",
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
        self.law_bundle_router = law_bundle_router
        self.v8_composite_merge_enabled = v8_composite_merge_enabled
        self.v8_composite_merge_mode = v8_composite_merge_mode
        self.prompt_layout = prompt_layout
        if output_mode not in {"labels_and_evidence", "labels_only", "labels_and_anchor", "labels_and_sparse_evidence"}:
            raise ValueError("output_mode must be labels_and_evidence, labels_only, or labels_and_anchor")
        if output_mode == "labels_only" and strict_document_evidence:
            raise ValueError("labels_only cannot use strict_document_evidence")
        if output_mode == "labels_only" and v8_composite_merge_enabled:
            raise ValueError("labels_only cannot use v8_composite_merge")
        if output_mode in {"labels_and_anchor", "labels_and_sparse_evidence"} and not strict_document_evidence:
            raise ValueError("labels_and_anchor requires strict_document_evidence")
        self.output_mode = output_mode
        self.prompt_output_mode = output_mode
        if not active_items or any(item not in ITEMS for item in active_items):
            raise ValueError("active_items must be a non-empty subset of v1..v24")
        if len(active_items) != len(set(active_items)):
            raise ValueError("active_items must not contain duplicates")
        self.active_items = active_items
        if self.v8_composite_merge_enabled and "v8" not in active_items:
            self.v8_composite_merge_enabled = False
        if self.v8_composite_merge_mode not in {"fallback_or", "strict_conjunction"}:
            raise ValueError("v8_composite_merge_mode must be fallback_or or strict_conjunction")
        self.system_prompt = build_system_prompt(
            item_table,
            mode=prompt_mode,
            reference_text=reference_text,
            reference_navigation=reference_navigation,
            document_scoped=(strict_document_evidence or output_mode == "labels_only"),
            decision_cards=decision_cards,
            v8_composite_enabled=v8_composite_merge_enabled,
            candidate_detection=candidate_detection,
            active_items=active_items,
            layout=prompt_layout,
            output_mode=self.output_mode,
        )
        self._prompt_options = {
            "item_table": item_table,
            "mode": prompt_mode,
            "document_scoped": (strict_document_evidence or output_mode == "labels_only"),
            "decision_cards": decision_cards,
            "v8_composite_enabled": v8_composite_merge_enabled,
            "candidate_detection": candidate_detection,
            "active_items": active_items,
            "layout": prompt_layout,
            "output_mode": self.output_mode,
        }
        self._routed_system_prompts: dict[str, str] = {}
        self.response_schema = judgment_schema(
            self.v8_composite_merge_enabled, active_items, output_mode
        )

    def system_prompt_for_record(self, record: dict[str, Any]) -> str:
        if self.law_bundle_router is None:
            return self.system_prompt
        route = self.law_bundle_router.route(record)
        if route.profile not in self._routed_system_prompts:
            self._routed_system_prompts[route.profile] = build_system_prompt(
                **self._prompt_options,
                reference_text=route.reference_text,
                reference_navigation=self.law_bundle_router.navigation_text(record),
            )
        return self._routed_system_prompts[route.profile]

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
        competition_context = self.competition_product_context_for_record(record)
        system_prompt = self.system_prompt_for_record(record)
        if self.context_strategy == "full_split_merge":
            if self.count_tokens is None:
                raise ValueError("full_split_merge requires an exact tokenizer token counter")
            contexts = pack_document_contexts_to_token_budget(
                record,
                system_prompt,
                self.count_tokens,
                self.prompt_budget_tokens,
                self.notice_anchor_chars,
                competition_product_context=competition_context,
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
                system_prompt,
                self.count_tokens,
                self.prompt_budget_tokens,
                self.notice_anchor_chars,
                competition_product_context=competition_context,
            )
        return forced_contexts

    def messages_for_context(
        self, record: dict[str, Any], context: str | DocumentContext | None
    ) -> list[dict[str, str]]:
        return build_messages(
            record, self.system_prompt_for_record(record), self.max_document_chars,
            include_normalized_facts=self.include_normalized_facts,
            document_context=context.text if isinstance(context, DocumentContext) else context,
            competition_product_context=self.competition_product_context_for_record(record),
            v24_comparison_context=(format_v24_comparison_context(record) if "v24" in self.active_items else None),
            markdown_sections=self.prompt_layout in {"markdown", "markdown_v2"},
            output_mode=self.prompt_output_mode,
        )

    def competition_product_context_for_record(self, record: dict[str, Any]) -> str | None:
        if self.competition_products is None:
            return None
        product_items = {"v10", "v11", "v13", "v16", "v18"}
        if not product_items.intersection(self.active_items):
            return None
        return format_competition_product_context(
            record, competition_product_fact(record, self.competition_products), self.active_items
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
        v8_observations: list[dict[str, Any]] = []
        parse_errors: list[dict[str, Any]] = []
        for pass_index, completion in enumerate(completions, 1):
            try:
                parsed, raw_observations = parse_pass_response(
                    completion.content, self.v8_composite_merge_enabled, self.active_items,
                    self.output_mode,
                )
            except PredictionError as exc:
                # Structured decoding is the normal path, but vLLM can still return
                # an empty/incomplete candidate. Never discard every completed notice
                # because one pass is unusable; it is equivalent to an all-negative
                # pass and is recorded for reproducibility.
                parsed = zero_judgment(self.active_items)
                raw_observations = {}
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
                    items=self.active_items,
                    output_mode=self.output_mode,
                )
            judgments.append(processed)
            if self.v8_composite_merge_enabled:
                v8_observations.append(
                    _validate_v8_observation(
                        raw_observations,
                        context.target_text if isinstance(context, DocumentContext) else "",
                        context,
                    )
                )
        merged_active = _merge_notice_judgments(
            record,
            judgments,
            v8_observations,
            self.absence_detection_strategy,
            self.v8_composite_merge_enabled,
            self.v8_composite_merge_mode,
            self.active_items,
        )
        # A group pass is still serializable as the competition's complete 24-item
        # row.  Its inactive items are placeholders and are never treated as a
        # group decision by the grouped orchestrator.
        judgment = zero_judgment()
        judgment.update(merged_active)
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
            v8_observations=tuple(v8_observations),
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
    items: tuple[str, ...] = ITEMS,
) -> dict[str, dict[str, Any]]:
    """OR pass decisions, retaining the earliest valid positive evidence.

    Fixed document ordering means the first positive is the memo's ``11`` case:
    a finding visible in both passes is attributed to the earlier pass. ``01``
    and ``10`` retain their sole positive pass; only ``00`` becomes negative.
    """
    if not judgments:
        raise ValueError("at least one pass judgment is required")
    combined: dict[str, dict[str, Any]] = {}
    for item in items:
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


def _v8_observation_default() -> dict[str, str]:
    return {"상태": "검토", "관찰근거문구": ""}


def _validate_v8_observation(
    observation: dict[str, Any], source_text: str, context: Any
) -> dict[str, Any]:
    """Keep only v8 document-local observation evidence; never interpret its meaning."""
    result: dict[str, Any] = {
        "doc_id": context.target_document_id if isinstance(context, DocumentContext) else None,
        "document_type": context.target_document_type if isinstance(context, DocumentContext) else None,
    }
    value = observation or _v8_observation_default()
    evidence = _clean_evidence(value.get("관찰근거문구"), source_text)
    state = value.get("상태", "검토")
    if state in {"실적", "지역", "둘다"} and not evidence:
        state = "검토"
    result.update({"상태": state, "관찰근거문구": evidence})
    return result


def _merge_notice_judgments(
    record: dict[str, Any],
    judgments: list[dict[str, dict[str, Any]]],
    v8_observations: list[dict[str, Any]],
    absence_detection_strategy: str,
    v8_composite_merge_enabled: bool,
    v8_composite_merge_mode: str = "fallback_or",
    items: tuple[str, ...] = ITEMS,
) -> dict[str, dict[str, Any]]:
    combined = _combine_pass_judgments(judgments, absence_detection_strategy, items)
    if not v8_composite_merge_enabled:
        return combined

    # v8 exception: two independent source-document observations can form its one conjunction.
    def observed(state: str) -> dict[str, Any] | None:
        for value in v8_observations:
            if value["상태"] == state and value["관찰근거문구"]:
                return {"위반여부": 1, "근거문구": value["관찰근거문구"]}
        return None

    conjunction = observed("둘다") or (
        observed("실적") if observed("실적") and observed("지역") else None
    )
    combined["v8"] = conjunction or (
        combined["v8"] if v8_composite_merge_mode == "fallback_or"
        else {"위반여부": 0, "근거문구": ""}
    )
    return combined
