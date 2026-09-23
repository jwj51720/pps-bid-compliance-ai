from src.pps_ai.direct_attachment_coverage_audit import attachment_counterfactual


def test_attachment_counterfactual_preserves_source_record_and_provenance() -> None:
    record = {
        "id": "A", "meta": {},
        "docs": [
            {"doc_id": "D0", "type": "공고문", "text": "ordinary"},
            {"doc_id": "D1", "type": "규격서", "text": "target"},
        ],
    }

    def classify(value):
        hit = any(doc["type"] == "공고문" and doc["text"] == "target"
                  for doc in value["docs"])
        return {f"{item}_final": hit for item in ("v1", "v2", "v5", "v6", "v7", "v8")}

    original, attachments = attachment_counterfactual(record, classify)
    assert not original["v1"]
    assert len(attachments) == 1
    assert attachments[0]["type"] == "규격서"
    assert attachments[0]["doc_id"] == "D1"
    assert attachments[0]["flags"]["v1"]
    assert record["docs"][1]["type"] == "규격서"
