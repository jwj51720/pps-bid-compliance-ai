from __future__ import annotations

from src.pps_ai.domain.models import NoticeDocument, NoticeRecord
from src.pps_ai.v16_full_source_verifier import build_v16_tasks, parse_v16_response


class CharacterCounter:
    def count(self, messages):
        return sum(len(message["content"]) for message in messages)


def record(texts: list[str]) -> NoticeRecord:
    documents = tuple(
        NoticeDocument.from_raw("N1", index, {
            "doc_id": f"D{index}", "type": "공고문" if index == 0 else "규격서",
            "text": text,
        }) for index, text in enumerate(texts)
    )
    return NoticeRecord(
        notice_id="N1", documents=documents,
        metadata={
            "업무구분": "일반용역", "계약방법": "제한경쟁",
            "입찰추정가격": 150_000_000, "조항호내용": "특수한 기술이 요구되는 용역계약",
            "세부품명번호목록": None,
        },
        input_completeness={}, dropped_document_counts={},
        raw={"id": "N1", "docs": [], "meta": {}},
    )


def test_parse_v16_response_is_strict() -> None:
    assert parse_v16_response({"content": '{"v16":0}', "finish_reason": "stop"}) == 0


def test_observation_contract_reduces_only_explicit_contrary_fact() -> None:
    response = {
        "content": (
            '{"applicability":"APPLIES","qualification":"BIDDER_BROAD",'
            '"qualification_quote":"중소기업 확인서","exception":"NOT_FOUND",'
            '"exception_quote":""}'
        ),
        "finish_reason": "stop",
    }
    assert parse_v16_response(
        response,
        "metadata 중소기업 확인서\n[실제 공고 원문 — 이 pass의 연속 원문]\n원문 중소기업 확인서 문장",
        "v16-observation-v2",
    ) == 0


def test_observation_quote_cannot_come_from_metadata_section() -> None:
    response = {
        "content": (
            '{"applicability":"APPLIES","qualification":"BIDDER_BROAD",'
            '"qualification_quote":"메타 중소기업","exception":"NOT_FOUND",'
            '"exception_quote":""}'
        ),
        "finish_reason": "stop",
    }
    import pytest
    with pytest.raises(ValueError, match="actual rendered source"):
        parse_v16_response(
            response,
            "메타 중소기업\n[실제 공고 원문 — 이 pass의 연속 원문]\n실제 원문 없음",
            "v16-observation-v2",
        )


def test_overflow_tasks_cover_every_character_once() -> None:
    source = record(["가" * 800, "나" * 600])
    fixed_probe, _ = build_v16_tasks(source, "card", {}, CharacterCounter(), 5000)
    full_size = CharacterCounter().count(fixed_probe[0]["messages"])
    tasks, ledger = build_v16_tasks(source, "card", {}, CharacterCounter(), full_size - 500)
    assert len(tasks) > 1
    coverage = {}
    for part in ledger:
        for span in part["spans"]:
            coverage.setdefault(span["doc_id"], []).append((span["start"], span["end"]))
    assert sorted(coverage["D0"]) == [(0, 800)]
    assert sorted(coverage["D1"]) == [(0, 600)]
