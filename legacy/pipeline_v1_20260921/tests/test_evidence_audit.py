from src.evidence_audit import locate_evidence, paragraph_spans, spans_covering


def _record() -> dict:
    return {
        "id": "test-1",
        "docs": [
            {"doc_id": "D0", "type": "공고문", "text": "첫 문단\n계속 문장\n\n둘째 문단"},
            {"doc_id": "D1", "type": "규격서", "text": "모델 X를 납품한다"},
        ],
    }


def test_locate_evidence_keeps_exact_source_slice():
    location = locate_evidence(_record(), "모델 X를 납품한다")
    assert location is not None
    assert location.doc_id == "D1"
    assert location.match_mode == "exact"
    assert location.source_text == "모델 X를 납품한다"


def test_locate_evidence_allows_only_whitespace_shape_difference():
    location = locate_evidence(_record(), "첫 문단 계속 문장")
    assert location is not None
    assert location.match_mode == "whitespace_normalized"
    assert location.source_text == "첫 문단\n계속 문장"


def test_paragraph_spans_cover_multiline_evidence():
    location = locate_evidence(_record(), "첫 문단\n계속 문장")
    assert location is not None
    spans = paragraph_spans(_record())
    covered = spans_covering(location, spans)
    assert len(covered) == 1
    assert covered[0].text == "첫 문단\n계속 문장"
