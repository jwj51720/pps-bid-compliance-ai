import pytest

from src.pps_ai.domain.models import NoticeDocument, NoticeRecord
from src.pps_ai.v1_full_source_role_probe import SYSTEM, _task, parse_response
from src.pps_ai.v5_full_source_role_probe import build_role_tasks, _validate_coverage


class _CharacterCounter:
    def count(self, messages):
        return sum(len(message["content"]) for message in messages)


def _record():
    notice_id = "TEST"
    documents = (
        NoticeDocument.from_raw(notice_id, 0, {
            "doc_id": "D0", "type": "공고문", "text": "입찰 공고문\n대학만 참가 가능\n",
        }),
        NoticeDocument.from_raw(notice_id, 1, {
            "doc_id": "D1", "type": "제안요청서", "text": "업무 내용\n" + "가" * 3000,
        }),
    )
    return NoticeRecord(notice_id, documents, {"적용계약법": "국가계약법"}, {}, {}, {})


def test_v1_role_probe_covers_full_overflow_source() -> None:
    record = _record()
    tasks, ledger = build_role_tasks(record, _CharacterCounter(), 1500, task_factory=_task)
    assert len(tasks) > 1
    assert all(row["tokens"] <= 1500 for row in ledger)
    assert all(task["messages"][0]["content"] == SYSTEM for task in tasks)
    _validate_coverage(record, ledger)


def test_v1_role_probe_requires_actual_positive_source_quote() -> None:
    task = {"source_texts": ["대학만 참가 가능"]}
    response = {"finish_reason": "stop", "invalid": False,
                "content": '{"role":"EXCLUSIVE_BIDDER_ORGANIZATION","quote":"대학만 참가 가능"}'}
    assert parse_response(response, task)["role"] == "EXCLUSIVE_BIDDER_ORGANIZATION"
    response["content"] = '{"role":"EXCLUSIVE_BIDDER_ORGANIZATION","quote":"대학만 입찰 가능"}'
    with pytest.raises(ValueError, match="not recoverable"):
        parse_response(response, task)


def test_v1_role_probe_rejects_invalid_response() -> None:
    task = {"source_texts": ["대학만 참가 가능"]}
    response = {"finish_reason": "length", "invalid": True,
                "content": '{"role":"NOT_EXCLUSIVE","quote":""}'}
    with pytest.raises(ValueError, match="normally"):
        parse_response(response, task)
