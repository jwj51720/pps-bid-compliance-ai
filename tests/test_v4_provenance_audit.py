from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.pps_ai.audits.v4_provenance import (
    _confusion,
    _parse_v4_response,
    _selected_source,
)
from src.pps_ai.domain import NoticeDocument, NoticeRecord


def test_confusion_uses_positive_class_f1() -> None:
    labels = {
        "A": {"v4": "1"}, "B": {"v4": "1"}, "C": {"v4": "0"},
    }
    assert _confusion(labels, {"A": 1, "B": 0, "C": 1}) == {
        "tp": 1, "fp": 1, "fn": 1, "f1": 0.5,
    }


def test_parse_v4_response_rejects_unknown_enum(tmp_path: Path) -> None:
    path = tmp_path / "response.json"
    path.write_text(json.dumps({
        "content": json.dumps({"v4": {"q": "Y", "r": "?", "e": "N", "id": None}}),
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid r"):
        _parse_v4_response(path)


def test_selected_source_requires_exact_supplied_document_substring() -> None:
    text = "입찰참가자격: 최근 실적이 있는 업체"
    document = NoticeDocument(
        notice_id="N1", doc_id="D0", document_type="공고문", order=0, text=text,
        sha256="0" * 64,
    )
    record = NoticeRecord(
        notice_id="N1", documents=(document,), metadata={}, input_completeness={},
        dropped_document_counts={}, raw={},
    )
    candidates = [{"id": "S01", "doc_id": "D0", "text": "최근 실적이 있는 업체"}]
    selected = _selected_source(record, candidates, "S01")
    assert selected is not None
    assert selected["document_sha256"] == "0" * 64

    with pytest.raises(ValueError, match="exact document substring"):
        _selected_source(record, [{"id": "S02", "doc_id": "D0", "text": "바뀐 문구"}], "S02")
