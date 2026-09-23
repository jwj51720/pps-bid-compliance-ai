"""Tests for label-free v3 population morphology audit."""

from __future__ import annotations

import json

from src.pps_ai.domain import NoticeDocument, NoticeRecord
from src.pps_ai.v3_population_audit import (
    amount_relation,
    summarize_dev_observations,
    summarize_records,
)


def _record(text: str, *, estimate: int = 100_000_000) -> NoticeRecord:
    raw = {
        "id": "N1",
        "docs": [{"doc_id": "D1", "type": "공고문", "text": text}],
        "meta": {"입찰추정가격": estimate},
    }
    document = NoticeDocument.from_raw("N1", 0, raw["docs"][0])
    return NoticeRecord("N1", (document,), raw["meta"], {}, {}, raw)


def test_amount_relation_is_source_upper_bound() -> None:
    relation, band, surfaces, parsed = amount_relation(
        "실적 5천만원 또는 2억원", 100_000_000,
    )
    assert relation == "mixed_le_and_gt_estimate"
    assert band == "ge_1.5"
    assert surfaces == 2
    assert parsed == 2


def test_summarize_records_separates_notice_and_candidate_denominators() -> None:
    summary = summarize_records([
        _record("입찰 참가자격은 최근 실적 합계 2억원 이상인 업체입니다."),
        _record("금액 표면이 없는 일반 공고입니다."),
    ])
    assert summary["records"] == 2
    assert summary["candidates"] == 1
    assert summary["notice_feature_counts"]["candidate_route"] == 1
    assert summary["candidate_feature_counts"]["qualification_surface"] == 1
    assert summary["candidate_feature_counts"]["aggregate_surface"] == 1
    assert summary["candidate_feature_counts"]["contains_amount_gt_estimate"] == 1


def test_summarize_dev_observations_preserves_raw_basis(tmp_path) -> None:
    path = tmp_path / "observations.json"
    path.write_text(json.dumps([{
        "id": "N1",
        "diagnostic": {
            "valid": True,
            "observations": [{
                "role": "BID_QUALIFICATION",
                "requirement_basis": "AGGREGATE",
                "mandatory": "YES",
            }],
        },
    }]), encoding="utf-8")
    summary = summarize_dev_observations(path)
    assert summary["aggregate_qualification_notice_count"] == 1
    assert summary["aggregate_qualification_notice_ids"] == ["N1"]
