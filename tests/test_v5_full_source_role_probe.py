import pytest

from src.pps_ai.domain.models import NoticeDocument, NoticeRecord
from src.pps_ai.v5_full_source_role_probe import (
    _aggregate,
    build_role_tasks,
    parse_role_response,
)


class _CharacterCounter:
    def count(self, messages):
        return sum(len(message["content"]) for message in messages)


def _record(attachment_length: int) -> NoticeRecord:
    notice_id = "TEST"
    documents = (
        NoticeDocument.from_raw(notice_id, 0, {
            "doc_id": "D0", "type": "공고문", "text": "입찰 공고문\n참가자격 확인\n",
        }),
        NoticeDocument.from_raw(notice_id, 1, {
            "doc_id": "D1", "type": "과업지시서", "text": "기술 내용\n" + "가" * attachment_length,
        }),
    )
    return NoticeRecord(notice_id, documents, {"적용계약법": "국가계약법"}, {}, {}, {})


def test_overflow_role_tasks_cover_each_source_character_once() -> None:
    record = _record(3000)
    tasks, ledger = build_role_tasks(record, _CharacterCounter(), 1500)
    assert len(tasks) > 1
    assert all(row["tokens"] <= 1500 for row in ledger)
    by_doc = {document.doc_id: [] for document in record.documents}
    for row in ledger:
        for span in row["spans"]:
            by_doc[span["doc_id"]].append((span["start"], span["end"]))
    for document in record.documents:
        assert "".join(document.text[start:end] for start, end in sorted(by_doc[document.doc_id])) == document.text


def test_positive_quote_must_be_exact_current_source() -> None:
    task = {"source_texts": ["실제 참가자 본점 소재지"]}
    response = {"finish_reason": "stop", "invalid": False,
                "content": '{"role":"BIDDER_LOCATION","quote":"본점 소재지"}'}
    assert parse_role_response(response, task)["role"] == "BIDDER_LOCATION"
    response["content"] = '{"role":"BIDDER_LOCATION","quote":"[문서 D1]"}'
    with pytest.raises(ValueError, match="exact current source"):
        parse_role_response(response, task)


def test_malformed_part_does_not_turn_into_absence() -> None:
    assert _aggregate([{"valid": True, "role": "NOT_BIDDER_LOCATION"}, {"valid": False}]) == "UNCLEAR"
    assert _aggregate([{"valid": True, "role": "BIDDER_LOCATION"}, {"valid": False}]) == "BIDDER_LOCATION"
