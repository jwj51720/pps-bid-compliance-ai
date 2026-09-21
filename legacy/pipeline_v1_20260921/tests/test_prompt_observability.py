from src.prompt_observability import audit_prompt_observability


def _record() -> dict:
    return {
        "id": "notice-1",
        "docs": [
            {"doc_id": "D0", "type": "공고문", "text": "A" * 50},
            {"doc_id": "D1", "type": "규격서", "text": "모델 X를 요구한다"},
        ],
        "meta": {},
        "dropped_doc_counts": {},
    }


def test_audit_marks_nonempty_evidence_outside_baseline_context() -> None:
    labels = {
        "notice-1": {
            **{f"v{index}": "0" for index in range(1, 25)},
            **{f"e{index}": "" for index in range(1, 25)},
        }
    }
    labels["notice-1"]["v9"] = "1"
    labels["notice-1"]["e9"] = "모델 X를 요구한다"
    report = audit_prompt_observability([_record()], labels, context_chars=40)
    row = report["rows"][0]
    assert row["observability"] == "source_outside_4k"
    assert row["source_document_type"] == "규격서"


def test_audit_marks_absence_positive_with_omitted_documents_as_scope_risk() -> None:
    labels = {
        "notice-1": {
            **{f"v{index}": "0" for index in range(1, 25)},
            **{f"e{index}": "" for index in range(1, 25)},
        }
    }
    labels["notice-1"]["v10"] = "1"
    report = audit_prompt_observability([_record()], labels, context_chars=40)
    assert report["rows"][0]["observability"] == "absence_requires_full_scope"
