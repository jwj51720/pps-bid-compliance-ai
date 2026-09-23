"""Tests for label-free v19 population morphology."""

from __future__ import annotations

import json

from src.pps_ai.domain import NoticeDocument, NoticeRecord
from src.pps_ai.v19_population_audit import (
    morphology_features,
    summarize_dev_observations,
    summarize_records,
)


def _record(text: str) -> NoticeRecord:
    raw = {
        "id": "N1",
        "docs": [{"doc_id": "D1", "type": "공고문", "text": text}],
        "meta": {},
    }
    document = NoticeDocument.from_raw("N1", 0, raw["docs"][0])
    return NoticeRecord("N1", (document,), {}, {}, {}, raw)


def test_morphology_features_preserve_cooccurrence_without_decision() -> None:
    features = morphology_features(
        "제조사의 물품공급 확약서를 입찰서와 함께 제출한다."
    )
    assert "external_and_supply_surface" in features
    assert "external_supply_and_bid_surface" in features
    assert "self_or_form_without_external_supply" not in features


def test_summarize_records_counts_candidate_and_self_form_stratum() -> None:
    summary = summarize_records([
        _record("청렴계약 이행확약서 별지 서식을 준수합니다."),
        _record("일반 공고문입니다."),
    ])
    assert summary["records"] == 2
    assert summary["candidates"] == 1
    assert summary["notice_feature_counts"]["candidate_route"] == 1
    assert summary["candidate_feature_counts"]["self_promise_surface"] == 1
    assert summary["candidate_feature_counts"]["self_or_form_without_external_supply"] == 1


def test_summarize_dev_observations_counts_positive_predicate(tmp_path) -> None:
    path = tmp_path / "observations.json"
    path.write_text(json.dumps([{
        "id": "N1",
        "diagnostic": {
            "fallback": False,
            "observations": [{
                "requirement_role": "BID_OR_PROPOSAL_QUALIFICATION",
                "document_kind": "EXTERNAL_SUPPLY_OR_TECH_ASSURANCE",
                "positive_predicate": True,
            }],
        },
    }]), encoding="utf-8")
    summary = summarize_dev_observations(path)
    assert summary["positive_predicate_notice_count"] == 1
    assert summary["role_kind_counts"][
        "BID_OR_PROPOSAL_QUALIFICATION|EXTERNAL_SUPPLY_OR_TECH_ASSURANCE"
    ] == 1
