"""The native full-input draft preserves every source before token admission."""

from __future__ import annotations

from src.pps_ai.domain.models import NoticeDocument, NoticeRecord
from src.pps_ai.facts.metadata import FIELD_LABELS
from src.pps_ai.views.native_full_prompt import ITEM_IDS, build_native_full_task


def test_full_task_contains_all_cards_metadata_products_and_ordered_docs() -> None:
    metadata = {field: None for field in FIELD_LABELS}
    metadata["세부품명번호목록"] = "물품[1234567890]"
    documents = (
        NoticeDocument.from_raw("n1", 0, {
            "doc_id": "D2", "type": "과업지시서", "text": "과업 원문 UNIQUE_TASK",
        }),
        NoticeDocument.from_raw("n1", 1, {
            "doc_id": "D0", "type": "공고문", "text": "공고 원문 UNIQUE_NOTICE",
        }),
        NoticeDocument.from_raw("n1", 2, {
            "doc_id": "D1", "type": "규격서", "text": "규격 원문 UNIQUE_SPEC",
        }),
    )
    record = NoticeRecord("n1", documents, metadata, {}, {}, {})
    cards = {item: f"{item} 독립 판정 계약" for item in ITEM_IDS}
    task = build_native_full_task(
        record, cards,
        {"1234567890": {"세부품명": "경쟁품", "특이사항": "조건부 적용"}},
    )
    user = task["messages"][1]["content"]
    assert all(f"{item} 독립 판정 계약" in user for item in ITEM_IDS)
    assert user.index("UNIQUE_NOTICE") < user.index("UNIQUE_SPEC") < user.index("UNIQUE_TASK")
    assert user.count("UNIQUE_NOTICE") == user.count("UNIQUE_SPEC") == user.count("UNIQUE_TASK") == 1
    assert "조건부 적용" in user
    assert "경쟁품" in user
    assert "세부품명번호목록" not in user
    assert "적용 불가" not in user
    assert len(task["schema"]["required"]) == 48
    assert task["schema"]["properties"]["e10"]["enum"] == [""]


def test_missing_card_fails_before_task_is_admitted() -> None:
    metadata = {field: None for field in FIELD_LABELS}
    metadata["세부품명번호목록"] = None
    document = NoticeDocument.from_raw("n1", 0, {
        "doc_id": "D0", "type": "공고문", "text": "공고 원문",
    })
    record = NoticeRecord("n1", (document,), metadata, {}, {}, {})
    try:
        build_native_full_task(record, {"v1": "카드"}, {})
    except ValueError as error:
        assert "all 24 cards" in str(error)
    else:
        raise AssertionError("missing cards were admitted")
