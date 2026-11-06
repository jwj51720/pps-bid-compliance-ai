from __future__ import annotations

import json

from src.pps_ai.decisions.v19_quote_resolution_v2 import (
    parse_v19_observations_relaxed_quote,
    reduce_v19_with_quote_resolution,
    resolve_exact_quote,
)
from src.pps_ai.views.v19_requirements import build_v19_requirement_view


def _row(quote: str, *, positive: bool) -> dict[str, str]:
    return {
        "requirement_role": "BID_OR_PROPOSAL_QUALIFICATION" if positive else "OTHER",
        "document_kind": "EXTERNAL_SUPPLY_OR_TECH_ASSURANCE" if positive else "OTHER_DOCUMENT",
        "external_issuer_explicit": "YES" if positive else "NO",
        "bidder_must_obtain_or_hold": "YES" if positive else "NO",
        "bidder_must_submit": "NO",
        "obtain_before_bid_deadline": "YES" if positive else "NO",
        "submit_with_bid_or_proposal": "NO",
        "submit_after_bid_or_contract": "NO",
        "quoted_text": quote,
    }


def test_whitespace_only_resolution_returns_unchanged_source_span() -> None:
    source = "제조사의 물품공급 확약서를\n입찰 마감 전까지  보유하여야 한다."
    quote = "제조사의 물품공급 확약서를 입찰 마감 전까지 보유하여야 한다."
    resolved, method = resolve_exact_quote(source, quote)
    assert method == "WHITESPACE_UNIQUE"
    assert resolved == source
    assert resolved in source


def test_resolution_rejects_non_whitespace_edit_and_ambiguous_match() -> None:
    assert resolve_exact_quote("원문 확약서", "요약 확약서") == (None, "NO_MATCH")
    assert resolve_exact_quote("확 약서 / 확  약서", "확약서") == (None, "AMBIGUOUS_MATCH")


def test_negative_invalid_quote_does_not_invalidate_semantic_response() -> None:
    record = {
        "id": "N1", "meta": {},
        "docs": [{"doc_id": "D0", "type": "공고문", "text": "직접이행 확약서"}],
    }
    candidates = build_v19_requirement_view(record)["candidates"]
    response = {
        "finish_reason": "stop", "invalid": False,
        "content": json.dumps({"observations": {"R01": _row("N/A", positive=False)}}),
    }
    rows, reason = parse_v19_observations_relaxed_quote(response, candidates)
    assert reason is None
    assert rows is not None
    value, evidence, diagnostic = reduce_v19_with_quote_resolution(candidates, rows)
    assert (value, evidence) == (0, "")
    assert diagnostic["quote_resolution"][0]["resolved"] is False


def test_positive_requires_exactly_resolvable_evidence() -> None:
    source = "제조사의 물품공급 확약서를\n입찰 마감 전까지 보유하여야 한다."
    record = {
        "id": "N1", "meta": {},
        "docs": [{"doc_id": "D0", "type": "공고문", "text": source}],
    }
    candidates = build_v19_requirement_view(record)["candidates"]
    response = {
        "finish_reason": "stop", "invalid": False,
        "content": json.dumps({"observations": {
            "R01": _row(
                "제조사의 물품공급 확약서를 입찰 마감 전까지 보유하여야 한다.",
                positive=True,
            ),
        }}),
    }
    rows, _ = parse_v19_observations_relaxed_quote(response, candidates)
    assert rows is not None
    value, evidence, diagnostic = reduce_v19_with_quote_resolution(candidates, rows)
    assert value == 1
    assert evidence == source
    assert diagnostic["quote_resolution"][0]["method"] == "WHITESPACE_UNIQUE"

    response["content"] = json.dumps({"observations": {
        "R01": _row("원문과 다른 물품공급 확약서", positive=True),
    }})
    rows, _ = parse_v19_observations_relaxed_quote(response, candidates)
    assert rows is not None
    value, evidence, diagnostic = reduce_v19_with_quote_resolution(candidates, rows)
    assert value is None
    assert evidence == ""
    assert diagnostic["fallback"] is True
