from __future__ import annotations

import json

from src.pps_ai.decisions.v3_keyed_serialization import (
    adapt_keyed_response,
    build_v3_keyed_schema,
    decide_v3_keyed,
)
from src.pps_ai.views.v3_monetary import build_v3_monetary_view


def _record() -> dict[str, object]:
    return {
        "id": "N1",
        "meta": {"입찰추정가격": 100_000_000},
        "docs": [
            {"doc_id": "D0", "type": "공고문", "text": "참가자격 수행실적 2억원 이상."},
            {"doc_id": "D1", "type": "제안요청서", "text": "평가용 수행실적 3억원 이상이면 5점."},
        ],
    }


def _response(observations: dict[str, object]) -> dict[str, object]:
    return {
        "finish_reason": "stop",
        "invalid": False,
        "content": json.dumps({"observations": observations}, ensure_ascii=False),
    }


def test_keyed_schema_requires_exact_candidate_keys() -> None:
    view = build_v3_monetary_view(_record())
    observations = build_v3_keyed_schema(view)["properties"]["observations"]
    assert observations["required"] == ["M01", "M02"]
    assert set(observations["properties"]) == {"M01", "M02"}
    assert observations["additionalProperties"] is False
    assert "source_id" not in observations["properties"]["M01"]["properties"]


def test_adapter_rejects_missing_or_extra_candidate_key() -> None:
    view = build_v3_monetary_view(_record())
    value = {
        "role": "OTHER", "requirement_basis": "UNKNOWN",
        "mandatory": "UNKNOWN", "amount_surface": None,
    }
    assert adapt_keyed_response(_response({"M01": value}), view) is None
    assert adapt_keyed_response(_response({"M01": value, "M02": value, "M03": value}), view) is None


def test_keyed_adapter_preserves_v3_reducer_semantics() -> None:
    record = _record()
    view = build_v3_monetary_view(record)
    response = _response({
        "M01": {
            "role": "BID_QUALIFICATION",
            "requirement_basis": "SINGLE_CONTRACT",
            "mandatory": "YES",
            "amount_surface": "2억원",
        },
        "M02": {
            "role": "EVALUATION",
            "requirement_basis": "SINGLE_CONTRACT",
            "mandatory": "NO",
            "amount_surface": "3억원",
        },
    })
    value, evidence, diagnostic = decide_v3_keyed(record, view, response, 0, "")
    assert value == 1
    assert evidence in record["docs"][0]["text"]
    assert diagnostic["decision"] == "POSITIVE_PROOF"

