from scripts.audit_complete_fact_admission import _metadata_marker, source_coverage_gaps


def test_human_readable_metadata_style_uses_line_marker() -> None:
    assert _metadata_marker("적용계약법", "official_lines_human_v2") == "- 적용계약법:"


def test_source_coverage_accepts_continuation_headers_without_losing_bytes():
    record = {
        "docs": [
            {"doc_id": "D0", "type": "공고문", "text": "abcdef"},
            {"doc_id": "D1", "type": "제안요청서", "text": "uvwxyz"},
        ]
    }
    contexts = [
        "[공고문:D0]\nabcdef\n\n[제안요청서:D1]\nuvw",
        "[제안요청서:D1] [계속 3]\nxyz",
    ]

    assert source_coverage_gaps(record, contexts) == []


def test_source_coverage_reports_a_gap_between_continuation_fragments():
    record = {"docs": [{"doc_id": "D0", "type": "공고문", "text": "abcdef"}]}
    contexts = ["[공고문:D0]\nabc", "[공고문:D0] [계속 4]\nef"]

    gaps = source_coverage_gaps(record, contexts)

    assert gaps == [{
        "doc_id": "D0",
        "type": "공고문",
        "expected_offset": 3,
        "observed_offset": 4,
        "payload_characters": 2,
    }]
