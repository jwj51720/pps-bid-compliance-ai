import json

from src.context_budget import (
    estimate_context_budget,
    pack_contexts_to_token_budget,
    pack_document_contexts_to_token_budget,
)
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
        record, "system", count_tokens, prompt_budget_tokens=200, notice_anchor_chars=10
    )

    assert len(contexts) > 1
    assert all(count_tokens([{"content": f"[문서]\n{context}"}]) <= 200 for context in contexts)
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
        record, system_prompt, count_tokens, prompt_budget_tokens=350, notice_anchor_chars=0
    )
    messages = [build_messages(record, system_prompt, None, document_context=context) for context in contexts]

    assert len(messages) > 1
    assert all(reference in value[0]["content"] for value in messages)
    assert all(count_tokens(value) <= 350 for value in messages)


def test_full_split_merge_keeps_one_target_document_per_pass_and_splits_long_one() -> None:
    record = {
        "id": "N1",
        "meta": {},
        "dropped_doc_counts": {},
        "docs": [
            {"doc_id": "A1", "type": "공고문", "text": "A" * 20},
            {"doc_id": "S1", "type": "규격서", "text": "S" * 100},
            {"doc_id": "R1", "type": "제안요청서", "text": "R" * 10},
        ],
    }

    def count_tokens(messages):
        return len(messages[-1]["content"])

    contexts = pack_document_contexts_to_token_budget(
        record,
        "system",
        count_tokens,
        prompt_budget_tokens=250,
        notice_anchor_chars=5,
    )

    assert len(contexts) == 4
    assert "[공고문:A1]" in contexts[0].text
    assert "[규격서:S1]" in contexts[1].text
    assert "[규격서:S1] [계속 " in contexts[2].text
    assert "[제안요청서:R1]" in contexts[3].text
    assert "[공고문 앵커:A1]" not in contexts[0].text
    assert "[공고문 앵커:A1]" in contexts[1].text
    assert contexts[1].target_text + contexts[2].target_text == "S" * 100
    assert all(count_tokens([{"content": context.text}]) <= 250 for context in contexts)


def test_full_split_budget_counts_product_context_in_every_pass() -> None:
    record = {
        "id": "N1",
        "meta": {},
        "dropped_doc_counts": {},
        "docs": [
            {"doc_id": "A1", "type": "공고문", "text": "A" * 80},
        ],
    }

    def count_tokens(messages):
        return sum(len(message["content"]) for message in messages)

    product_context = "대회 제공 경쟁제품 고시 조회 결과 " * 3
    contexts = pack_document_contexts_to_token_budget(
        record,
        "system",
        count_tokens,
        prompt_budget_tokens=300,
        competition_product_context=product_context,
    )
    messages = [
        build_messages(
            record,
            "system",
            None,
            document_context=context.text,
            competition_product_context=product_context,
        )
        for context in contexts
    ]

    assert len(contexts) > 1
    assert all(count_tokens(message) <= 300 for message in messages)
