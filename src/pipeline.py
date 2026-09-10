"""Shared notice-to-judgment baseline pipeline."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, replace
from typing import Any, Protocol

from src.applicability import safe_inactive_items
from src.data import competition_product_fact, full_document_text
from src.frozen_rules import apply_exp123_frozen_rules
from src.law_bundles import MetadataLawBundleRouter
from src.context_budget import (
    DocumentContext,
    TokenCounter,
    pack_contexts_to_token_budget,
    pack_document_contexts_to_token_budget,
)
from src.prompt import (
    append_untrusted_review_draft,
    append_locator_navigation,
    append_fact_inventory,
    append_source_inventory,
    build_messages,
    build_official_baseline_context,
    build_locator_system_prompt,
    build_inventory_system_prompt,
    build_fact_inventory_system_prompt,
    build_split_document_contexts,
    build_system_prompt,
    build_triage_system_prompt,
    format_competition_product_context,
    format_v24_comparison_context,
)
from src.schema import (
    ABSENCE_ITEMS,
    EVIDENCE_MAX_CHARS,
    FACT_INVENTORY_CATEGORIES,
    FACT_INVENTORY_CATEGORIES_V2,
    ITEMS,
    V8_COMPOSITE_STATES,
    judgment_schema,
    TRIAGE_STATES,
    locator_schema,
    inventory_schema,
    fact_inventory_schema,
    triage_schema,
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


class ContextAdmissionError(RuntimeError):
    """A diagnostic full-context request cannot fit the exact token budget."""


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
    applicability_inactive_items: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class TwoPassAdjudicationPrediction:
    """Auditable result of one draft pass and one final review pass."""

    pass_a: Prediction
    pass_b: Prediction
    final: Prediction
    final_source: str


@dataclass(frozen=True)
class TriageThenStrictPrediction:
    """B architecture: non-final routing followed by a strict subset pass.

    Triage states are diagnostic routing signals only.  The strict pass owns
    every non-frozen final label/evidence; absence items and malformed triage
    are always routed, so no stage-1 state can silently become an absence 0.
    """

    triage_raw_response: str
    triage_latency_seconds: float
    triage_usage: dict[str, Any]
    triage_finish_reason: str | None
    triage_states: dict[str, str]
    strict_items: tuple[str, ...]
    strict: Prediction
    final: Prediction
    triage_parse_error: str | None
    strict_recovery_used: bool
    triage_messages: tuple[dict[str, str], ...]
    strict_messages: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class LocatorThenFinalPrediction:
    """C architecture: non-final source locator followed by all-item V/E."""

    locator_raw_response: str
    locator_snippets: dict[str, str]
    locator_latency_seconds: float
    locator_usage: dict[str, Any]
    locator_finish_reason: str | None
    locator_parse_error: str | None
    final: Prediction
    final_recovery_used: bool
    locator_messages: tuple[dict[str, str], ...]
    final_messages: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class InventoryThenFinalPrediction:
    """F architecture: complete-source facts followed by a final V/E call."""

    inventory_raw_responses: tuple[str, ...]
    inventory_by_item: dict[str, tuple[tuple[str, str], ...]]
    absence_pack_summary: dict[str, str]
    inventory_usage: tuple[dict[str, Any], ...]
    inventory_latency_seconds: tuple[float, ...]
    inventory_parse_errors: tuple[str, ...]
    inventory_messages: tuple[tuple[dict[str, str], ...], ...]
    final: Prediction
    final_messages: tuple[dict[str, str], ...]
    final_recovery_used: bool


@dataclass(frozen=True)
class FactInventoryThenFinalPrediction:
    """Source-category excerpts followed by one independent final V/E task."""

    inventory_raw_responses: tuple[str, ...]
    inventory_by_category: dict[str, tuple[tuple[str, str], ...]]
    inventory_usage: tuple[dict[str, Any], ...]
    inventory_latency_seconds: tuple[float, ...]
    inventory_parse_errors: tuple[str, ...]
    inventory_messages: tuple[tuple[dict[str, str], ...], ...]
    final: Prediction
    final_messages: tuple[dict[str, str], ...]
    final_recovery_used: bool


@dataclass(frozen=True)
class FactInventoryFullFinalPrediction:
    """Source fact navigation followed by a source-complete final V/E task."""

    inventory_raw_responses: tuple[str, ...]
    inventory_by_category: dict[str, tuple[tuple[str, str], ...]]
    inventory_usage: tuple[dict[str, Any], ...]
    inventory_latency_seconds: tuple[float, ...]
    inventory_parse_errors: tuple[str, ...]
    inventory_messages: tuple[tuple[dict[str, str], ...], ...]
    inventory_max_items: int
    inventory_position: str
    inventory_categories: tuple[str, ...]
    final: Prediction
    final_messages_by_context: tuple[tuple[dict[str, str], ...], ...]
    final_recovery_used: bool


def extract_json(text: str) -> Any:
    candidates = [text.strip(), *(match.group(1) for match in JSON_FENCE.finditer(text))]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            repaired = _close_complete_json_object(candidate)
            if repaired is not None:
                try:
                    return json.loads(repaired)
                except json.JSONDecodeError:
                    pass
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    raise PredictionError("model response is not valid JSON")


def _close_complete_json_object(candidate: str) -> str | None:
    """Repair only a missing outer-object closure after otherwise valid JSON.

    Some constrained Gemma responses emit every requested field, close the
    final field object, then fill the remaining generation budget with
    whitespace without writing the one final root ``}``.  This function never
    edits a token, inserts a comma, or recovers a partial value: it appends
    closing braces only when a JSON-aware scan finds unmatched opening braces
    and the last non-whitespace token already closes an object or array.
    ``json.loads`` remains the final authority.
    """
    stripped = candidate.strip()
    if not stripped.startswith("{") or not stripped.endswith(("}", "]")):
        return None
    depth = 0
    in_string = False
    escaped = False
    for char in stripped:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                return None
    if in_string or depth <= 0:
        return None
    return stripped + ("}" * depth)


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


def parse_triage_response(text: str, items: tuple[str, ...] = ITEMS) -> dict[str, str]:
    """Parse a complete, closed route-state payload; never infer a route."""
    payload = extract_json(text)
    if not isinstance(payload, dict):
        raise PredictionError("triage response must be a JSON object")
    missing = [item for item in items if item not in payload]
    unexpected = sorted(set(payload) - set(items))
    if missing or unexpected:
        raise PredictionError(
            f"triage response keys mismatch: missing={missing}, unexpected={unexpected}"
        )
    states: dict[str, str] = {}
    for item in items:
        state = payload[item]
        if state not in TRIAGE_STATES:
            raise PredictionError(f"{item} has invalid triage state")
        states[item] = state
    return states


def parse_locator_response(text: str, items: tuple[str, ...]) -> dict[str, str | None]:
    """Parse locator excerpts; this parser intentionally has no label field."""
    payload = extract_json(text)
    if not isinstance(payload, dict):
        raise PredictionError("locator response must be a JSON object")
    missing = [item for item in items if item not in payload]
    unexpected = sorted(set(payload) - set(items))
    if missing or unexpected:
        raise PredictionError(
            f"locator response keys mismatch: missing={missing}, unexpected={unexpected}"
        )
    result: dict[str, str | None] = {}
    for item in items:
        value = payload[item]
        if value is not None and not isinstance(value, str):
            raise PredictionError(f"{item} locator value must be a string or null")
        result[item] = value
    return result


def parse_inventory_response(text: str, items: tuple[str, ...]) -> dict[str, str | None]:
    """Inventory uses the same primitive payload but includes absence items."""
    payload = extract_json(text)
    if not isinstance(payload, dict):
        raise PredictionError("inventory response must be a JSON object")
    if set(payload) != set(items):
        raise PredictionError("inventory response keys do not match active items")
    result: dict[str, str | None] = {}
    for item in items:
        value = payload[item]
        if value is not None and not isinstance(value, str):
            raise PredictionError(f"{item} inventory value must be a string or null")
        result[item] = value
    return result


def parse_fact_inventory_response(
    text: str,
    max_items: int = 3,
    categories: tuple[str, ...] = FACT_INVENTORY_CATEGORIES,
) -> dict[str, list[str]]:
    """Parse category excerpts without assigning any v label semantics."""
    if max_items not in {3, 4}:
        raise ValueError("fact inventory max_items must be 3 or 4")
    if categories not in {FACT_INVENTORY_CATEGORIES, FACT_INVENTORY_CATEGORIES_V2}:
        raise ValueError("fact inventory categories must be a supported version")
    payload = extract_json(text)
    if not isinstance(payload, dict) or set(payload) != set(categories):
        raise PredictionError("fact inventory response keys do not match factual categories")
    result: dict[str, list[str]] = {}
    for category in categories:
        values = payload[category]
        if not isinstance(values, list) or len(values) > max_items or not all(isinstance(value, str) for value in values):
            raise PredictionError(
                f"{category} fact inventory value must be up to {max_items} strings"
            )
        result[category] = values
    return result


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
        prompt_profile: str = "default",
        role_directive: str = "standard",
        item_catalog_style: str = "minimal",
        metadata_style: str = "full_json",
        output_mode: str = "labels_and_evidence",
        visible_document_types: tuple[str, ...] | None = None,
        frozen_rule_set: str | None = None,
        locator_policy: str = "strict_v1",
        applicability_gate_mode: str = "off",
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
        self.prompt_profile = prompt_profile
        self.role_directive = role_directive
        self.item_catalog_style = item_catalog_style
        self.metadata_style = metadata_style
        self.visible_document_types = visible_document_types
        self._item_table = item_table
        self._prompt_mode = prompt_mode
        self._reference_text = reference_text
        self._reference_navigation = reference_navigation
        self._decision_cards = decision_cards
        self._candidate_detection = candidate_detection
        if locator_policy not in {"strict_v1", "broad_candidate_v1"}:
            raise ValueError("locator_policy must be strict_v1 or broad_candidate_v1")
        self.locator_policy = locator_policy
        if applicability_gate_mode not in {"off", "safe_v1"}:
            raise ValueError("applicability_gate_mode must be off or safe_v1")
        if applicability_gate_mode == "safe_v1" and competition_products is None:
            raise ValueError("safe_v1 applicability gate requires competition products")
        self.applicability_gate_mode = applicability_gate_mode
        if frozen_rule_set not in {None, "exp123_v1"}:
            raise ValueError("frozen_rule_set must be exp123_v1 or null")
        self.frozen_rule_set = frozen_rule_set
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
        self.task_profile = (
            "absence" if set(active_items) == set(ABSENCE_ITEMS)
            else "v24_consistency" if active_items == ("v24",)
            else "general"
        )
        if self.v8_composite_merge_enabled and "v8" not in active_items:
            self.v8_composite_merge_enabled = False
        v8_composite_enabled = self.v8_composite_merge_enabled
        if self.v8_composite_merge_mode not in {"fallback_or", "strict_conjunction"}:
            raise ValueError("v8_composite_merge_mode must be fallback_or or strict_conjunction")
        self.system_prompt = build_system_prompt(
            item_table,
            mode=prompt_mode,
            reference_text=reference_text,
            reference_navigation=reference_navigation,
            document_scoped=(strict_document_evidence or output_mode == "labels_only"),
            decision_cards=decision_cards,
            v8_composite_enabled=v8_composite_enabled,
            candidate_detection=candidate_detection,
            active_items=active_items,
            layout=prompt_layout,
            profile=prompt_profile,
            role_directive=role_directive,
            item_catalog_style=item_catalog_style,
            output_mode=self.output_mode,
        )
        self._prompt_options = {
            "item_table": item_table,
            "mode": prompt_mode,
            "document_scoped": (strict_document_evidence or output_mode == "labels_only"),
            "decision_cards": decision_cards,
            "v8_composite_enabled": v8_composite_enabled,
            "candidate_detection": candidate_detection,
            "active_items": active_items,
            "layout": prompt_layout,
            "profile": prompt_profile,
            "role_directive": role_directive,
            "item_catalog_style": item_catalog_style,
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
        effective, inactive = self.effective_pipeline_for_record(record)
        if effective is not self:
            prediction = effective.predict(record)
            judgment = prediction.judgment
            if self.frozen_rule_set == "exp123_v1":
                judgment = apply_exp123_frozen_rules(record, judgment)
            return replace(
                prediction,
                judgment=judgment,
                applicability_inactive_items=tuple(sorted(inactive.items())),
            )
        contexts = self.contexts_for_record(record)
        completions: list[Any] = []
        for context in contexts:
            completion = self.client.complete(
                self.messages_for_context(record, context), self.response_schema
            )
            completions.append(completion)
        return self.finalize(record, completions, contexts)

    def effective_pipeline_for_record(
        self, record: dict[str, Any]
    ) -> tuple["BaselinePipeline", dict[str, str]]:
        """Build a record-specific model subset only for explicit 0 preconditions."""
        if self.applicability_gate_mode == "off":
            return self, {}
        assert self.competition_products is not None
        inactive = safe_inactive_items(record, self.competition_products)
        active = tuple(item for item in self.active_items if item not in inactive)
        if not active:
            raise RuntimeError("safe applicability gate cannot suppress every item")
        return self._subset_pipeline(active, prompt_profile="complete_fact_subset_v1"), inactive

    def predict_with_untrusted_label_review(
        self, record: dict[str, Any]
    ) -> TwoPassAdjudicationPrediction:
        """Run one exact pass, then independently adjudicate its labels.

        The second message receives no first-pass evidence text and final labels
        come entirely from pass B. If B cannot be parsed, retaining A is only a
        transport recovery; it never merges individual labels.
        """
        contexts = self.contexts_for_record(record)
        if len(contexts) != 1:
            raise ValueError("two-pass adjudication requires exactly one notice context")
        pass_a = self.predict(record)
        pass_b_messages = append_untrusted_review_draft(
            self.messages_for_context(record, contexts[0]),
            pass_a.judgment,
            self.active_items,
        )
        completion = self.client.complete(pass_b_messages, self.response_schema)
        pass_b = self.finalize(record, [completion], contexts)
        if pass_b.parse_errors:
            return TwoPassAdjudicationPrediction(
                pass_a=pass_a,
                pass_b=pass_b,
                final=pass_a,
                final_source="pass_a_recovery_after_pass_b_parse_error",
            )
        return TwoPassAdjudicationPrediction(
            pass_a=pass_a,
            pass_b=pass_b,
            final=pass_b,
            final_source="pass_b",
        )

    def _triage_messages_for_context(
        self, record: dict[str, Any], context: str | DocumentContext | None
    ) -> list[dict[str, str]]:
        """Build the B-stage message with the same user material as final pass."""
        record = self._visible_record(record)
        system = build_triage_system_prompt(
            self._item_table, self._decision_cards, self.active_items
        )
        return build_messages(
            record,
            system,
            self.max_document_chars,
            include_normalized_facts=self.include_normalized_facts,
            document_context=context.text if isinstance(context, DocumentContext) else context,
            competition_product_context=self.competition_product_context_for_record(record),
            v24_comparison_context=(format_v24_comparison_context(record) if "v24" in self.active_items else None),
            markdown_sections=self.prompt_layout in {"markdown", "markdown_v2"},
            prompt_profile=self.prompt_profile,
            metadata_style=self.metadata_style,
            output_mode=self.prompt_output_mode,
            task_profile=self.task_profile,
        )

    def _subset_pipeline(
        self, active_items: tuple[str, ...], *, prompt_profile: str,
    ) -> "BaselinePipeline":
        """Create the B-stage final owner without carrying a frozen override.

        The parent applies the single EXP123 replacement after the full final
        row has been assembled.  This prevents a group/subset placeholder from
        becoming a second, hidden source of v2/v3/v21 decisions.
        """
        return BaselinePipeline(
            item_table=self._item_table,
            client=self.client,
            max_document_chars=self.max_document_chars,
            prompt_mode=self._prompt_mode,
            include_normalized_facts=self.include_normalized_facts,
            context_strategy=self.context_strategy,
            notice_anchor_chars=self.notice_anchor_chars,
            overflow_split_enabled=self.overflow_split_enabled,
            count_tokens=self.count_tokens,
            prompt_budget_tokens=self.prompt_budget_tokens,
            reference_text=self._reference_text,
            reference_navigation=self._reference_navigation,
            law_bundle_router=None,
            strict_document_evidence=self.strict_document_evidence,
            absence_detection_strategy=self.absence_detection_strategy,
            decision_cards=self._decision_cards,
            competition_products=self.competition_products,
            v8_composite_merge_enabled=False,
            v8_composite_merge_mode=self.v8_composite_merge_mode,
            candidate_detection=self._candidate_detection,
            active_items=active_items,
            prompt_layout=self.prompt_layout,
            prompt_profile=prompt_profile,
            role_directive=self.role_directive,
            item_catalog_style=self.item_catalog_style,
            metadata_style=self.metadata_style,
            output_mode=self.output_mode,
            visible_document_types=self.visible_document_types,
            frozen_rule_set=None,
            locator_policy=self.locator_policy,
            applicability_gate_mode="off",
        )

    def _strict_subset_pipeline(self, active_items: tuple[str, ...]) -> "BaselinePipeline":
        """Create the triage final owner with the official subset rendering."""
        return self._subset_pipeline(
            active_items, prompt_profile="official_baseline_subset_v1",
        )

    def predict_with_triage_then_strict(
        self, record: dict[str, Any]
    ) -> TriageThenStrictPrediction:
        """Run B triage and strict final without treating a route as a label."""
        contexts = self.contexts_for_record(record)
        if len(contexts) != 1:
            raise ValueError("triage-then-strict requires exactly one notice context")
        context = contexts[0]
        triage_messages = self._triage_messages_for_context(record, context)
        triage_completion = self.client.complete(triage_messages, triage_schema(self.active_items))
        triage_error: str | None = None
        try:
            states = parse_triage_response(triage_completion.content, self.active_items)
        except PredictionError as exc:
            # A malformed or incomplete route must not discard an item.  The
            # strict stage receives the complete original item set instead.
            states = {item: "불명확" for item in self.active_items}
            triage_error = str(exc)
        strict_items = tuple(
            item for item in self.active_items
            if states[item] != "해당없음" or item in ABSENCE_ITEMS
        )
        if not strict_items:
            raise RuntimeError("triage contract must route at least one item")
        strict_pipeline = self._strict_subset_pipeline(strict_items)
        strict_messages = strict_pipeline.messages_for_context(record, context)
        strict_completion = self.client.complete(strict_messages, strict_pipeline.response_schema)
        strict = strict_pipeline.finalize(record, [strict_completion], [context])
        strict_recovery_used = bool(strict.parse_errors)
        if strict_recovery_used:
            # A parse failure in a subset cannot safely zero only that subset;
            # recover with one ordinary all-item final call.  This is the sole
            # third-call path and remains visible in the result manifest.
            final = self.predict(record)
        else:
            final_judgment = zero_judgment()
            for item in strict_items:
                final_judgment[item] = strict.judgment[item]
            if self.frozen_rule_set == "exp123_v1":
                final_judgment = apply_exp123_frozen_rules(record, final_judgment)
            final = Prediction(
                record_id=record["id"],
                judgment=final_judgment,
                raw_response=strict.raw_response,
                model=strict.model,
                latency_seconds=triage_completion.latency_seconds + strict.latency_seconds,
                usage=_combined_usage([triage_completion, strict_completion]),
                finish_reason=strict.finish_reason,
                pass_judgments=strict.pass_judgments,
                v8_observations=strict.v8_observations,
                parse_errors=strict.parse_errors,
            )
        return TriageThenStrictPrediction(
            triage_raw_response=triage_completion.content,
            triage_latency_seconds=triage_completion.latency_seconds,
            triage_usage=triage_completion.usage,
            triage_finish_reason=triage_completion.finish_reason,
            triage_states=states,
            strict_items=strict_items,
            strict=strict,
            final=final,
            triage_parse_error=triage_error,
            strict_recovery_used=strict_recovery_used,
            triage_messages=tuple(triage_messages),
            strict_messages=tuple(strict_messages),
        )

    def _locator_messages_for_context(
        self,
        record: dict[str, Any],
        context: str | DocumentContext | None,
        locator_items: tuple[str, ...],
    ) -> list[dict[str, str]]:
        record = self._visible_record(record)
        system = build_locator_system_prompt(
            self._item_table, self._decision_cards, locator_items, self.locator_policy
        )
        return build_messages(
            record,
            system,
            self.max_document_chars,
            include_normalized_facts=self.include_normalized_facts,
            document_context=context.text if isinstance(context, DocumentContext) else context,
            competition_product_context=self.competition_product_context_for_record(record),
            v24_comparison_context=None,
            markdown_sections=self.prompt_layout in {"markdown", "markdown_v2"},
            prompt_profile=self.prompt_profile,
            metadata_style=self.metadata_style,
            output_mode=self.prompt_output_mode,
            task_profile="general",
        )

    def predict_with_locator_then_final(
        self, record: dict[str, Any]
    ) -> LocatorThenFinalPrediction:
        """Run C locator then an all-item V/E final pass.

        Null/invalid locator excerpts are discarded as navigation information;
        final V/E still receives all 24 items and the original notice context.
        """
        contexts = self.contexts_for_record(record)
        if len(contexts) != 1:
            raise ValueError("locator-then-final requires exactly one notice context")
        context = contexts[0]
        locator_items = tuple(item for item in self.active_items if item not in ABSENCE_ITEMS)
        locator_messages = self._locator_messages_for_context(record, context, locator_items)
        locator_completion = self.client.complete(locator_messages, locator_schema(locator_items))
        locator_error: str | None = None
        try:
            parsed = parse_locator_response(locator_completion.content, locator_items)
        except PredictionError as exc:
            parsed = {item: None for item in locator_items}
            locator_error = str(exc)
        source_context = build_official_baseline_context(
            self._visible_record(record), self.max_document_chars or 10**9
        )
        snippets = {
            item: _clean_evidence(value, source_context) if value else ""
            for item, value in parsed.items()
        }
        final_messages = append_locator_navigation(
            self.messages_for_context(record, context), snippets, locator_items
        )
        final_completion = self.client.complete(final_messages, self.response_schema)
        final = self.finalize(record, [final_completion], [context])
        recovery_used = bool(final.parse_errors)
        if recovery_used:
            final = self.predict(record)
        return LocatorThenFinalPrediction(
            locator_raw_response=locator_completion.content,
            locator_snippets=snippets,
            locator_latency_seconds=locator_completion.latency_seconds,
            locator_usage=locator_completion.usage,
            locator_finish_reason=locator_completion.finish_reason,
            locator_parse_error=locator_error,
            final=final,
            final_recovery_used=recovery_used,
            locator_messages=tuple(locator_messages),
            final_messages=tuple(final_messages),
        )

    def predict_with_inventory_then_final(
        self, record: dict[str, Any]
    ) -> InventoryThenFinalPrediction:
        """Read every admitted source pack for facts, then make one final V/E call."""
        contexts = self.contexts_for_record(record)
        inventory_system = build_inventory_system_prompt(
            self._item_table, self._decision_cards, self.active_items
        )
        collected: dict[str, list[tuple[str, str]]] = {item: [] for item in self.active_items}
        raw: list[str] = []
        usages: list[dict[str, Any]] = []
        latencies: list[float] = []
        errors: list[str] = []
        messages_log: list[tuple[dict[str, str], ...]] = []
        absence_present = {item: False for item in self.active_items if item in ABSENCE_ITEMS}
        for context in contexts:
            messages = build_messages(
                self._visible_record(record), inventory_system, self.max_document_chars,
                document_context=context.text if isinstance(context, DocumentContext) else context,
                competition_product_context=self.competition_product_context_for_record(record),
                prompt_profile=self.prompt_profile, metadata_style=self.metadata_style,
                output_mode="labels_only",
            )
            messages_log.append(tuple(messages))
            completion = self.client.complete(messages, inventory_schema(self.active_items))
            raw.append(completion.content); usages.append(completion.usage); latencies.append(completion.latency_seconds)
            try:
                parsed = parse_inventory_response(completion.content, self.active_items)
            except PredictionError as exc:
                errors.append(str(exc)); parsed = {item: None for item in self.active_items}
            source = context.text if isinstance(context, DocumentContext) else (
                context if context is not None else build_official_baseline_context(self._visible_record(record), None)
            )
            for item, value in parsed.items():
                excerpt = _clean_evidence(value, source)
                if not excerpt:
                    continue
                doc_id = next((doc["doc_id"] for doc in self._visible_record(record)["docs"] if excerpt in doc["text"]), "source")
                if (doc_id, excerpt) not in collected[item]:
                    collected[item].append((doc_id, excerpt))
                if item in absence_present:
                    absence_present[item] = True
        absence_summary = {
            item: ("전체 문서 묶음에서 필요한 조건·예외 문구가 하나 이상 관찰됨 (최종 판정 아님)"
                   if absence_present[item] else "각 문서 묶음에서 관련 필수문구를 발견하지 못함 (최종 판정 아님)")
            for item in absence_present
        }
        final_context = build_official_baseline_context(self._visible_record(record), 4000)
        final_messages = append_source_inventory(
            self.messages_for_context(record, final_context), collected, absence_summary, self.active_items
        )
        completion = self.client.complete(final_messages, self.response_schema)
        final = self.finalize(record, [completion], [final_context])
        recovery = bool(final.parse_errors)
        if recovery:
            final = self.predict(record)
        return InventoryThenFinalPrediction(
            inventory_raw_responses=tuple(raw),
            inventory_by_item={item: tuple(values) for item, values in collected.items()},
            absence_pack_summary=absence_summary,
            inventory_usage=tuple(usages), inventory_latency_seconds=tuple(latencies),
            inventory_parse_errors=tuple(errors), inventory_messages=tuple(messages_log),
            final=final, final_messages=tuple(final_messages), final_recovery_used=recovery,
        )

    def predict_with_fact_inventory_then_final(
        self, record: dict[str, Any]
    ) -> FactInventoryThenFinalPrediction:
        """Compress complete source into factual, not item-labelled, excerpts."""
        contexts = self.contexts_for_record(record)
        inventory_system = build_fact_inventory_system_prompt()
        collected: dict[str, list[tuple[str, str]]] = {
            category: [] for category in FACT_INVENTORY_CATEGORIES
        }
        raw: list[str] = []
        usages: list[dict[str, Any]] = []
        latencies: list[float] = []
        errors: list[str] = []
        messages_log: list[tuple[dict[str, str], ...]] = []
        visible = self._visible_record(record)
        for context in contexts:
            source = context.text if isinstance(context, DocumentContext) else (
                context if context is not None else build_official_baseline_context(visible, None)
            )
            messages = build_messages(
                visible, inventory_system, self.max_document_chars,
                document_context=source,
                prompt_profile=self.prompt_profile,
                metadata_style=self.metadata_style,
                output_mode="labels_only",
            )
            messages_log.append(tuple(messages))
            completion = self.client.complete(messages, fact_inventory_schema())
            raw.append(completion.content)
            usages.append(completion.usage)
            latencies.append(completion.latency_seconds)
            try:
                parsed = parse_fact_inventory_response(completion.content)
            except PredictionError as exc:
                errors.append(str(exc))
                parsed = {category: [] for category in FACT_INVENTORY_CATEGORIES}
            for category, values in parsed.items():
                for value in values:
                    excerpt = _clean_evidence(value, source)
                    if not excerpt:
                        continue
                    doc_id = next(
                        (doc["doc_id"] for doc in visible["docs"] if excerpt in doc["text"]),
                        "source",
                    )
                    if (doc_id, excerpt) not in collected[category]:
                        collected[category].append((doc_id, excerpt))
        # The original notice anchor is supplementary orientation only. Complete
        # source coverage belongs to the first factual stage, not this 4k block.
        final_context = build_official_baseline_context(visible, 4000)
        final_messages = append_fact_inventory(
            self.messages_for_context(record, final_context),
            {category: tuple(values) for category, values in collected.items()},
        )
        completion = self.client.complete(final_messages, self.response_schema)
        final = self.finalize(record, [completion], [final_context])
        recovery = bool(final.parse_errors)
        if recovery:
            final = self.predict(record)
        return FactInventoryThenFinalPrediction(
            inventory_raw_responses=tuple(raw),
            inventory_by_category={category: tuple(values) for category, values in collected.items()},
            inventory_usage=tuple(usages),
            inventory_latency_seconds=tuple(latencies),
            inventory_parse_errors=tuple(errors),
            inventory_messages=tuple(messages_log),
            final=final,
            final_messages=tuple(final_messages),
            final_recovery_used=recovery,
        )

    def predict_with_fact_inventory_then_full_final(
        self, record: dict[str, Any], inventory_max_items: int = 3,
        inventory_position: str = "after_source",
        inventory_categories: tuple[str, ...] = FACT_INVENTORY_CATEGORIES,
    ) -> FactInventoryFullFinalPrediction:
        """Use non-final source facts while retaining every source in final V/E.

        The navigation ledger is advisory only.  It is appended before exact
        token admission, so its presence may create extra final source packs;
        no source document is dropped and an empty ledger never becomes 0.
        """
        if self.count_tokens is None:
            raise ValueError("fact-inventory full-final requires exact tokenizer admission")
        stage_contexts = self.contexts_for_record(record)
        inventory_system = build_fact_inventory_system_prompt(
            inventory_max_items, categories=inventory_categories,
        )
        collected: dict[str, list[tuple[str, str]]] = {
            category: [] for category in inventory_categories
        }
        raw: list[str] = []
        usages: list[dict[str, Any]] = []
        latencies: list[float] = []
        errors: list[str] = []
        messages_log: list[tuple[dict[str, str], ...]] = []
        visible = self._visible_record(record)
        for context in stage_contexts:
            source = context.text if isinstance(context, DocumentContext) else (
                context if context is not None else build_official_baseline_context(visible, None)
            )
            messages = build_messages(
                visible, inventory_system, self.max_document_chars,
                document_context=source,
                prompt_profile=self.prompt_profile,
                metadata_style=self.metadata_style,
                output_mode="labels_only",
            )
            messages_log.append(tuple(messages))
            completion = self.client.complete(
                messages, fact_inventory_schema(inventory_max_items, categories=inventory_categories),
            )
            raw.append(completion.content)
            usages.append(completion.usage)
            latencies.append(completion.latency_seconds)
            try:
                parsed = parse_fact_inventory_response(
                    completion.content,
                    max_items=inventory_max_items,
                    categories=inventory_categories,
                )
            except PredictionError as exc:
                errors.append(str(exc))
                parsed = {category: [] for category in inventory_categories}
            for category, values in parsed.items():
                for value in values:
                    excerpt = _clean_evidence(value, source)
                    if not excerpt:
                        continue
                    doc_id = next(
                        (doc["doc_id"] for doc in visible["docs"] if excerpt in doc["text"]),
                        "source",
                    )
                    if (doc_id, excerpt) not in collected[category]:
                        collected[category].append((doc_id, excerpt))

        inventory = {category: tuple(values) for category, values in collected.items()}

        def final_messages_for(context: str | None) -> list[dict[str, str]]:
            return append_fact_inventory(
                self.messages_for_context(record, context), inventory,
                position=inventory_position,
                categories=inventory_categories,
            )

        final_contexts = pack_contexts_to_token_budget(
            visible,
            self.system_prompt_for_record(record),
            self.count_tokens,
            self.prompt_budget_tokens,
            self.notice_anchor_chars,
            message_builder=final_messages_for,
        )
        final_messages = [final_messages_for(context) for context in final_contexts]
        completions = [self.client.complete(messages, self.response_schema) for messages in final_messages]
        final = self.finalize(record, completions, final_contexts)
        recovery = bool(final.parse_errors)
        if recovery:
            final = self.predict(record)
        return FactInventoryFullFinalPrediction(
            inventory_raw_responses=tuple(raw),
            inventory_by_category=inventory,
            inventory_usage=tuple(usages),
            inventory_latency_seconds=tuple(latencies),
            inventory_parse_errors=tuple(errors),
            inventory_messages=tuple(messages_log),
            inventory_max_items=inventory_max_items,
            inventory_position=inventory_position,
            inventory_categories=inventory_categories,
            final=final,
            final_messages_by_context=tuple(tuple(messages) for messages in final_messages),
            final_recovery_used=recovery,
        )

    def contexts_for_record(
        self, record: dict[str, Any]
    ) -> list[str | DocumentContext | None]:
        record = self._visible_record(record)
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
                message_builder=lambda context: self.messages_for_context(record, context),
            )
            return contexts
        if self.context_strategy == "single_no_split":
            if self.count_tokens is None:
                raise ValueError("single_no_split requires an exact tokenizer token counter")
            messages = self.messages_for_context(record, None)
            token_count = self.count_tokens(messages)
            if token_count > self.prompt_budget_tokens:
                raise ContextAdmissionError(
                    f"{record['id']} requires {token_count} prompt tokens; "
                    f"budget is {self.prompt_budget_tokens}"
                )
            return [None]
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
                message_builder=lambda context: self.messages_for_context(record, context),
            )
        return forced_contexts

    def messages_for_context(
        self, record: dict[str, Any], context: str | DocumentContext | None
    ) -> list[dict[str, str]]:
        record = self._visible_record(record)
        return build_messages(
            record, self.system_prompt_for_record(record), self.max_document_chars,
            include_normalized_facts=self.include_normalized_facts,
            document_context=context.text if isinstance(context, DocumentContext) else context,
            competition_product_context=self.competition_product_context_for_record(record),
            v24_comparison_context=(format_v24_comparison_context(record) if "v24" in self.active_items else None),
            markdown_sections=self.prompt_layout in {"markdown", "markdown_v2"},
            prompt_profile=self.prompt_profile,
            metadata_style=self.metadata_style,
            output_mode=self.prompt_output_mode,
            task_profile=self.task_profile,
        )

    def _visible_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """Return the config-selected source documents without mutating input data."""
        if self.visible_document_types is None:
            return record
        return {
            **record,
            "docs": [
                document for document in record["docs"]
                if document["type"] in self.visible_document_types
            ],
        }

    def competition_product_context_for_record(self, record: dict[str, Any]) -> str | None:
        if self.competition_products is None:
            return None
        # Every v10–v18 condition depends on the organizer CSV's exact product
        # classification.  The renderer decides which Korean clarification is
        # relevant to the active subset; do not silently remove the underlying
        # applicability fact for v12/v14/v15/v17.
        product_items = {f"v{number}" for number in range(10, 19)}
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
        if self.frozen_rule_set == "exp123_v1":
            judgment = apply_exp123_frozen_rules(record, judgment)
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
