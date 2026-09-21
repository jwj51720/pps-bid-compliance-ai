from src.dev_precedent_audit import (
    candidate_indexes_except_notice,
    source_valid_positive_candidates,
)


def _record(record_id: str, text: str) -> dict:
    return {
        "id": record_id,
        "docs": [{"doc_id": "D0", "type": "공고문", "text": text}],
        "meta": {},
    }


def test_source_valid_candidates_require_positive_exact_evidence() -> None:
    records = [_record("a", "실적증명서를 제출한다"), _record("b", "다른 문장")]
    labels = {
        "a": {"v1": "1", "e1": "실적증명서를 제출한다"},
        "b": {"v1": "1", "e1": "원문에 없음"},
    }
    candidates = source_valid_positive_candidates(records, labels)
    assert candidates == [{
        "notice_id": "a", "item": "v1", "evidence": "실적증명서를 제출한다",
        "document_type": "공고문",
    }]


def test_candidate_indexes_exclude_query_notice() -> None:
    candidates = [
        {"notice_id": "a", "item": "v1"},
        {"notice_id": "b", "item": "v1"},
        {"notice_id": "a", "item": "v2"},
    ]
    assert candidate_indexes_except_notice(candidates, "v1", "a") == [1]
