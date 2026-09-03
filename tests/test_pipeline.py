from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.context_budget import DocumentContext
from src.pipeline import (
    BaselinePipeline,
    PredictionError,
    _combine_pass_judgments,
    _merge_notice_judgments,
    _usage_number,
    parse_judgment,
    parse_pass_response,
    postprocess_judgment,
)
from src.prompt import (
    build_document_context,
    build_messages,
    build_split_document_contexts,
    build_system_prompt,
    format_competition_product_context,
    format_v24_comparison_context,
    normalize_notice_facts,
)
from src.schema import ITEMS, judgment_schema
from src.law_bundles import MetadataLawBundleRouter


def _record(text: str = "서울특별시에 본사를 둔 업체로 제한한다") -> dict:
    return {
        "id": "test-id",
        "docs": [{"doc_id": "D0", "type": "공고문", "text": text}],
        "meta": {},
        "dropped_doc_counts": {},
        "input_completeness": {"fully_observed": True},
        "anon_applied": True,
        "assembly_policy_version": "test",
    }


def _judgment() -> dict:
    return {item: {"위반여부": 0, "근거문구": None} for item in ITEMS}


def test_parse_judgment_requires_every_item() -> None:
    with pytest.raises(PredictionError, match="missing items"):
        parse_judgment('{"v1": {"위반여부": 0, "근거문구": null}}')


def test_group_schema_and_parser_require_only_requested_items() -> None:
    items = ("v2", "v3")
    payload = {item: {"위반여부": 0, "근거문구": None} for item in items}
    assert parse_judgment(json.dumps(payload), items) == payload
    assert judgment_schema(items=items)["required"] == ["v2", "v3"]


def test_labels_only_schema_parser_and_postprocess_have_no_evidence() -> None:
    items = ("v1", "v2")
    payload = {"v1": 1, "v2": 0}
    schema = judgment_schema(items=items, output_mode="labels_only")
    assert schema["properties"]["v1"] == {"type": "integer", "enum": [0, 1]}
    parsed = parse_judgment(json.dumps(payload), items, output_mode="labels_only")
    result = postprocess_judgment(parsed, _record(), items=items, output_mode="labels_only")
    assert result == {"v1": {"위반여부": 1, "근거문구": ""}, "v2": {"위반여부": 0, "근거문구": ""}}


def test_sparse_evidence_is_serialization_only_and_never_overrides_labels() -> None:
    items = ("v1", "v10")
    payload = {
        "판정": {"v1": 1, "v10": 1},
        "발췌": [{"항목": "v1", "근거문구": "서울특별시에 본사를 둔 업체"}],
        "부재검토": {"v10": "필수조건_확인"},
    }
    parsed = parse_judgment(
        json.dumps(payload, ensure_ascii=False), items, output_mode="labels_and_sparse_evidence"
    )
    assert parsed["v1"] == {"위반여부": 1, "근거문구": "서울특별시에 본사를 둔 업체"}
    # The review is audit information. It must not change the final label.
    assert parsed["v10"] == {"위반여부": 1, "근거문구": None}
    schema = judgment_schema(items=items, output_mode="labels_and_sparse_evidence")
    assert schema["required"] == ["판정", "발췌", "부재검토"]


def test_labels_only_messages_do_not_request_evidence_output() -> None:
    item_table = {"v1": {"항목명": "항목 1", "비고": ""}}
    prompt = build_system_prompt(item_table, active_items=("v1",), output_mode="labels_only")
    message = build_messages(_record(), prompt, None, output_mode="labels_only")[1]["content"]
    assert "근거문구" not in prompt
    assert "근거문구" not in message
    assert "인용" not in message
    assert "법적 요건을 모두 충족하는 명시적 제한·요구·불일치" in prompt
    assert "[부재탐지] 항목은 필요한 문구와 조건이 공고 자료 전체에 없을 때만 1" in prompt
    assert "메타데이터 값만으로 1을 정하지 말고" in message


def test_evidence_mode_keeps_plain_card_source_instruction() -> None:
    item_table = {"v1": {"항목명": "항목 1", "비고": ""}}
    cards = {"v1": {"item_name": "항목 1", "prompt_text": "1 조건: A. 0 조건: B."}}
    prompt = build_system_prompt(item_table, decision_cards=cards, active_items=("v1",))
    assert "근거문구는 언제나 공고/첨부문서 원문에서만 인용한다." in prompt


def test_metadata_law_router_uses_only_contract_metadata(tmp_path: Path) -> None:
    bundles = {}
    for profile in (
        "national_complete", "local_general_complete", "local_small_complete",
        "local_negotiated_complete", "local_small_negotiated_complete",
    ):
        path = tmp_path / f"{profile}.txt"
        text = f"reference for {profile}\n"
        path.write_text(text, encoding="utf-8")
        import hashlib
        bundles[profile] = {
            "path": str(path), "sha256": hashlib.sha256(text.encode()).hexdigest(), "chunks": [],
        }
    (tmp_path / "manifest.json").write_text(json.dumps({"bundles": bundles}), encoding="utf-8")
    router = MetadataLawBundleRouter(tmp_path)
    assert router.route({"id": "n", "meta": {"적용계약법": "국가계약법"}}).profile == "national_complete"
    assert router.route({"id": "s", "meta": {"적용계약법": "지방계약법", "계약방법": "수의계약"}}).profile == "local_small_complete"
    assert router.route({"id": "h", "meta": {"적용계약법": "지방계약법", "낙찰방법": "협상에의한계약"}}).profile == "local_negotiated_complete"


def test_parse_judgment_accepts_fenced_json() -> None:
    expected = _judgment()
    parsed = parse_judgment(f"```json\n{json.dumps(expected, ensure_ascii=False)}\n```")
    assert parsed == expected


def test_v8_composite_response_requires_closed_observation_states() -> None:
    payload = _judgment()
    payload["v8병합관찰"] = {"상태": "실적", "관찰근거문구": "실적 제한"}
    judgment, observation = parse_pass_response(json.dumps(payload, ensure_ascii=False), True)
    assert judgment == _judgment()
    assert observation["상태"] == "실적"


def test_finalize_defaults_only_an_invalid_pass_to_zero_and_records_it() -> None:
    class Completion:
        content = "not JSON"
        model = "test"
        latency_seconds = 0.0
        usage = {}
        finish_reason = "length"

    item_table = {
        item: {"항목명": item, "부재탐지": False, "국가계약법": "", "지방계약법": "", "비고": ""}
        for item in ITEMS
    }
    pipeline = BaselinePipeline(item_table=item_table, client=None, max_document_chars=None)

    prediction = pipeline.finalize(_record(), [Completion()])

    assert all(cell["위반여부"] == 0 for cell in prediction.judgment.values())
    assert prediction.parse_errors == (
        {"pass_index": 1, "error": "model response is not valid JSON", "raw_response": "not JSON"},
    )


def test_postprocess_keeps_only_exact_source_evidence() -> None:
    judgment = _judgment()
    judgment["v1"] = {"위반여부": 1, "근거문구": "서울특별시에 본사를 둔 업체"}
    judgment["v2"] = {"위반여부": 1, "근거문구": "서울 업체만 허용"}
    result = postprocess_judgment(judgment, _record())
    assert result["v1"]["근거문구"] == "서울특별시에 본사를 둔 업체"
    assert result["v2"]["근거문구"] == ""


def test_postprocess_blanks_absence_evidence() -> None:
    judgment = _judgment()
    judgment["v10"] = {"위반여부": 1, "근거문구": "서울특별시"}
    assert postprocess_judgment(judgment, _record())["v10"]["근거문구"] == ""


def test_postprocess_restores_original_whitespace_span() -> None:
    judgment = _judgment()
    judgment["v1"] = {"위반여부": 1, "근거문구": "대학 또는 산학협력단만 참여"}
    record = _record("대학 또는\n산학협력단만 참여 가능")
    evidence = postprocess_judgment(judgment, record)["v1"]["근거문구"]
    assert evidence == "대학 또는\n산학협력단만 참여"


def test_null_document_limit_keeps_all_documents_in_fixed_type_order() -> None:
    record = _record()
    record["docs"] = [
        {"doc_id": "D2", "type": "과업지시서", "text": "과업 전체"},
        {"doc_id": "D1", "type": "공고문", "text": "공고 전체"},
    ]

    context = build_document_context(record, None)

    assert "[절단]" not in context
    assert context.index("[공고문:D1]") < context.index("[과업지시서:D2]")
    assert "공고 전체" in context
    assert "과업 전체" in context


def test_structured_prompt_uses_full_item_table_without_reference_data() -> None:
    item_table = {
        item: {"항목명": item, "부재탐지": False, "국가계약법": "국가 참조", "지방계약법": "지방 참조", "비고": ""}
        for item in ITEMS
    }
    prompt = build_system_prompt(item_table, mode="structured")

    assert "국가계약법 참조: 국가 참조" in prompt
    assert "판정 원칙:" in prompt


def test_markdown_prompt_layout_changes_presentation_not_active_items() -> None:
    item_table = {
        item: {"항목명": item, "부재탐지": False, "국가계약법": "", "지방계약법": "", "비고": ""}
        for item in ITEMS
    }
    prompt = build_system_prompt(item_table, active_items=("v2", "v3"), layout="markdown")
    assert "# 역할" in prompt
    assert "# 판정 항목" in prompt
    assert "v2" in prompt and "v3" in prompt
    assert "- v1:" not in prompt


def test_markdown_user_message_separates_metadata_and_target_document() -> None:
    message = build_messages(
        _record(), "system", None, document_context="[공고문:D0]\n본문", markdown_sections=True
    )[1]["content"]
    assert "# 나라장터 입력 메타데이터" in message
    assert "# 공고 자료" in message
    assert "```json" in message
    assert "공고 ID" not in message
    assert "# 출력" in message


def test_markdown_v2_ends_with_exact_json_contract_after_references() -> None:
    item_table = {
        item: {"항목명": item, "부재탐지": False, "국가계약법": "", "지방계약법": "", "비고": ""}
        for item in ITEMS
    }
    prompt = build_system_prompt(
        item_table, active_items=("v1",), layout="markdown_v2", reference_text="법령 원문"
    )
    assert "# 판정 순서" in prompt
    assert "# 참고 법령·고시 — 판정 기준" in prompt
    assert prompt.rfind("# 출력 형식") > prompt.rfind("법령 원문")


def test_decision_card_conditions_are_rendered_as_separate_bullets() -> None:
    item_table = {"v1": {"항목명": "항목 1", "비고": ""}}
    cards = {
        "v1": {
            "item_name": "항목 1",
            "prompt_text": "적용 확인: A. 1 조건: B. 0 조건: C.",
        }
    }
    prompt = build_system_prompt(
        item_table, decision_cards=cards, active_items=("v1",), layout="markdown_v2"
    )
    assert "  - 적용 확인: A." in prompt
    assert "  - 1 조건: B." in prompt
    assert "  - 0 조건: C." in prompt
    assert "공식 참고자료 안내" not in prompt


def test_normalized_facts_only_restate_notice_metadata() -> None:
    meta = {"세부품명번호목록": "과일류[5030990101]", "입찰추정가격": 10}
    facts = normalize_notice_facts(meta)

    assert facts["세부품명번호"] == ["5030990101"]
    assert facts["추정가격원"] == 10


def test_competition_product_fact_is_visible_but_not_evidence() -> None:
    context = format_competition_product_context(
        _record(),
        {
            "status": "matched",
            "matched_products": [{"세부품명": "잡석"}],
        },
    )
    messages = build_messages(
        _record(),
        "system",
        None,
        competition_product_context=context,
    )
    content = messages[-1]["content"]
    assert "경쟁제품 고시 조회 결과" in content
    assert "v10·v11·v13" in content
    assert "잡석" in content
    assert "matched_codes" not in content


def test_competition_product_not_matched_context_hides_internal_codes() -> None:
    record = _record()
    record["meta"]["세부품명번호목록"] = "잡지[5510150601]"
    context = format_competition_product_context(
        record,
        {"status": "not_matched", "matched_products": []},
    )

    assert "잡지" in context
    assert "5510150601" not in context
    assert "not_matched" not in context


def test_unknown_product_lookup_is_not_rendered_as_a_negative_applicability_fact() -> None:
    context = format_competition_product_context(
        _record(), {"status": "unknown", "matched_products": []}, ("v10", "v16")
    )

    assert "비경쟁제품 또는 비적용이라는 판정이 아니라" in context
    assert "조회 불가만으로 0 또는 1을 정하지 말고" in context


def test_v24_checklist_restates_only_comparable_metadata_fields() -> None:
    record = _record()
    record["meta"] = {
        "배정예산금액": 100,
        "입찰추정가격": 90,
        "계약방법": "제한경쟁",
        "낙찰방법": "협상에의한계약",
        "지역제한여부": "Y",
        "제한지역코드목록": "서울",
        "업종제한여부": "N",
        "면허업종제한목록": "",
        "무관한필드": "노출되면 안 됨",
    }
    context = format_v24_comparison_context(record)

    assert "제한 문구가 존재한다는 사실만으로 불일치가 되지 않는다" in context
    assert "계약방법" in context
    assert "무관한필드" not in context


def test_product_context_is_omitted_for_an_unrelated_v_group() -> None:
    item_table = {
        item: {"항목명": item, "부재탐지": False, "국가계약법": "", "지방계약법": "", "비고": ""}
        for item in ITEMS
    }
    record = _record()
    record["meta"]["세부품명번호목록"] = "잡석[8014199001]"
    products = {"8014199001": {"세부품명": "잡석"}}

    unrelated = BaselinePipeline(
        item_table=item_table, client=None, max_document_chars=None,
        competition_products=products, active_items=("v1",),
    )
    relevant = BaselinePipeline(
        item_table=item_table, client=None, max_document_chars=None,
        competition_products=products, active_items=("v10",),
    )

    assert unrelated.competition_product_context_for_record(record) is None
    assert "v10" in (relevant.competition_product_context_for_record(record) or "")
    assert "v16" not in (relevant.competition_product_context_for_record(record) or "")


def test_split_contexts_preserve_order_anchor_and_long_document_text() -> None:
    record = _record()
    record["docs"] = [
        {"doc_id": "R1", "type": "제안요청서", "text": "R" * 80},
        {"doc_id": "N1", "type": "공고문", "text": "NOTICE" * 10},
        {"doc_id": "S1", "type": "규격서", "text": "SPEC" * 10},
    ]

    contexts = build_split_document_contexts(record, max_chars=70, notice_anchor_chars=12)

    assert len(contexts) > 1
    assert all("[공고문 앵커:N1]" in context for context in contexts)
    payload = "".join(context.replace("[공고문 앵커:N1]\nNOTICENOTICE", "") for context in contexts)
    assert "[공고문:N1]" in payload
    assert "[규격서:S1]" in payload
    assert "[제안요청서:R1]" in payload
    assert payload.index("[공고문:N1]") < payload.index("[규격서:S1]") < payload.index("[제안요청서:R1]")
    assert payload.count("R") >= 80


def test_combined_pass_judgments_ors_labels_and_keeps_first_positive_evidence() -> None:
    first = _judgment()
    second = _judgment()
    first["v1"] = {"위반여부": 1, "근거문구": "first"}
    second["v1"] = {"위반여부": 1, "근거문구": "second"}
    second["v2"] = {"위반여부": 1, "근거문구": "only second"}

    combined = _combine_pass_judgments([first, second])

    assert combined["v1"] == {"위반여부": 1, "근거문구": "first"}
    assert combined["v2"] == {"위반여부": 1, "근거문구": "only second"}
    assert combined["v3"] == {"위반여부": 0, "근거문구": ""}


def test_full_split_merge_requires_token_counter() -> None:
    item_table = {
        item: {"항목명": item, "부재탐지": False, "국가계약법": "", "지방계약법": "", "비고": ""}
        for item in ITEMS
    }
    pipeline = BaselinePipeline(
        item_table=item_table,
        client=None,
        max_document_chars=None,
        context_strategy="full_split_merge",
    )

    with pytest.raises(ValueError, match="exact tokenizer"):
        pipeline.contexts_for_record(_record())


def test_strict_document_evidence_rejects_anchor_only_positive() -> None:
    class Completion:
        model = "test"
        latency_seconds = 0.0
        usage = {}
        finish_reason = "stop"
        content = json.dumps(
            {
                **_judgment(),
                "v1": {"위반여부": 1, "근거문구": "앵커에만 있는 제한"},
            },
            ensure_ascii=False,
        )

    item_table = {
        item: {"항목명": item, "부재탐지": False, "국가계약법": "", "지방계약법": "", "비고": ""}
        for item in ITEMS
    }
    pipeline = BaselinePipeline(
        item_table=item_table,
        client=None,
        max_document_chars=None,
        context_strategy="full_split_merge",
        strict_document_evidence=True,
    )
    context = DocumentContext(
        text="[공고문 앵커:D0]\\n앵커에만 있는 제한\\n\\n[규격서:D1]\\n대상 문서",
        target_document_id="D1",
        target_document_type="규격서",
        target_text="대상 문서",
    )

    prediction = pipeline.finalize(_record(), [Completion()], [context])

    assert prediction.judgment["v1"] == {"위반여부": 0, "근거문구": ""}


def test_absence_items_use_and_while_other_items_use_or() -> None:
    first = _judgment()
    second = _judgment()
    first["v1"] = {"위반여부": 1, "근거문구": "first"}
    first["v10"] = {"위반여부": 1, "근거문구": ""}
    second["v10"] = {"위반여부": 0, "근거문구": ""}

    combined = _combine_pass_judgments([first, second], "per_pass_and")

    assert combined["v1"] == {"위반여부": 1, "근거문구": "first"}
    assert combined["v10"] == {"위반여부": 0, "근거문구": ""}


def test_v8_composite_merge_requires_both_document_local_facts() -> None:
    first = _judgment()
    observations = [
        {
            "doc_id": "D0",
            "document_type": "공고문",
            "상태": "실적",
            "관찰근거문구": "실적 제한",
        },
        {
            "doc_id": "D1",
            "document_type": "규격서",
            "상태": "지역",
            "관찰근거문구": "서울 소재 업체",
        },
    ]
    merged = _merge_notice_judgments(_record(), [first, _judgment()], observations, "per_pass_and", True)
    assert merged["v8"] == {"위반여부": 1, "근거문구": "실적 제한"}
    assert merged["v10"]["위반여부"] == 0


def test_v8_strict_conjunction_rejects_ordinary_or_positive() -> None:
    first = _judgment()
    first["v8"] = {"위반여부": 1, "근거문구": "실적 제한"}

    merged = _merge_notice_judgments(
        _record(), [first], [], "per_pass_and", True, "strict_conjunction"
    )

    assert merged["v8"] == {"위반여부": 0, "근거문구": ""}


def test_usage_number_accepts_nested_openrouter_cost() -> None:
    assert _usage_number({"cost": 0.0123}) == 0.0123
    assert _usage_number({"unexpected": "value"}) == 0.0
