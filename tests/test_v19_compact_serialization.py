from __future__ import annotations

import json

from src.pps_ai.decisions.v19_compact_serialization import (
    adapt_compact_response,
    build_v19_compact_schema,
    build_v19_compact_task,
)
from src.pps_ai.decisions.v19_quote_resolution_v2 import (
    parse_v19_observations_relaxed_quote,
)
from src.pps_ai.views.v19_requirements import build_v19_requirement_view


def _fixture() -> tuple[dict[str, object], dict[str, object]]:
    record = {
        "id": "N1", "meta": {},
        "docs": [{
            "doc_id": "D0", "type": "공고문",
            "text": "제조사의 물품공급 확약서를 입찰 마감 전까지 보유한다.",
        }],
    }
    return record, build_v19_requirement_view(record)


def test_compact_schema_preserves_all_nine_required_fields() -> None:
    _, view = _fixture()
    schema = build_v19_compact_schema(view["candidates"])
    cell = schema["properties"]["observations"]["properties"]["R01"]
    assert cell["required"] == ["r", "k", "x", "h", "s", "b", "w", "a", "q"]
    assert cell["additionalProperties"] is False


def test_compact_task_preserves_user_and_semantic_system_prefix() -> None:
    record, view = _fixture()
    from src.pps_ai.decisions.v19_requirements import build_v19_task

    base = build_v19_task(record, view["candidates"])
    compact = build_v19_compact_task(record, view["candidates"])
    assert compact["messages"][1] == base["messages"][1]
    assert compact["messages"][0]["content"].startswith(base["messages"][0]["content"])


def test_compact_adapter_round_trips_every_semantic_field() -> None:
    _, view = _fixture()
    compact = {
        "r": 0, "k": 0, "x": 1, "h": 1, "s": 0,
        "b": 1, "w": 0, "a": 2, "q": view["candidates"][0].text,
    }
    response = {
        "finish_reason": "stop", "invalid": False,
        "content": json.dumps({"observations": {"R01": compact}}, ensure_ascii=False),
    }
    adapted = adapt_compact_response(response, view["candidates"])
    assert adapted is not None
    rows, reason = parse_v19_observations_relaxed_quote(adapted, view["candidates"])
    assert reason is None
    assert rows == [{
        "source_id": "R01",
        "requirement_role": "BID_OR_PROPOSAL_QUALIFICATION",
        "document_kind": "EXTERNAL_SUPPLY_OR_TECH_ASSURANCE",
        "external_issuer_explicit": "YES",
        "bidder_must_obtain_or_hold": "YES",
        "bidder_must_submit": "NO",
        "obtain_before_bid_deadline": "YES",
        "submit_with_bid_or_proposal": "NO",
        "submit_after_bid_or_contract": "UNKNOWN",
        "quoted_text": view["candidates"][0].text,
    }]


def test_compact_adapter_rejects_missing_or_extra_key() -> None:
    _, view = _fixture()
    value = {
        "r": 6, "k": 4, "x": 2, "h": 2, "s": 2,
        "b": 2, "w": 2, "a": 2, "q": "N/A",
    }
    for changed in ({key: item for key, item in value.items() if key != "a"}, {**value, "z": 0}):
        response = {
            "finish_reason": "stop", "invalid": False,
            "content": json.dumps({"observations": {"R01": changed}}),
        }
        assert adapt_compact_response(response, view["candidates"]) is None
