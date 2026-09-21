from __future__ import annotations

import hashlib
from pathlib import Path

from src.pps_ai.domain import NoticeDocument, NoticeRecord
from src.pps_ai.views.v9_targets import build_v9_target_view


def _record() -> NoticeRecord:
    raw = {
        "id": "N1",
        "meta": {},
        "docs": [
            {
                "doc_id": "D0",
                "type": "공고문",
                "text": "납품 제품은 동등 이상 제품을 허용한다.",
            },
            {
                "doc_id": "D1",
                "type": "규격서",
                "text": "제조사·모델명: Example AB-1200 장비를 사용할 것.",
            },
            {
                "doc_id": "D2",
                "type": "과업지시서",
                "text": "일반적인 작업 절차만 설명한다.",
            },
        ],
    }
    documents = tuple(
        NoticeDocument.from_raw("N1", order, value)
        for order, value in enumerate(raw["docs"])
    )
    return NoticeRecord("N1", documents, {}, {}, {}, raw)


def test_v9_view_inspects_every_document_and_preserves_source_order() -> None:
    view = build_v9_target_view(_record())
    assert [row["doc_id"] for row in view["document_coverage"]] == ["D0", "D1", "D2"]
    assert all(row["inspected"] for row in view["document_coverage"])
    assert [candidate.doc_id for candidate in view["candidates"]] == ["D0", "D1"]
    assert view["document_coverage"][2]["state"] == "NOT_FOUND"


def test_v9_candidates_are_exact_hashed_substrings() -> None:
    record = _record()
    view = build_v9_target_view(record)
    documents = {document.doc_id: document for document in record.documents}
    for candidate in view["candidates"]:
        document = documents[candidate.doc_id]
        assert document.text[candidate.start:candidate.end] == candidate.text
        assert hashlib.sha256(candidate.text.encode("utf-8")).hexdigest() == candidate.sha256


def test_v9_overlapping_surfaces_merge_without_semantic_classification() -> None:
    view = build_v9_target_view(_record())
    specification = next(
        candidate for candidate in view["candidates"] if candidate.doc_id == "D1"
    )
    assert "SEMANTIC_MARKER" in specification.trigger_kinds
    assert "MODEL_LIKE_TOKEN" in specification.trigger_kinds
    assert len([candidate for candidate in view["candidates"] if candidate.doc_id == "D1"]) == 1
    assert view["omission_policy"]["semantic_labeling"] is False


def test_v9_view_source_has_no_label_or_notice_specific_dependency() -> None:
    source = (Path(__file__).parents[1] / "src/pps_ai/views/v9_targets.py").read_text(
        encoding="utf-8"
    )
    assert "dev_labels" not in source
    assert "PPS-DEV" not in source
    assert "legacy" not in source
