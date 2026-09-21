"""Estimate full-notice prompt budgets from recorded Gemma usage."""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from src.data import load_item_table
from src.prompt import DOCUMENT_ORDER, build_messages, build_system_prompt

TokenCounter = Callable[[list[dict[str, str]]], int]


@dataclass(frozen=True)
class DocumentContext:
    """A rendered full-split pass and the exact target text visible in it."""

    text: str
    target_document_id: str
    target_document_type: str
    target_text: str


def estimate_context_budget(
    records: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    item_table_path: str | Path,
    current_document_chars: int,
    max_model_len: int,
    output_reserve_tokens: int,
) -> dict[str, Any]:
    """Scale observed prompt-token use to an otherwise identical full-doc prompt.

    This is a diagnostic estimate, not a replacement for counting with the
    evaluation server's supplied Gemma tokenizer during packaging.
    """
    if current_document_chars <= 0:
        raise ValueError("current_document_chars must be positive")
    if not 0 < output_reserve_tokens < max_model_len:
        raise ValueError("output_reserve_tokens must be within max_model_len")

    records_by_id = {record["id"]: record for record in records}
    token_usage = {
        prediction["id"]: prediction.get("usage", {}).get("prompt_tokens")
        for prediction in predictions
    }
    missing = sorted(record_id for record_id in records_by_id if not token_usage.get(record_id))
    if missing:
        raise ValueError(f"missing recorded prompt token usage: {missing[:10]}")

    system_prompt = build_system_prompt(load_item_table(item_table_path))
    prompt_budget = max_model_len - output_reserve_tokens
    rows: list[dict[str, Any]] = []
    for record_id in sorted(records_by_id):
        record = records_by_id[record_id]
        current_chars = _message_characters(
            build_messages(record, system_prompt, current_document_chars)
        )
        full_chars = _message_characters(build_messages(record, system_prompt, 10**9))
        observed_tokens = int(token_usage[record_id])
        estimate = observed_tokens * full_chars / current_chars
        rows.append(
            {
                "id": record_id,
                "observed_prompt_tokens": observed_tokens,
                "current_prompt_characters": current_chars,
                "full_prompt_characters": full_chars,
                "estimated_full_prompt_tokens": round(estimate, 2),
                "fits_estimated_budget": estimate <= prompt_budget,
            }
        )

    estimates = sorted(row["estimated_full_prompt_tokens"] for row in rows)
    return {
        "method": "per-notice prompt-token scaling from recorded same-model usage",
        "limitation": (
            "Estimate only: exact submission validation must call the supplied "
            "Gemma tokenizer with the final chat template."
        ),
        "max_model_len": max_model_len,
        "output_reserve_tokens": output_reserve_tokens,
        "prompt_budget_tokens": prompt_budget,
        "source_document_char_limit": current_document_chars,
        "record_count": len(rows),
        "estimated_fit_count": sum(row["fits_estimated_budget"] for row in rows),
        "estimated_overflow_count": sum(not row["fits_estimated_budget"] for row in rows),
        "estimated_full_prompt_tokens": _summarize(estimates),
        "largest_estimated_records": sorted(
            rows,
            key=lambda row: row["estimated_full_prompt_tokens"],
            reverse=True,
        )[:10],
        "records": rows,
    }


def _message_characters(messages: list[dict[str, str]]) -> int:
    return sum(len(message["content"]) for message in messages)


def _summarize(values: list[float]) -> dict[str, float]:
    if not values:
        return {"median": 0.0, "p95": 0.0, "max": 0.0}
    return {
        "median": round(statistics.median(values), 2),
        "p95": round(_quantile(values, 0.95), 2),
        "max": round(max(values), 2),
    }


def _quantile(values: list[float], probability: float) -> float:
    position = (len(values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    weight = position - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def pack_contexts_to_token_budget(
    record: dict[str, Any],
    system_prompt: str,
    count_tokens: TokenCounter,
    prompt_budget_tokens: int,
    notice_anchor_chars: int = 4000,
    competition_product_context: str | None = None,
    message_builder: Callable[[str | None], list[dict[str, str]]] | None = None,
) -> list[str | None]:
    """Return one full context or ordered, token-admitted split contexts.

    Every returned context is counted with the same final system/user messages.
    An overflowing source document is split at a character boundary only after
    token counting finds the largest prefix that fits; characters are never used
    as the admission criterion.
    """
    def messages_for(context: str | None) -> list[dict[str, str]]:
        if message_builder is not None:
            return message_builder(context)
        return build_messages(
            record,
            system_prompt,
            None,
            document_context=context,
            competition_product_context=competition_product_context,
        )

    full_messages = messages_for(None)
    if count_tokens(full_messages) <= prompt_budget_tokens:
        # ``None`` preserves the pipeline's normal full-document construction
        # when the caller supplied the actual final message builder.  Retain
        # the historic rendered-string return for standalone callers.
        if message_builder is not None:
            return [None]
        return [
            build_messages(
                record,
                system_prompt,
                None,
                competition_product_context=competition_product_context,
            )[1]["content"].split("[문서]\n", 1)[1]
        ]

    order = {name: index for index, name in enumerate(DOCUMENT_ORDER)}
    documents = sorted(
        record["docs"],
        key=lambda document: (order.get(document["type"], len(order)), document["doc_id"]),
    )
    announcement = next(document for document in documents if document["type"] == "공고문")
    anchor = announcement["text"][:notice_anchor_chars]
    anchor_header = f"[공고문 앵커:{announcement['doc_id']}]\n"

    unavailable = record.get("dropped_doc_counts") or {}
    unavailable_text = ""
    if unavailable:
        unavailable_text = "\n\n[미수록 문서] " + ", ".join(
            f"{name} {count}건" for name, count in sorted(unavailable.items())
        )

    def render(parts: list[str]) -> str:
        prefix = anchor_header + anchor if anchor else ""
        body = "\n\n".join(parts)
        return "\n\n".join(value for value in (prefix, body) if value) + unavailable_text

    def fits(parts: list[str]) -> bool:
        return count_tokens(messages_for(render(parts))) <= prompt_budget_tokens

    # Ensure even an unusually long announcement anchor cannot block progress.
    if not fits([]):
        low, high = 0, len(anchor)
        while low < high:
            middle = (low + high + 1) // 2
            anchor = announcement["text"][:middle]
            if fits([]):
                low = middle
            else:
                high = middle - 1
        anchor = announcement["text"][:low]
        if not fits([]):
            raise ValueError("metadata and prompt exceed token budget before documents")

    contexts: list[str] = []
    current: list[str] = []

    def flush() -> None:
        nonlocal current
        if current:
            contexts.append(render(current))
            current = []

    for document in documents:
        header = f"[{document['type']}:{document['doc_id']}]\n"
        text = document["text"]
        offset = 0
        while offset < len(text) or (not text and offset == 0):
            suffix = "" if offset == 0 else f" [계속 {offset}]"
            fragment_header = header.rstrip("\n") + suffix + "\n"
            remaining = text[offset:]
            candidate = current + [fragment_header + remaining]
            if fits(candidate):
                current = candidate
                offset = len(text) if text else 1
                continue
            if current:
                flush()
                continue
            low, high = 1, len(remaining)
            best = 0
            while low <= high:
                middle = (low + high) // 2
                if fits([fragment_header + remaining[:middle]]):
                    best = middle
                    low = middle + 1
                else:
                    high = middle - 1
            if best == 0:
                raise ValueError(f"document header cannot fit token budget: {document['doc_id']}")
            current = [fragment_header + remaining[:best]]
            offset += best
            flush()
    flush()
    return contexts


def pack_document_contexts_to_token_budget(
    record: dict[str, Any],
    system_prompt: str,
    count_tokens: TokenCounter,
    prompt_budget_tokens: int,
    notice_anchor_chars: int = 4000,
    competition_product_context: str | None = None,
    message_builder: Callable[[str], list[dict[str, str]]] | None = None,
) -> list[DocumentContext]:
    """Make a pass per source document, splitting only an oversized document.

    This is deliberately different from :func:`pack_contexts_to_token_budget`.
    The adaptive packer combines consecutive documents until the final Gemma
    prompt would overflow.  This mode instead exposes exactly one target source
    document in each pass.  A bounded announcement anchor accompanies
    non-announcement documents so every pass remains tied to the notice, as
    required by the competition input policy.  The target document itself is
    never character-truncated: a too-large document becomes ordered fragments
    admitted by the final chat-template token count.
    """
    order = {name: index for index, name in enumerate(DOCUMENT_ORDER)}
    documents = sorted(
        record["docs"],
        key=lambda document: (order.get(document["type"], len(order)), document["doc_id"]),
    )
    announcement = next(document for document in documents if document["type"] == "공고문")
    anchor = announcement["text"][:notice_anchor_chars]
    anchor_header = f"[공고문 앵커:{announcement['doc_id']}]\n"

    unavailable = record.get("dropped_doc_counts") or {}
    unavailable_text = ""
    if unavailable:
        unavailable_text = "\n\n[미수록 문서] " + ", ".join(
            f"{name} {count}" for name, count in sorted(unavailable.items())
        )

    def render(target: str, include_anchor: bool) -> str:
        prefix = anchor_header + anchor if include_anchor and anchor else ""
        return "\n\n".join(value for value in (prefix, target) if value) + unavailable_text

    def fits(target: str, include_anchor: bool) -> bool:
        context = render(target, include_anchor)
        messages = (
            message_builder(context)
            if message_builder is not None
            else build_messages(
                record,
                system_prompt,
                None,
                document_context=context,
                competition_product_context=competition_product_context,
            )
        )
        return count_tokens(messages) <= prompt_budget_tokens

    # Metadata, system prompt, and the fixed reference are mandatory context;
    # do not silently drop them to make document splitting appear successful.
    if not fits("", False):
        raise ValueError("metadata and prompt exceed token budget before documents")

    contexts: list[DocumentContext] = []
    for document in documents:
        header = f"[{document['type']}:{document['doc_id']}]\n"
        include_anchor = document["doc_id"] != announcement["doc_id"]
        text = document["text"]
        offset = 0
        while offset < len(text) or (not text and offset == 0):
            suffix = "" if offset == 0 else f" [계속 {offset}]"
            fragment_header = header.rstrip("\n") + suffix + "\n"
            remaining = text[offset:]
            whole_fragment = fragment_header + remaining
            if fits(whole_fragment, include_anchor):
                contexts.append(
                    DocumentContext(
                        text=render(whole_fragment, include_anchor),
                        target_document_id=document["doc_id"],
                        target_document_type=document["type"],
                        target_text=remaining,
                    )
                )
                offset = len(text) if text else 1
                continue

            low, high = 1, len(remaining)
            best = 0
            while low <= high:
                middle = (low + high) // 2
                if fits(fragment_header + remaining[:middle], include_anchor):
                    best = middle
                    low = middle + 1
                else:
                    high = middle - 1
            if best == 0:
                raise ValueError(f"document header cannot fit token budget: {document['doc_id']}")
            contexts.append(
                DocumentContext(
                    text=render(fragment_header + remaining[:best], include_anchor),
                    target_document_id=document["doc_id"],
                    target_document_type=document["type"],
                    target_text=remaining[:best],
                )
            )
            offset += best
    return contexts
