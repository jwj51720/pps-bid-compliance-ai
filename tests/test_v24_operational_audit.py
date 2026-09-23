from __future__ import annotations

from src.pps_ai.domain import NoticeDocument, NoticeRecord
from src.pps_ai.v24_operational_audit import (
    binary_metrics,
    evidence_axis_surface,
    error_strata,
    metadata_axis_available,
    notice_surface,
)


def _record() -> NoticeRecord:
    raw = {
        "id": "N1",
        "meta": {
            "배정예산금액": 100000000,
            "입찰추정가격": 90909091,
            "계약방법": "제한경쟁",
            "지역제한여부": "Y",
            "제한지역코드목록": "서울특별시",
            "업종제한여부": "N",
            "면허업종제한목록": None,
        },
        "docs": [
            {"doc_id": "D0", "type": "공고문", "text": "추정가격 90,909,091원 제한경쟁"},
            {"doc_id": "D1", "type": "규격서", "text": "본점 소재지 서울특별시"},
        ],
    }
    documents = tuple(
        NoticeDocument.from_raw("N1", order, document)
        for order, document in enumerate(raw["docs"])
    )
    return NoticeRecord("N1", documents, raw["meta"], {}, {}, raw)


def test_metadata_availability_respects_no_restriction_flags() -> None:
    meta = _record().raw["meta"]
    assert metadata_axis_available(meta, "region")
    assert metadata_axis_available(meta, "industry")


def test_notice_surface_tracks_comparable_and_attachment_axes() -> None:
    row = notice_surface(_record(), 6850)
    assert row["axes"]["amount"]["comparable_surface"]
    assert row["axes"]["contract"]["comparable_surface"]
    assert row["axes"]["region"]["attachment_candidate_surface"]
    assert not row["axes"]["industry"]["candidate_surface"]


def test_error_strata_uses_predictions_only_for_evaluation_partition() -> None:
    base = {"features": {"amount.candidate_surface"}, "axes": {}}
    surfaces = {f"N{i}": base for i in range(1, 5)}
    result = error_strata(
        surfaces,
        {"N1": 1, "N2": 0, "N3": 1, "N4": 0},
        {"N1": 1, "N2": 1, "N3": 0, "N4": 0},
        1,
    )
    assert result["counts"] == {"TP": 1, "FP": 1, "FN": 1, "TN": 1}


def test_evidence_axis_surface_is_literal_and_can_be_multi_axis() -> None:
    assert evidence_axis_surface("추정가격과 계약방법") == ["amount", "contract"]
    assert evidence_axis_surface("관련 문구") == ["unclassified"]


def test_binary_metrics_reports_positive_class_f1() -> None:
    assert binary_metrics({"a": 1, "b": 0, "c": 1}, {"a": 1, "b": 1, "c": 0}) == {
        "tp": 1, "fp": 1, "fn": 1, "f1": 0.5,
    }
