from scripts.audit_dev_evidence_observability import audit
from src.schema import ITEMS


def test_gold_span_presence_does_not_infer_legal_label_validity():
    record = {"id": "x", "docs": [{"doc_id": "D0", "type": "공고문", "text": "가나 원문"}]}
    labels = {item: 0 for item in ITEMS}
    labels.update({"v9": 1, "e9": "가나", "v10": 1, "e10": "",
                   "v24": 1, "e24": ""})
    result = audit([record], {"x": labels}, {"fast": {"x"}, "holdout": set()})
    assert result["per_item"]["v9"]["status_counts"] == {"exact_source_span": 1}
    assert result["per_item"]["v10"]["status_counts"] == {"absence_evidence_exempt": 1}
    assert result["per_item"]["v24"]["status_counts"] == {"blank_nonabsence_evidence": 1}
    assert result["per_item"]["v9"]["panels"]["holdout"] == {}


def test_exact_evidence_must_fit_one_source_document_not_cross_document_join():
    record = {"id": "x", "docs": [
        {"doc_id": "D0", "type": "공고문", "text": "가"},
        {"doc_id": "D1", "type": "규격서", "text": "나"}]}
    labels = {item: 0 for item in ITEMS}
    labels.update({"v9": 1, "e9": "가나"})
    result = audit([record], {"x": labels}, {})
    assert result["per_item"]["v9"]["status_counts"] == {"no_exact_span": 1}
