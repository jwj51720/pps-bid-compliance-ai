import json

from src.context_budget import estimate_context_budget


def test_estimates_full_document_prompt_against_reserved_output(tmp_path):
    item_table = {
        "항목": {
            f"v{index}": {"항목명": f"항목 {index}", "부재탐지": False, "비고": ""}
            for index in range(1, 25)
        }
    }
    item_path = tmp_path / "items.json"
    item_path.write_text(json.dumps(item_table), encoding="utf-8")
    record = {
        "id": "N1",
        "docs": [{"doc_id": "D1", "type": "공고문", "text": "가나다라마바사"}],
        "meta": {},
        "dropped_doc_counts": {},
        "input_completeness": {},
        "anon_applied": False,
        "assembly_policy_version": "test",
    }
    result = estimate_context_budget(
        records=[record],
        predictions=[{"id": "N1", "usage": {"prompt_tokens": 10}}],
        item_table_path=item_path,
        current_document_chars=2,
        max_model_len=100,
        output_reserve_tokens=20,
    )

    assert result["prompt_budget_tokens"] == 80
    assert result["record_count"] == 1
    assert result["records"][0]["full_prompt_characters"] > result["records"][0]["current_prompt_characters"]
