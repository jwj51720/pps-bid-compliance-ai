import json

from src.context_budget import estimate_context_budget, pack_contexts_to_token_budget
from src.prompt import build_messages


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


def test_token_budget_packer_splits_long_document_and_keeps_all_text() -> None:
    record = {
        "id": "N1",
        "docs": [
            {"doc_id": "N", "type": "공고문", "text": "N" * 20},
            {"doc_id": "R", "type": "제안요청서", "text": "R" * 160},
        ],
        "meta": {},
        "dropped_doc_counts": {},
        "input_completeness": {},
        "anon_applied": False,
        "assembly_policy_version": "test",
    }

    def count_tokens(messages):
        return len(messages[-1]["content"].split("[문서]\n", 1)[1])

    contexts = pack_contexts_to_token_budget(
        record, "system", count_tokens, prompt_budget_tokens=100, notice_anchor_chars=10
    )

    assert len(contexts) > 1
    assert all(count_tokens([{"content": f"[문서]\n{context}"}]) <= 100 for context in contexts)
    assert sum(context.count("R") for context in contexts) >= 160


def test_fixed_reference_is_counted_for_every_split_pass() -> None:
    record = {
        "id": "N1",
        "docs": [
            {"doc_id": "N", "type": "공고문", "text": "N" * 20},
            {"doc_id": "R", "type": "제안요청서", "text": "R" * 160},
        ],
        "meta": {},
        "dropped_doc_counts": {},
        "input_completeness": {},
        "anon_applied": False,
        "assembly_policy_version": "test",
    }
    reference = "LAW" * 20
    system_prompt = "system\n" + reference

    def count_tokens(messages):
        return sum(len(message["content"]) for message in messages)

    contexts = pack_contexts_to_token_budget(
        record, system_prompt, count_tokens, prompt_budget_tokens=180, notice_anchor_chars=0
    )
    messages = [build_messages(record, system_prompt, None, document_context=context) for context in contexts]

    assert len(messages) > 1
    assert all(reference in value[0]["content"] for value in messages)
    assert all(count_tokens(value) <= 180 for value in messages)
