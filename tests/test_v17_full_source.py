"""V17 phase-A task keeps product roles and source completeness separate."""

from __future__ import annotations

from src.pps_ai.domain.models import NoticeDocument, NoticeRecord
from src.pps_ai.views.v17_full_source import (
    build_v17_full_source_task, eligible_v17_full_source,
)


def _record(price: int, business: str) -> NoticeRecord:
    documents = (
        NoticeDocument.from_raw("n1", 0, {
            "doc_id": "D1", "type": "규격서", "text": "규격 본문 UNIQUE_SPEC 1234567890",
        }),
        NoticeDocument.from_raw("n1", 1, {
            "doc_id": "D0", "type": "공고문", "text": "참가자격 UNIQUE_NOTICE",
        }),
    )
    return NoticeRecord("n1", documents, {
        "입찰추정가격": price, "업무구분": business,
        "계약방법": "제한경쟁", "조항호내용": "입력 조항",
        "세부품명번호목록": None,
    }, {}, {}, {})


def test_v17_gate_uses_only_explicit_price_and_business_scope() -> None:
    assert eligible_v17_full_source(_record(99_999_999, "물품(내자)"))
    assert eligible_v17_full_source(_record(99_999_999, "일반용역"))
    assert not eligible_v17_full_source(_record(100_000_000, "일반용역"))
    assert not eligible_v17_full_source(_record(50_000_000, "공사"))


def test_v17_task_contains_every_document_and_role_uncertainty() -> None:
    record = _record(50_000_000, "물품(내자)")
    task = build_v17_full_source_task(record, "v17 독립 카드", {
        "1234567890": {"세부품명": "경쟁품", "특이사항": "특정 용도만 적용"},
    })
    system = task["messages"][0]["content"]
    user = task["messages"][1]["content"]
    documents = user.split("[모든 제공 문서 원문]", 1)[1]
    assert "G=실제 구매대상" in system
    assert "직접생산확인서" in system
    assert documents.index("UNIQUE_NOTICE") < documents.index("UNIQUE_SPEC")
    assert documents.count("UNIQUE_NOTICE") == documents.count("UNIQUE_SPEC") == 1
    assert "특정 용도만 적용" in user
    assert "구매대상인지 참가자격용인지 별도 확인" in user
    assert len(task["schema"]["required"]) == 4
