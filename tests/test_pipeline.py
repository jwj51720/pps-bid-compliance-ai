from __future__ import annotations

import importlib.util
from pathlib import Path
import json

import pytest

from src.context_budget import DocumentContext, pack_contexts_to_token_budget
from src.external.openrouter import MockClient
from src.external.openrouter import Completion
from src.pipeline import (
    BaselinePipeline,
    ContextAdmissionError,
    PredictionError,
    _combine_pass_judgments,
    _merge_notice_judgments,
    _usage_number,
    collect_validated_fact_inventory,
    parse_judgment,
    parse_locator_response,
    parse_inventory_response,
    parse_fact_inventory_response,
    parse_procedure_fact_response,
    parse_timeline_fact_response,
    parse_v4_fact_first_response,
    parse_v4_specialist_fact_first_response,
    parse_v5_numeric_relation_response,
    parse_v6_geography_proof_response,
    parse_v19_role_proof_response,
    parse_v23_quantitative_proof_response,
    parse_v10_product_presence_response,
    parse_v12_product_target_response,
    parse_v13_product_scope_response,
    parse_category_fact_first_response,
    parse_v23_proof_judgment_response,
    parse_v24_fact_first_response,
    parse_pass_response,
    parse_triage_response,
    postprocess_judgment,
)
from src.prompt import (
    append_fact_inventory,
    append_locator_navigation,
    append_source_inventory,
    build_locator_system_prompt,
    build_triage_system_prompt,
    build_document_context,
    build_messages,
    build_official_baseline_context,
    build_split_document_contexts,
    build_source_only_fact_messages,
    build_system_prompt,
    format_official_baseline_meta,
    format_competition_product_context,
    format_organizer_input_semantics,
    format_v24_comparison_context,
    format_v24_role_pairs_context,
    normalize_notice_facts,
)
from src.schema import ITEMS, TRIAGE_STATES, category_fact_first_judgment_schema, judgment_schema, locator_schema, inventory_schema, triage_schema, v4_fact_first_judgment_schema, v4_specialist_fact_first_judgment_schema, v5_numeric_relation_judgment_schema, v6_geography_proof_judgment_schema, v10_product_presence_judgment_schema, v12_product_target_judgment_schema, v13_product_scope_judgment_schema, v19_role_proof_judgment_schema, v23_quantitative_proof_judgment_schema, v24_fact_first_judgment_schema
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


def test_shared_navigation_builder_preserves_exp171_message_contract() -> None:
    record = _record("[지역:r1|단위=기초|광역=경기도] 참가 업체")
    record["meta"] = {"적용계약법": "지방계약법"}
    pipeline = BaselinePipeline(
        item_table={item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS},
        client=MockClient(),
        max_document_chars=None,
        organizer_input_semantics_mode="anonymization_v1",
        metadata_style="official_lines",
        prompt_profile="complete_fact_v1",
    )
    system = "사실만 발췌"
    source, messages = pipeline.navigation_messages_for_context(
        record, None, system
    )
    expected = build_messages(
        record,
        system,
        pipeline.max_document_chars,
        document_context=source,
        organizer_input_semantics_context=format_organizer_input_semantics(
            record, "anonymization_v1"
        ),
        prompt_profile=pipeline.prompt_profile,
        metadata_style=pipeline.metadata_style,
        output_mode="labels_only",
    )

    assert messages == expected
    assert "[나라장터 입력 메타]" in messages[1]["content"]
    assert "[주최 측 입력 표기 규약]" in messages[1]["content"]


def test_parse_judgment_requires_every_item() -> None:
    with pytest.raises(PredictionError, match="missing items"):
        parse_judgment('{"v1": {"위반여부": 0, "근거문구": null}}')


def test_v24_fact_first_schema_and_parser_put_review_before_final_judgment() -> None:
    schema = v24_fact_first_judgment_schema()
    assert schema["required"] == ["v24대조", "판정"]
    payload = {
        "v24대조": [{
            "필드": "예산", "원문값": "예산금액 100원",
            "메타값": "배정예산금액: 200원", "관계": "양립불가능",
        }],
        "판정": _judgment(),
    }
    judgment, reviews = parse_v24_fact_first_response(
        json.dumps(payload, ensure_ascii=False)
    )
    assert judgment["v24"]["위반여부"] == 0
    assert reviews[0]["관계"] == "양립불가능"


def test_v4_fact_first_schema_parser_and_source_validation() -> None:
    schema = v4_fact_first_judgment_schema()
    assert schema["required"] == ["v4검토", "판정"]
    payload = {
        "v4검토": {
            "참가자격실적근거": "국가기관 발주 실적만 인정",
            "금액구간": "고시금액이상",
            "특정발주기관한정": "있음",
            "특정실적종류한정": "없음",
            "구체적필요사유": "없음",
            "카드대조": "1조건충족",
        },
        "판정": _judgment(),
    }
    parsed, review = parse_v4_fact_first_response(json.dumps(payload, ensure_ascii=False))
    assert parsed == _judgment()
    assert review["카드대조"] == "1조건충족"

    class Client:
        def complete(self, messages, response_schema):
            return Completion(
                content=json.dumps(payload, ensure_ascii=False), model="test",
                latency_seconds=0.0, usage={}, finish_reason="stop",
            )

    pipeline = BaselinePipeline(
        item_table={item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS},
        client=Client(), max_document_chars=None,
        prompt_mode="v4_fact_first_relation_v1", prompt_profile="complete_fact_v1",
    )
    prediction = pipeline.predict(_record("국가기관 발주 실적만 인정"))
    assert prediction.v4_fact_reviews[0]["원문검증됨"] is True
    assert prediction.v4_fact_reviews[0]["검증원문값"] == "국가기관 발주 실적만 인정"


def test_v4_fact_first_keeps_relation_checklist_after_source() -> None:
    pipeline = BaselinePipeline(
        item_table={item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS},
        client=MockClient(), max_document_chars=None,
        prompt_mode="v4_fact_first_relation_v1", prompt_profile="complete_fact_v1",
    )
    system, user = (
        message["content"] for message in pipeline.messages_for_context(
            _record("마지막 원문 문장"), None
        )
    )
    assert "`v4검토`" in system
    assert user.index("마지막 원문 문장") < user.index("[판정 직전 관계 체크리스트]")
    assert user.index("[판정 직전 관계 체크리스트]") < user.index("[v4 출력 전 확인]")
    assert pipeline.response_schema == v4_fact_first_judgment_schema()


def test_v4_specialist_fact_first_is_role_aware_and_does_not_override_label() -> None:
    payload = {
        "v4역할검토": {
            "실적요구원문": "실적증명서는 해당 기관 발급분만 인정",
            "조항역할": "증빙서류_행정",
            "과거계약실적요구": "없음",
            "발주기관범위": "발주기관제한없음",
            "실적종류범위": "실적제한아님",
            "유사동등실적인정": "불명",
            "구체적필요사유": "없음",
            "카드대조": "0조건충족",
        },
        "판정": {"v4": {"위반여부": 1, "근거문구": "실적증명서는 해당 기관 발급분만 인정"}},
    }
    parsed, review = parse_v4_specialist_fact_first_response(
        json.dumps(payload, ensure_ascii=False)
    )
    assert parsed["v4"]["위반여부"] == 1
    assert review["조항역할"] == "증빙서류_행정"

    class Client:
        def complete(self, messages, response_schema):
            return Completion(
                content=json.dumps(payload, ensure_ascii=False), model="test",
                latency_seconds=0.0, usage={}, finish_reason="stop",
            )

    pipeline = BaselinePipeline(
        item_table={item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS},
        client=Client(), max_document_chars=None,
        prompt_mode="v4_specialist_fact_first_v1",
        prompt_profile="complete_fact_subset_v1", active_items=("v4",),
    )
    prediction = pipeline.predict(_record("실적증명서는 해당 기관 발급분만 인정"))
    assert prediction.judgment["v4"]["위반여부"] == 1
    assert prediction.v4_fact_reviews[0]["원문검증됨"] is True
    system, user = (
        message["content"] for message in pipeline.messages_for_context(
            _record("마지막 원문 문장"), None
        )
    )
    assert "`v4역할검토`" in system
    assert "[판정 직전 관계 체크리스트]" not in user
    assert user.index("마지막 원문 문장") < user.index("[v4 출력 전 역할 검증]")
    assert pipeline.response_schema == v4_specialist_fact_first_judgment_schema()


def test_v4_specialist_fact_first_rejects_non_v4_active_items() -> None:
    with pytest.raises(ValueError, match="requires v4-only"):
        BaselinePipeline(
            item_table={item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS},
            client=MockClient(), max_document_chars=None,
            prompt_mode="v4_specialist_fact_first_v1",
            prompt_profile="complete_fact_subset_v1", active_items=("v3", "v4"),
        )


def test_v5_numeric_relation_is_observable_and_does_not_override_label() -> None:
    payload = {
        "v5수치대조": {
            "적용분기": "공기업준정부기관",
            "입찰추정가격": 100_000_000,
            "적용임계값": 710_000_000,
            "금액관계": "미만",
            "지역문구역할": "참가자격",
            "허용사유": "없음",
        },
        "판정": {
            "v5": {"위반여부": 1, "근거문구": "본점 소재지가 서울인 업체"}
        },
    }
    parsed, review = parse_v5_numeric_relation_response(
        json.dumps(payload, ensure_ascii=False)
    )
    assert review["금액관계"] == "미만"
    assert parsed["v5"]["위반여부"] == 1

    class Client:
        def complete(self, messages, response_schema):
            return Completion(
                content=json.dumps(payload, ensure_ascii=False), model="test",
                latency_seconds=0.0, usage={}, finish_reason="stop",
            )

    pipeline = BaselinePipeline(
        item_table={item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS},
        client=Client(), max_document_chars=None,
        prompt_mode="v5_numeric_relation_v1",
        prompt_profile="complete_fact_subset_v1", active_items=("v5",),
    )
    prediction = pipeline.predict(_record("본점 소재지가 서울인 업체"))
    assert prediction.judgment["v5"]["위반여부"] == 1
    assert prediction.v5_numeric_reviews[0]["금액관계"] == "미만"
    system, user = (
        message["content"] for message in pipeline.messages_for_context(
            _record("마지막 원문 문장"), None
        )
    )
    assert "`v5수치대조`" in system
    assert user.index("마지막 원문 문장") < user.index("[v5 출력 전 수치·역할 검증]")
    assert pipeline.response_schema == v5_numeric_relation_judgment_schema()


def test_v5_numeric_relation_rejects_non_v5_or_labels_only() -> None:
    item_table = {
        item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS
    }
    with pytest.raises(ValueError, match="requires v5-only V/E"):
        BaselinePipeline(
            item_table=item_table, client=MockClient(), max_document_chars=None,
            prompt_mode="v5_numeric_relation_v1",
            prompt_profile="complete_fact_subset_v1", active_items=("v4", "v5"),
        )
    with pytest.raises(ValueError, match="requires v5-only V/E"):
        BaselinePipeline(
            item_table=item_table, client=MockClient(), max_document_chars=None,
            prompt_mode="v5_numeric_relation_v1", output_mode="labels_only",
            prompt_profile="complete_fact_subset_v1", active_items=("v5",),
        )


def test_v6_geography_proof_is_observable_and_does_not_override_label() -> None:
    excerpt = "본점 소재지를 경기도 [지역:r1|단위=기초|광역=경기도] 또는 제주도에 둔 업체"
    payload = {
        "v6지역대조": {
            "금액구간": "고시금액미만",
            "지역참가자격원문": excerpt,
            "지역문구역할": "참가자격",
            "기초지역참가제한": "포함",
            "계약절차": "제한경쟁",
            "허용요건": "불충족",
            "카드대조": "1조건충족",
        },
        "판정": {"v6": {"위반여부": 0, "근거문구": None}},
    }
    parsed, review = parse_v6_geography_proof_response(
        json.dumps(payload, ensure_ascii=False)
    )
    assert review["기초지역참가제한"] == "포함"
    assert parsed["v6"]["위반여부"] == 0

    class Client:
        def complete(self, messages, response_schema):
            return Completion(
                content=json.dumps(payload, ensure_ascii=False), model="test",
                latency_seconds=0.0, usage={}, finish_reason="stop",
            )

    pipeline = BaselinePipeline(
        item_table={item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS},
        client=Client(), max_document_chars=None,
        prompt_mode="v6_geography_proof_v1",
        prompt_profile="complete_fact_subset_v1", active_items=("v6",),
    )
    prediction = pipeline.predict(_record(excerpt))
    assert prediction.judgment["v6"]["위반여부"] == 0
    assert prediction.v6_geography_reviews[0]["원문검증됨"]
    system, user = (
        message["content"] for message in pipeline.messages_for_context(
            _record("마지막 원문 문장"), None
        )
    )
    assert "`v6지역대조`" in system
    assert user.index("마지막 원문 문장") < user.index("[v6 출력 전 지역관계 검증]")
    assert pipeline.response_schema == v6_geography_proof_judgment_schema()


def test_v6_geography_proof_rejects_non_v6_or_labels_only() -> None:
    item_table = {
        item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS
    }
    with pytest.raises(ValueError, match="requires v6-only V/E"):
        BaselinePipeline(
            item_table=item_table, client=MockClient(), max_document_chars=None,
            prompt_mode="v6_geography_proof_v1",
            prompt_profile="complete_fact_subset_v1", active_items=("v5", "v6"),
        )
    with pytest.raises(ValueError, match="requires v6-only V/E"):
        BaselinePipeline(
            item_table=item_table, client=MockClient(), max_document_chars=None,
            prompt_mode="v6_geography_proof_v1", output_mode="labels_only",
            prompt_profile="complete_fact_subset_v1", active_items=("v6",),
        )


def test_v6_geography_proof_mock_is_schema_valid() -> None:
    schema = v6_geography_proof_judgment_schema()
    completion = MockClient().complete([], schema)
    parsed, review = parse_v6_geography_proof_response(completion.content)

    assert review["카드대조"] == "판단불가"
    assert parsed["v6"]["위반여부"] == 0


@pytest.mark.parametrize("output_mode", ["labels_and_evidence", "labels_only"])
def test_v23_quantitative_proof_is_observable_and_model_owned(output_mode: str) -> None:
    announcement = "공고일: 2026. 1. 1. 제안서 제출마감: 2026. 1. 8."
    decision = (
        {"v23": 0}
        if output_mode == "labels_only"
        else {"v23": {"위반여부": 0, "근거문구": None}}
    )
    payload = {
        "v23기간대조": {
            "적용계약법": "지방계약", "계약방식": "협상",
            "입찰추정가격": 90000000, "금액구간": "1억미만",
            "적용최소일수": 10, "공고일근거": "공고일: 2026. 1. 1.",
            "종료일근거": "제안서 제출마감: 2026. 1. 8.",
            "종료일역할": "제안서마감", "계산일수": 7,
            "긴급재공고": "해당없음", "카드대조": "1조건충족",
        },
        "판정": decision,
    }
    parsed, review = parse_v23_quantitative_proof_response(
        json.dumps(payload, ensure_ascii=False), output_mode
    )
    assert review["계산일수"] == 7
    assert parsed["v23"]["위반여부"] == 0

    class Client:
        def complete(self, messages, response_schema):
            return Completion(
                content=json.dumps(payload, ensure_ascii=False), model="test",
                latency_seconds=0.0, usage={}, finish_reason="stop",
            )

    pipeline = BaselinePipeline(
        item_table={item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS},
        client=Client(), max_document_chars=None,
        prompt_mode="v23_quantitative_proof_v1", output_mode=output_mode,
        prompt_profile="complete_fact_subset_v1", active_items=("v23",),
    )
    prediction = pipeline.predict(_record(announcement))
    review = prediction.v23_quantitative_reviews[0]
    assert review["공고일근거_원문검증됨"]
    assert review["종료일근거_원문검증됨"]
    system, user = (
        message["content"] for message in pipeline.messages_for_context(
            _record(announcement), None
        )
    )
    assert "`v23기간대조`" in system
    assert user.index(announcement) < user.index("[v23 출력 전 기간관계 검증]")
    assert pipeline.response_schema == v23_quantitative_proof_judgment_schema(output_mode)


def test_v23_quantitative_proof_requires_v23_only() -> None:
    item_table = {
        item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS
    }
    with pytest.raises(ValueError, match="requires v23-only"):
        BaselinePipeline(
            item_table=item_table, client=MockClient(), max_document_chars=None,
            prompt_mode="v23_quantitative_proof_v1",
            prompt_profile="complete_fact_subset_v1", active_items=("v22", "v23"),
        )


@pytest.mark.parametrize("output_mode", ["labels_and_evidence", "labels_only"])
def test_v23_quantitative_proof_mock_is_schema_valid(output_mode: str) -> None:
    schema = v23_quantitative_proof_judgment_schema(output_mode)
    completion = MockClient().complete([], schema)
    parsed, review = parse_v23_quantitative_proof_response(completion.content, output_mode)

    assert review["카드대조"] == "판단불가"
    assert parsed["v23"]["위반여부"] == 0


@pytest.mark.parametrize("output_mode", ["labels_and_evidence", "labels_only"])
def test_v19_role_proof_is_observable_and_model_owned(output_mode: str) -> None:
    excerpt = "공급업체는 제조사의 A/S확약서를 입찰 전일까지 보유하여야 합니다."
    decision = (
        {"v19": 1}
        if output_mode == "labels_only"
        else {"v19": {"위반여부": 1, "근거문구": excerpt}}
    )
    payload = {
        "v19역할대조": {
            "후보원문": excerpt,
            "서류종류": "물품공급·기술지원확약서",
            "요구행위": "발급·보유",
            "기준시점": "입찰·제안전",
            "입찰효과": "필수제출",
            "카드대조": "1조건충족",
        },
        "판정": decision,
    }
    parsed, review = parse_v19_role_proof_response(
        json.dumps(payload, ensure_ascii=False), output_mode
    )
    assert parsed["v19"]["위반여부"] == 1
    assert review["기준시점"] == "입찰·제안전"

    class Client:
        def complete(self, messages, response_schema):
            return Completion(
                content=json.dumps(payload, ensure_ascii=False), model="test",
                latency_seconds=0.0, usage={}, finish_reason="stop",
            )

    pipeline = BaselinePipeline(
        item_table={item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS},
        client=Client(), max_document_chars=None,
        prompt_mode="v19_role_proof_v1", output_mode=output_mode,
        prompt_profile="complete_fact_subset_v1", active_items=("v19",),
    )
    prediction = pipeline.predict(_record(excerpt))
    review = prediction.v19_role_reviews[0]
    assert review["원문검증됨"]
    assert prediction.judgment["v19"]["위반여부"] == 1
    assert prediction.judgment["v19"]["근거문구"] == excerpt
    system, user = (
        message["content"] for message in pipeline.messages_for_context(
            _record(excerpt), None
        )
    )
    assert "`v19역할대조`" in system
    assert user.index(excerpt) < user.index("[v19 출력 전 역할·시점 검증]")
    assert pipeline.response_schema == v19_role_proof_judgment_schema(output_mode)


def test_v19_role_proof_requires_v19_only() -> None:
    item_table = {
        item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS
    }
    with pytest.raises(ValueError, match="requires v19-only"):
        BaselinePipeline(
            item_table=item_table, client=MockClient(), max_document_chars=None,
            prompt_mode="v19_role_proof_v1",
            prompt_profile="complete_fact_subset_v1", active_items=("v18", "v19"),
        )


@pytest.mark.parametrize("output_mode", ["labels_and_evidence", "labels_only"])
def test_v19_role_proof_mock_is_schema_valid(output_mode: str) -> None:
    schema = v19_role_proof_judgment_schema(output_mode)
    completion = MockClient().complete([], schema)
    parsed, review = parse_v19_role_proof_response(completion.content, output_mode)

    assert review["카드대조"] == "판단불가"
    assert parsed["v19"]["위반여부"] == 0


def test_v10_product_review_is_observable_and_does_not_override_label() -> None:
    payload = {
        "v10제품검토": {
            "실제구매대상": "행사대행 용역",
            "고시후보세부품명": "기타행사기획및대행서비스",
            "적용조건상태": "충족",
            "경쟁제품적용": "적용",
            "직접생산요구": "없음",
            "직접생산요구원문": None,
        },
        "판정": {"v10": 0},
    }
    parsed, review = parse_v10_product_presence_response(
        json.dumps(payload, ensure_ascii=False)
    )
    assert review["경쟁제품적용"] == "적용"
    assert review["직접생산요구"] == "없음"
    assert parsed["v10"]["위반여부"] == 0

    class Client:
        def complete(self, messages, response_schema):
            return Completion(
                content=json.dumps(payload, ensure_ascii=False), model="test",
                latency_seconds=0.0, usage={}, finish_reason="stop",
            )

    pipeline = BaselinePipeline(
        item_table={item: {"항목명": item, "부재탐지": item == "v10", "비고": ""} for item in ITEMS},
        client=Client(), max_document_chars=None,
        prompt_mode="v10_product_presence_review_v1", output_mode="labels_only",
        prompt_profile="complete_fact_subset_v1", active_items=("v10",),
    )
    prediction = pipeline.predict(_record("직접생산 요구가 없는 마지막 원문"))
    assert prediction.judgment["v10"]["위반여부"] == 0
    assert prediction.v10_product_reviews[0]["경쟁제품적용"] == "적용"
    system, user = (
        message["content"] for message in pipeline.messages_for_context(
            _record("마지막 원문 문장"), None
        )
    )
    assert "`v10제품검토`" in system
    assert "제공되지 않은 전체 목록을 추정하지 않는다" in system
    assert "exact-code 확인 결과 또는 대회 제공 전체 목록" not in system
    assert user.index("마지막 원문 문장") < user.index("[v10 출력 전 제품 적용·부재 검증]")
    assert pipeline.response_schema == v10_product_presence_judgment_schema()


def test_v10_product_review_full_catalog_prompt_names_catalog() -> None:
    pipeline = BaselinePipeline(
        item_table={
            item: {"항목명": item, "부재탐지": item == "v10", "비고": ""}
            for item in ITEMS
        },
        client=MockClient(), max_document_chars=None,
        prompt_mode="v10_product_presence_review_v1", output_mode="labels_only",
        prompt_profile="complete_fact_subset_v1", active_items=("v10",),
        competition_product_context_mode="full_catalog_v1",
    )

    assert "exact-code 확인 결과 또는 대회 제공 전체 목록" in pipeline.system_prompt
    assert "제공되지 않은 전체 목록을 추정하지 않는다" not in pipeline.system_prompt


def test_v10_product_review_requires_v10_only_vonly() -> None:
    item_table = {
        item: {"항목명": item, "부재탐지": item == "v10", "비고": ""}
        for item in ITEMS
    }
    with pytest.raises(ValueError, match="requires v10-only V-only"):
        BaselinePipeline(
            item_table=item_table, client=MockClient(), max_document_chars=None,
            prompt_mode="v10_product_presence_review_v1",
            prompt_profile="complete_fact_subset_v1", active_items=("v10",),
        )


@pytest.mark.parametrize("output_mode", ["labels_and_evidence", "labels_only"])
def test_v12_product_target_review_is_grounded_and_model_owned(output_mode: str) -> None:
    target = "공 고 명: 위탁연구과제 용역"
    requirement = "직접생산확인증명서를 소지한 업체여야 합니다."
    decision = (
        0 if output_mode == "labels_only"
        else {"위반여부": 0, "근거문구": None}
    )
    payload = {
        "v12제품대상검토": {
            "실제구매대상원문": target,
            "고시후보세부품명": "기타행사기획및대행서비스",
            "고시후보출처": "공고자료",
            "구매대상관계": "다른대상",
            "적용조건상태": "충족",
            "경쟁제품적용": "비적용",
            "직접생산요구원문": requirement,
            "직접생산요구역할": "참가자격",
            "허용사유": "없음",
            "카드대조": "1조건충족",
        },
        "판정": {"v12": decision},
    }
    parsed, review = parse_v12_product_target_response(
        json.dumps(payload, ensure_ascii=False), output_mode
    )
    assert review["구매대상관계"] == "다른대상"
    assert parsed["v12"]["위반여부"] == 0

    class Client:
        def complete(self, messages, response_schema):
            return Completion(
                content=json.dumps(payload, ensure_ascii=False), model="test",
                latency_seconds=0.0, usage={}, finish_reason="stop",
            )

    pipeline = BaselinePipeline(
        item_table={item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS},
        client=Client(), max_document_chars=None,
        prompt_mode="v12_product_target_review_v1",
        prompt_profile="complete_fact_subset_v1", active_items=("v12",),
        output_mode=output_mode,
    )
    prediction = pipeline.predict(_record(target + "\n" + requirement + "\n마지막 원문"))
    assert prediction.judgment["v12"]["위반여부"] == 0
    assert prediction.v12_product_reviews[0]["실제구매대상원문_원문검증됨"] is True
    assert prediction.v12_product_reviews[0]["직접생산요구원문_원문검증됨"] is True
    system, user = (
        message["content"] for message in pipeline.messages_for_context(
            _record(target + "\n" + requirement + "\n마지막 원문"), None
        )
    )
    assert "`v12제품대상검토`" in system
    assert user.index("마지막 원문") < user.index("[v12 출력 전 제품·대상 관계 검증]")
    assert pipeline.response_schema == v12_product_target_judgment_schema(output_mode)


def test_v12_product_target_review_requires_v12_only() -> None:
    item_table = {
        item: {"항목명": item, "부재탐지": False, "비고": ""}
        for item in ITEMS
    }
    with pytest.raises(ValueError, match="requires v12-only"):
        BaselinePipeline(
            item_table=item_table, client=MockClient(), max_document_chars=None,
            prompt_mode="v12_product_target_review_v1",
            prompt_profile="complete_fact_subset_v1", active_items=("v11", "v12"),
        )


@pytest.mark.parametrize("output_mode", ["labels_and_evidence", "labels_only"])
def test_v12_product_target_mock_is_schema_valid(output_mode: str) -> None:
    schema = v12_product_target_judgment_schema(output_mode)
    completion = MockClient().complete([], schema)
    parsed, review = parse_v12_product_target_response(completion.content, output_mode)

    assert parsed["v12"]["위반여부"] == 0
    assert review["카드대조"] == "판단불가"


def test_v13_product_scope_review_is_observable_and_model_owned() -> None:
    excerpt = "소기업·소상공인 확인서를 소지한 업체만 참가할 수 있습니다."
    payload = {
        "v13제품기업검토": {
            "실제구매대상": "행사대행 용역",
            "고시후보세부품명": "기타행사기획및대행서비스",
            "적용조건상태": "충족",
            "경쟁제품적용": "적용",
            "기업제한원문": excerpt,
            "기업제한역할": "참가자격",
            "일반중기업참가": "불가",
            "허용사유": "없음",
            "카드대조": "1조건충족",
        },
        "판정": {"v13": {"위반여부": 0, "근거문구": None}},
    }
    parsed, review = parse_v13_product_scope_response(
        json.dumps(payload, ensure_ascii=False)
    )
    assert review["카드대조"] == "1조건충족"
    assert parsed["v13"]["위반여부"] == 0

    class Client:
        def complete(self, messages, response_schema):
            return Completion(
                content=json.dumps(payload, ensure_ascii=False), model="test",
                latency_seconds=0.0, usage={}, finish_reason="stop",
            )

    pipeline = BaselinePipeline(
        item_table={item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS},
        client=Client(), max_document_chars=None,
        prompt_mode="v13_product_scope_review_v1",
        prompt_profile="complete_fact_subset_v1", active_items=("v13",),
        output_mode="labels_and_evidence",
    )
    prediction = pipeline.predict(_record(excerpt + "\n마지막 원문 문장"))
    assert prediction.judgment["v13"]["위반여부"] == 0
    assert prediction.v13_product_reviews[0]["원문검증됨"] is True
    system, user = (
        message["content"] for message in pipeline.messages_for_context(
            _record(excerpt + "\n마지막 원문 문장"), None
        )
    )
    assert "`v13제품기업검토`" in system
    assert user.index("마지막 원문 문장") < user.index("[v13 출력 전 제품 적용·기업범위 검증]")
    assert pipeline.response_schema == v13_product_scope_judgment_schema()


def test_v13_product_scope_review_requires_v13_only_ve() -> None:
    item_table = {
        item: {"항목명": item, "부재탐지": False, "비고": ""}
        for item in ITEMS
    }
    with pytest.raises(ValueError, match="requires v13-only V/E"):
        BaselinePipeline(
            item_table=item_table, client=MockClient(), max_document_chars=None,
            prompt_mode="v13_product_scope_review_v1", output_mode="labels_only",
            prompt_profile="complete_fact_subset_v1", active_items=("v13",),
        )
    with pytest.raises(ValueError, match="requires v13-only V/E"):
        BaselinePipeline(
            item_table=item_table, client=MockClient(), max_document_chars=None,
            prompt_mode="v13_product_scope_review_v1",
            prompt_profile="complete_fact_subset_v1", active_items=("v12", "v13"),
        )


def test_v13_product_scope_mock_is_schema_valid() -> None:
    schema = v13_product_scope_judgment_schema()
    completion = MockClient().complete([], schema)

    parsed, review = parse_v13_product_scope_response(completion.content)

    assert parsed["v13"]["위반여부"] == 0
    assert review["카드대조"] == "판단불가"


def test_category_fact_first_schema_parser_and_prompt_order() -> None:
    categories = (
        "참가자격_실적_지역", "제품_기업_직접생산", "규격_모델_기술요구",
        "제출서류_확약서", "계약방식_공동계약", "일정_설명회", "금액_메타대조",
    )
    schema = category_fact_first_judgment_schema()
    assert schema["required"] == ["사실목록", "판정"]
    payload = {
        "사실목록": {category: [] for category in categories},
        "판정": _judgment(),
    }
    payload["사실목록"]["참가자격_실적_지역"] = ["서울 지역 업체로 제한"]
    parsed, facts = parse_category_fact_first_response(
        json.dumps(payload, ensure_ascii=False)
    )
    assert parsed == _judgment()
    assert facts["참가자격_실적_지역"] == ["서울 지역 업체로 제한"]

    class Client:
        def complete(self, messages, response_schema):
            return Completion(
                content=json.dumps(payload, ensure_ascii=False), model="test",
                latency_seconds=0.0, usage={}, finish_reason="stop",
            )

    pipeline = BaselinePipeline(
        item_table={item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS},
        client=Client(), max_document_chars=None,
        prompt_mode="category_fact_first_relation_v1",
        prompt_profile="complete_fact_v1",
    )
    messages = pipeline.messages_for_context(_record("서울 지역 업체로 제한"), None)
    assert messages[1]["content"].index("서울 지역 업체로 제한") < messages[1]["content"].index("[판정 직전 관계 체크리스트]")
    assert messages[1]["content"].index("[판정 직전 관계 체크리스트]") < messages[1]["content"].index("[출력 전 원문 사실 정리]")
    prediction = pipeline.predict(_record("서울 지역 업체로 제한"))
    review = prediction.category_fact_reviews[0]["범주"]["참가자격_실적_지역"][0]
    assert review["원문검증됨"] is True
    assert review["검증원문값"] == "서울 지역 업체로 제한"
    assert prediction.judgment["v1"]["위반여부"] == 0


def test_v24_fact_review_is_audited_but_never_overrides_label() -> None:
    record = _record("예산금액 100원")
    pipeline = BaselinePipeline(
        item_table={item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS},
        client=MockClient(), max_document_chars=None,
        prompt_mode="v24_fact_first_v1", prompt_profile="complete_fact_v1",
    )
    payload = {
        "v24대조": [{
            "필드": "예산", "원문값": "예산금액 100원",
            "메타값": "배정예산금액: 200원", "관계": "양립불가능",
        }],
        "판정": _judgment(),
    }
    completion = Completion(
        content=json.dumps(payload, ensure_ascii=False), model="mock",
        latency_seconds=0.0, usage={},
    )
    prediction = pipeline.finalize(record, [completion], [None])
    assert prediction.judgment["v24"]["위반여부"] == 0
    assert prediction.v24_fact_reviews[0]["원문검증됨"] is True
    assert prediction.v24_fact_reviews[0]["검증원문값"] == "예산금액 100원"


def test_v24_role_pairs_separate_competition_and_award_methods() -> None:
    record = _record("입찰방법: 제한경쟁, 낙찰방법: 협상에 의한 계약")
    record["meta"] = {
        "배정예산금액": 100,
        "입찰추정가격": 90,
        "계약방법": "제한경쟁",
        "낙찰방법": "협상에의한계약",
        "지역제한여부": "N",
        "제한지역코드목록": None,
        "업종제한여부": "N",
        "면허업종제한목록": None,
    }
    context = format_v24_role_pairs_context(record)
    pipeline = BaselinePipeline(
        item_table={item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS},
        client=MockClient(), max_document_chars=None,
        prompt_mode="v24_role_pairs_v1", prompt_profile="complete_fact_v1",
    )
    messages = pipeline.messages_for_context(record, None)
    system, user = messages[0]["content"], messages[1]["content"]

    assert "경쟁 범주는 계약방법" in system
    assert "낙찰자 결정 방식은 낙찰방법" in system
    assert "납품·사업·설명회 장소는 지역제한이 아니다" in system
    assert "[v24 역할별 나라장터 값]" in user
    assert context in user
    assert user.index("[v24 역할별 나라장터 값]") < user.index("[공고 자료 원문]")


def test_baseline_complete_fact_does_not_silently_gain_v24_role_context() -> None:
    record = _record()
    record["meta"] = {"계약방법": "제한경쟁"}
    pipeline = BaselinePipeline(
        item_table={item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS},
        client=MockClient(), max_document_chars=None,
        prompt_mode="baseline", prompt_profile="complete_fact_v1",
    )
    messages = pipeline.messages_for_context(record, None)
    assert "[v24 역할별 대조]" not in messages[0]["content"]
    assert "[v24 역할별 나라장터 값]" not in messages[1]["content"]


def test_relation_checklist_is_after_complete_source_without_schema_change() -> None:
    record = _record("마지막 원문 문장")
    pipeline = BaselinePipeline(
        item_table={item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS},
        client=MockClient(), max_document_chars=None,
        prompt_mode="relation_checklist_after_source_v1",
        prompt_profile="complete_fact_v1",
    )
    user = pipeline.messages_for_context(record, None)[1]["content"]

    assert user.index("마지막 원문 문장") < user.index("[판정 직전 관계 체크리스트]")
    assert "v8: 실적제한과 지역제한이 같은 입찰자" in user
    assert "v23: 공고일·설명회·제안서마감·가격입찰마감" in user
    assert pipeline.response_schema == judgment_schema()


def test_relation_checklist_labels_only_has_no_ve_output_conflict() -> None:
    record = _record("마지막 원문 문장")
    pipeline = BaselinePipeline(
        item_table={item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS},
        client=MockClient(), max_document_chars=None,
        prompt_mode="relation_checklist_after_source_v1",
        prompt_profile="complete_fact_v1", output_mode="labels_only",
    )
    system, user = (
        message["content"] for message in pipeline.messages_for_context(record, None)
    )

    assert "최종 위반여부 V만 출력한다" in user
    assert "최종 V/E를 출력한다" not in user
    assert "근거문구" not in system
    assert pipeline.response_schema == judgment_schema(output_mode="labels_only")


def test_decision_protocol_preserves_ve_schema_and_follows_complete_source() -> None:
    record = _record("마지막 원문 문장")
    pipeline = BaselinePipeline(
        item_table={item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS},
        client=MockClient(), max_document_chars=None,
        prompt_mode="decision_protocol_after_source_v1",
        prompt_profile="complete_fact_v1",
    )
    system, user = (
        message["content"] for message in pipeline.messages_for_context(record, None)
    )

    assert "[구조적 판정 모드]" in system
    assert user.index("마지막 원문 문장") < user.index("[판정 직전 실행 절차")
    assert "부재라서 인용문이 없고 근거문구가 null이라는 이유로 0" in user
    assert "실제 구매대상과 exact-code 고시 후보의 적용조건" in user
    assert "v4: 특정 발주기관·실적종류 제한" in user
    assert "v7: 참가자의 허용 지역 집합" in user
    assert "v22: 행사가 입찰 전 설명회인지" in user
    assert pipeline.response_schema == judgment_schema()


def test_exact_card_recap_repeats_same_catalog_after_complete_source() -> None:
    record = _record("마지막 원문 문장")
    cards = {
        item: {"prompt_text": f"{item} exact 적용범위와 1/0 조건"}
        for item in ITEMS
    }
    pipeline = BaselinePipeline(
        item_table={item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS},
        client=MockClient(), max_document_chars=None,
        prompt_mode="exact_card_recap_after_source_v1",
        prompt_profile="complete_fact_v1",
        decision_cards=cards,
    )
    system, user = (
        message["content"] for message in pipeline.messages_for_context(record, None)
    )

    assert "[exact 카드 재대조 모드]" in system
    assert user.index("마지막 원문 문장") < user.index("[판정 직전 exact 카드 재대조]")
    for item in ITEMS:
        card = f"{item} exact 적용범위와 1/0 조건"
        assert system.count(card) == 1
        assert user.count(card) == 1
    assert pipeline.response_schema == judgment_schema()


def test_inventory_contract_is_non_final_and_requires_every_active_item() -> None:
    items = ("v1", "v10")
    schema = inventory_schema(items)
    assert schema["properties"]["v10"]["type"] == ["string", "null"]
    assert parse_inventory_response('{"v1": "실제 제한 문구", "v10": null}', items) == {
        "v1": "실제 제한 문구", "v10": None,
    }
    with pytest.raises(PredictionError):
        parse_inventory_response('{"v1": null}', items)


def test_source_inventory_says_missing_candidate_is_not_a_final_zero() -> None:
    messages = append_source_inventory(
        [{"role": "system", "content": "system"}, {"role": "user", "content": "source"}],
        {"v1": [("D0", "실제 원문")]}, {"v10": "각 문서 묶음에서 관련 필수문구를 발견하지 못함 (최종 판정 아님)"},
        ("v1", "v10"),
    )
    content = messages[1]["content"]
    assert "[D0] 실제 원문" in content
    assert "후보가 없어도 0이 아니다" in content
    assert "최종 판정 아님" in content


def test_organizer_anonymization_semantics_are_friendly_and_non_decisive() -> None:
    context = format_organizer_input_semantics(_record(), "anonymization_v1")

    assert context is not None
    assert "`단위=기초`가 기초자치단체 계층" in context
    assert "`r1`과 `r2`는 서로 다른 지역" in context
    assert "숨겨진 실제 지역명은 추정하지 않는다" in context
    assert "표기의 존재 자체는 위반이 아니다" in context
    assert "위반여부" not in context


def test_organizer_anonymization_semantics_off_and_non_anonymous_are_empty() -> None:
    record = _record()
    assert format_organizer_input_semantics(record, "off") is None
    record["anon_applied"] = False
    assert format_organizer_input_semantics(record, "anonymization_v1") is None


def test_organizer_semantics_reach_final_and_source_only_messages() -> None:
    context = format_organizer_input_semantics(_record(), "anonymization_v1")
    final = build_messages(
        _record(),
        "system",
        None,
        organizer_input_semantics_context=context,
        prompt_profile="complete_fact_v1",
        metadata_style="official_lines",
    )
    source_only = build_source_only_fact_messages("system", "원문", context)

    for messages in (final, source_only):
        assert "[주최 측 입력 표기 규약]" in messages[1]["content"]
        assert messages[1]["content"].count("[주최 측 입력 표기 규약]") == 1
    assert final[1]["content"].index("[주최 측 입력 표기 규약]") < final[1]["content"].index("[공고 자료 원문]")
    assert source_only[1]["content"].index("[주최 측 입력 표기 규약]") < source_only[1]["content"].index("[공고 자료 원문]")


def test_parse_judgment_recovers_only_missing_outer_closure() -> None:
    items = ("v1", "v2")
    payload = {item: {"위반여부": 0, "근거문구": None} for item in items}
    complete = json.dumps(payload, ensure_ascii=False)
    truncated_outer_closure = complete[:-1] + "   \n\t"
    assert parse_judgment(truncated_outer_closure, items) == payload

    with pytest.raises(PredictionError):
        parse_judgment(complete[:-10], items)


def test_group_schema_and_parser_require_only_requested_items() -> None:
    items = ("v2", "v3")
    payload = {item: {"위반여부": 0, "근거문구": None} for item in items}
    assert parse_judgment(json.dumps(payload), items) == payload
    assert judgment_schema(items=items)["required"] == ["v2", "v3"]


def test_triage_schema_and_prompt_are_non_final_routing_contracts() -> None:
    item_table = {
        "v1": {"항목명": "항목 1", "부재탐지": False, "비고": ""},
        "v10": {"항목명": "항목 10", "부재탐지": True, "비고": ""},
    }
    cards = {
        "v1": {"item_name": "항목 1", "prompt_text": "1 조건: A. 0 조건: B."},
        "v10": {"item_name": "항목 10", "prompt_text": "부재탐지: C."},
    }
    prompt = build_triage_system_prompt(item_table, cards, ("v1", "v10"))
    schema = triage_schema(("v1", "v10"))
    assert "최종 0/1 판정도, 근거문구 추출도 아니다" in prompt
    assert "v10: 항목 10  [근거 없음]" in prompt
    assert "판정 카드: 1 조건: A. 0 조건: B." in prompt
    assert schema["properties"]["v1"]["enum"] == list(TRIAGE_STATES)


def test_triage_parser_rejects_missing_or_unknown_route_keys() -> None:
    assert parse_triage_response('{"v1": "해당없음"}', ("v1",)) == {"v1": "해당없음"}
    with pytest.raises(PredictionError, match="keys mismatch"):
        parse_triage_response('{"v1": "해당없음", "v2": "해당없음"}', ("v1",))


def test_locator_schema_parser_and_navigation_are_non_final() -> None:
    items = ("v1", "v2")
    assert locator_schema(items)["properties"]["v1"]["type"] == ["string", "null"]
    assert parse_locator_response('{"v1": null, "v2": "실제 제한 문구"}', items) == {
        "v1": None, "v2": "실제 제한 문구"
    }
    with pytest.raises(PredictionError, match="keys mismatch"):
        parse_locator_response('{"v1": null}', items)
    messages = append_locator_navigation(
        [{"role": "system", "content": "s"}, {"role": "user", "content": "notice"}],
        {"v1": "", "v2": "실제 제한 문구"}, items,
    )
    assert "`찾지 못함`을 0으로 해석하지 않는다" in messages[-1]["content"]
    assert "위반·무위반" in messages[-1]["content"]


def test_locator_then_final_keeps_all_items_in_final_stage() -> None:
    item_table = {
        item: {
            "항목명": item,
            "부재탐지": item in {"v10", "v11", "v16", "v18", "v20"},
            "국가계약법": "",
            "지방계약법": "",
            "비고": "",
        }
        for item in ITEMS
    }
    pipeline = BaselinePipeline(
        item_table=item_table,
        client=MockClient(),
        max_document_chars=4000,
        context_strategy="single",
        overflow_split_enabled=False,
        prompt_profile="official_baseline_v1",
        output_mode="labels_and_evidence",
    )

    prediction = pipeline.predict_with_locator_then_final(_record())

    assert set(prediction.locator_snippets) == set(ITEMS) - {"v10", "v11", "v16", "v18", "v20"}
    assert all(not value for value in prediction.locator_snippets.values())
    assert set(prediction.final.judgment) == set(ITEMS)
    assert "위반 여부 판정도" in prediction.locator_messages[0]["content"]
    assert "`찾지 못함`을 0으로 해석하지 않는다" in prediction.final_messages[-1]["content"]


def test_vonly_draft_full_final_keeps_ve_final_owner() -> None:
    item_table = {
        item: {
            "항목명": item,
            "부재탐지": item in {"v10", "v11", "v16", "v18", "v20"},
            "국가계약법": "",
            "지방계약법": "",
            "비고": "",
        }
        for item in ITEMS
    }
    pipeline = BaselinePipeline(
        item_table=item_table,
        client=MockClient(),
        max_document_chars=4000,
        context_strategy="single",
        overflow_split_enabled=False,
        count_tokens=lambda messages: len(messages),
        prompt_profile="official_baseline_v1",
        output_mode="labels_and_evidence",
    )

    prediction = pipeline.predict_with_vonly_draft_then_full_final(_record())

    assert prediction.draft_available
    assert set(prediction.draft.judgment) == set(ITEMS)
    assert all(cell["근거문구"] in {None, ""} for cell in prediction.draft.judgment.values())
    assert set(prediction.final.judgment) == set(ITEMS)
    assert "1차 검토 초안" in prediction.final_messages_by_context[0][1]["content"]
    assert not prediction.final_recovery_used


def test_vonly_draft_full_final_supports_one_item_without_python_vote() -> None:
    item_table = {
        item: {"항목명": item, "부재탐지": False, "국가계약법": "", "지방계약법": "", "비고": ""}
        for item in ITEMS
    }
    pipeline = BaselinePipeline(
        item_table=item_table, client=MockClient(), max_document_chars=None,
        context_strategy="single", overflow_split_enabled=True,
        count_tokens=lambda messages: len(messages),
        prompt_profile="complete_fact_subset_v1", active_items=("v4",),
        output_mode="labels_and_evidence",
    )
    prediction = pipeline.predict_with_vonly_draft_then_full_final(_record())
    assert set(prediction.draft.pass_judgments[0]) == {"v4"}
    assert set(prediction.final.pass_judgments[0]) == {"v4"}
    assert "초안의 0 또는 1을 따르거나 인용하지 말고" in (
        prediction.final_messages_by_context[0][1]["content"]
    )
    assert "지정 항목(v4)을 다시 판단" in (
        prediction.final_messages_by_context[0][1]["content"]
    )


def test_vonly_draft_full_final_supports_v10_vonly_final_owner() -> None:
    item_table = {
        item: {
            "항목명": item, "부재탐지": item == "v10",
            "국가계약법": "", "지방계약법": "", "비고": "",
        }
        for item in ITEMS
    }
    pipeline = BaselinePipeline(
        item_table=item_table, client=MockClient(), max_document_chars=None,
        prompt_mode="v10_product_presence_review_v1",
        context_strategy="single", overflow_split_enabled=True,
        count_tokens=lambda messages: len(messages),
        prompt_profile="complete_fact_subset_v1", active_items=("v10",),
        output_mode="labels_only",
    )

    prediction = pipeline.predict_with_vonly_draft_then_full_final(_record())

    assert set(prediction.draft.pass_judgments[0]) == {"v10"}
    assert set(prediction.final.pass_judgments[0]) == {"v10"}
    assert prediction.final.judgment["v10"]["근거문구"] == ""
    assert "1차 검토 초안" in prediction.final_messages_by_context[0][1]["content"]


def test_vonly_consensus_uses_model_owned_resolver_not_python_vote() -> None:
    item_table = {
        item: {"항목명": item, "부재탐지": False, "국가계약법": "", "지방계약법": "", "비고": ""}
        for item in ITEMS
    }
    pipeline = BaselinePipeline(
        item_table=item_table, client=MockClient(), max_document_chars=4000,
        context_strategy="single", overflow_split_enabled=False,
        count_tokens=lambda messages: len(messages), prompt_profile="official_baseline_v1",
        output_mode="labels_only",
    )
    prediction = pipeline.predict_with_vonly_consensus(_record())
    assert len(prediction.drafts) == 2
    assert set(prediction.final.judgment) == set(ITEMS)
    assert "독립초안 1" in prediction.final_messages_by_context[0][1]["content"]
    assert "다수결" in prediction.final_messages_by_context[0][1]["content"]


def test_vonly_consensus_does_not_apply_parent_frozen_rule() -> None:
    item_table = {
        item: {"항목명": item, "부재탐지": False, "국가계약법": "", "지방계약법": "", "비고": ""}
        for item in ITEMS
    }
    record = _record("단일 실적 3억원 이상인 업체")
    record["meta"] = {"입찰추정가격": "100000000", "업무구분": "용역"}
    pipeline = BaselinePipeline(
        item_table=item_table, client=MockClient(), max_document_chars=4000,
        context_strategy="single", overflow_split_enabled=False,
        count_tokens=lambda messages: len(messages), prompt_profile="official_baseline_v1",
        output_mode="labels_only", frozen_rule_set="exp123_v1",
    )

    prediction = pipeline.predict_with_vonly_consensus(record)

    assert prediction.final.judgment["v2"] == {"위반여부": 0, "근거문구": ""}


def test_frozen_postprocess_preserves_model_judgment_and_exact_change_audit() -> None:
    item_table = {
        item: {"항목명": item, "부재탐지": False, "국가계약법": "", "지방계약법": "", "비고": ""}
        for item in ITEMS
    }
    record = _record("실적 3억원 이상인 업체만 참가할 수 있다")
    record["meta"] = {"입찰추정가격": 100_000_000, "업무구분": "용역"}
    pipeline = BaselinePipeline(
        item_table=item_table,
        client=MockClient(),
        max_document_chars=4000,
        context_strategy="single",
        overflow_split_enabled=False,
        prompt_profile="official_baseline_v1",
        frozen_rule_set="exp123_v1",
    )

    prediction = pipeline.predict(record)

    assert prediction.model_judgment is not None
    assert prediction.model_judgment["v2"]["위반여부"] == 0
    assert prediction.judgment["v2"] == {
        "위반여부": 1,
        "근거문구": "실적 3억원 이상인 업체만 참가할 수 있다",
    }
    assert prediction.postprocess_policy == "exp123_v1"
    assert [change["item"] for change in prediction.postprocess_changes] == ["v2"]
    assert prediction.postprocess_changes[0]["before"]["위반여부"] == 0
    assert prediction.postprocess_changes[0]["after"]["위반여부"] == 1
    assert prediction.postprocess_changes[0]["label_changed"] is True
    assert prediction.postprocess_changes[0]["evidence_changed"] is True


def test_rule_free_prediction_has_model_owned_final_and_empty_change_audit() -> None:
    item_table = {
        item: {"항목명": item, "부재탐지": False, "국가계약법": "", "지방계약법": "", "비고": ""}
        for item in ITEMS
    }
    pipeline = BaselinePipeline(
        item_table=item_table,
        client=MockClient(),
        max_document_chars=4000,
        context_strategy="single",
        overflow_split_enabled=False,
        prompt_profile="official_baseline_v1",
        frozen_rule_set=None,
    )

    prediction = pipeline.predict(_record())

    assert prediction.model_judgment == prediction.judgment
    assert prediction.postprocess_policy is None
    assert prediction.postprocess_changes == ()


def test_item_navigation_keeps_source_candidate_advisory_and_full_final() -> None:
    class ItemFactClient:
        def complete(self, messages, response_schema):
            if response_schema["properties"]["v1"].get("type") == ["string", "null"]:
                payload = {item: None for item in ITEMS}
                payload["v1"] = "서울특별시에 본사를 둔 업체로 제한한다"
            else:
                payload = _judgment()
            return Completion(json.dumps(payload, ensure_ascii=False), "test", 0.0, {})

    item_table = {
        item: {"항목명": item, "부재탐지": False, "국가계약법": "", "지방계약법": "", "비고": ""}
        for item in ITEMS
    }
    pipeline = BaselinePipeline(
        item_table=item_table, client=ItemFactClient(), max_document_chars=None,
        context_strategy="single", overflow_split_enabled=True,
        count_tokens=lambda messages: len(messages), prompt_profile="complete_fact_v1",
    )
    prediction = pipeline.predict_with_fact_inventory_then_full_final(
        _record(), item_navigation=True,
    )
    assert prediction.item_navigation
    assert prediction.inventory_by_category["v1"] == (("D0", "서울특별시에 본사를 둔 업체로 제한한다"),)
    rendered = "\n".join(message["content"] for message in prediction.final_messages_by_context[0])
    assert "후보없음 (이는 0이 아님)" in rendered
    assert "서울특별시에 본사를 둔 업체로 제한한다" in rendered


def test_v6_geography_navigation_is_source_only_and_final_keeps_full_source() -> None:
    from src.schema import V6_GEOGRAPHY_FACT_FIELDS

    source_clause = "서울특별시 [지역:r1|단위=기초] 또는 제주도에 본점을 둔 업체"

    class GeographyFactClient:
        def __init__(self):
            self.calls = []

        def complete(self, messages, response_schema):
            self.calls.append(messages)
            if tuple(response_schema.get("required", ())) == V6_GEOGRAPHY_FACT_FIELDS:
                payload = {field: [] for field in V6_GEOGRAPHY_FACT_FIELDS}
                payload["참가자격_지역문구"] = [source_clause]
            else:
                payload = {
                    "v6": {"위반여부": 1, "근거문구": source_clause}
                }
            return Completion(json.dumps(payload, ensure_ascii=False), "test", 0.0, {})

    item_table = {
        "v6": {
            "항목명": "고시금액 미만 지역제한 시,군,구",
            "부재탐지": False,
            "국가계약법": "",
            "지방계약법": "",
            "비고": "",
        }
    }
    client = GeographyFactClient()
    record = _record(source_clause)
    pipeline = BaselinePipeline(
        item_table=item_table,
        client=client,
        max_document_chars=None,
        context_strategy="single",
        overflow_split_enabled=True,
        count_tokens=lambda messages: len(str(messages)),
        prompt_profile="complete_fact_subset_v1",
        active_items=("v6",),
        decision_cards={
            "v6": {
                "item_name": "고시금액 미만 지역제한 시,군,구",
                "prompt_text": "판정 카드 원문",
            }
        },
        organizer_input_semantics_mode="anonymization_v1",
    )

    prediction = pipeline.predict_with_fact_inventory_then_full_final(
        record,
        inventory_categories=V6_GEOGRAPHY_FACT_FIELDS,
        source_only_inventory=True,
    )

    assert prediction.inventory_by_category["참가자격_지역문구"] == (
        ("D0", source_clause),
    )
    stage_rendered = "\n".join(message["content"] for message in client.calls[0])
    assert "[나라장터 입력 메타]" not in stage_rendered
    assert "판정 카드 원문" not in stage_rendered
    assert "v6" not in stage_rendered
    final_rendered = "\n".join(
        message["content"] for message in prediction.final_messages_by_context[0]
    )
    assert "판정 카드 원문" in final_rendered
    assert source_clause in final_rendered
    assert "최종 판정 아님" in final_rendered
    assert prediction.final.judgment["v6"]["위반여부"] == 1


def test_fact_inventory_final_parse_retry_keeps_same_source_first_messages() -> None:
    from src.schema import FACT_INVENTORY_CATEGORIES

    class MalformedOnceClient:
        def __init__(self):
            self.calls = []

        def complete(self, messages, response_schema):
            self.calls.append(messages)
            if tuple(response_schema.get("required", ())) == FACT_INVENTORY_CATEGORIES:
                payload = {category: [] for category in FACT_INVENTORY_CATEGORIES}
                content = json.dumps(payload, ensure_ascii=False)
            elif len(self.calls) == 2:
                content = "malformed"
            else:
                payload = _judgment()
                payload["v1"] = {
                    "위반여부": 1,
                    "근거문구": "서울특별시에 본사를 둔 업체로 제한한다",
                }
                content = json.dumps(payload, ensure_ascii=False)
            return Completion(content, "test", 0.0, {})

    client = MalformedOnceClient()
    pipeline = BaselinePipeline(
        item_table={item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS},
        client=client,
        max_document_chars=None,
        context_strategy="single",
        overflow_split_enabled=True,
        count_tokens=lambda messages: len(messages),
        prompt_profile="complete_fact_v1",
    )

    prediction = pipeline.predict_with_fact_inventory_then_full_final(_record())

    assert prediction.final_recovery_used
    assert prediction.final_retry_count == 1
    assert prediction.inventory_retry_count == 0
    assert not prediction.final.parse_errors
    assert prediction.final.judgment["v1"]["위반여부"] == 1
    assert client.calls[2] == client.calls[1]
    assert "최종 판정 아님" in client.calls[2][-1]["content"]


def test_fact_inventory_parse_retry_keeps_same_navigation_message() -> None:
    from src.schema import FACT_INVENTORY_CATEGORIES

    class MalformedInventoryOnceClient:
        def __init__(self):
            self.calls = []

        def complete(self, messages, response_schema):
            self.calls.append(messages)
            if len(self.calls) == 1:
                content = "malformed"
            elif tuple(response_schema.get("required", ())) == FACT_INVENTORY_CATEGORIES:
                payload = {category: [] for category in FACT_INVENTORY_CATEGORIES}
                content = json.dumps(payload, ensure_ascii=False)
            else:
                content = json.dumps(_judgment(), ensure_ascii=False)
            return Completion(content, "test", 0.0, {})

    client = MalformedInventoryOnceClient()
    pipeline = BaselinePipeline(
        item_table={item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS},
        client=client,
        max_document_chars=None,
        context_strategy="single",
        overflow_split_enabled=True,
        count_tokens=lambda messages: len(messages),
        prompt_profile="complete_fact_v1",
    )

    prediction = pipeline.predict_with_fact_inventory_then_full_final(_record())

    assert prediction.inventory_retry_count == 1
    assert prediction.inventory_parse_errors == ()
    assert client.calls[1] == client.calls[0]
    assert not prediction.final_recovery_used


def test_triage_then_strict_routes_absence_items_even_when_triage_says_not_applicable() -> None:
    item_table = {
        item: {
            "항목명": item,
            "부재탐지": item in {"v10", "v11", "v16", "v18", "v20"},
            "국가계약법": "",
            "지방계약법": "",
            "비고": "",
        }
        for item in ITEMS
    }
    pipeline = BaselinePipeline(
        item_table=item_table,
        client=MockClient(),
        max_document_chars=4000,
        context_strategy="single",
        overflow_split_enabled=False,
        prompt_profile="official_baseline_v1",
        output_mode="labels_and_evidence",
    )

    prediction = pipeline.predict_with_triage_then_strict(_record())

    assert prediction.triage_states["v1"] == "해당없음"
    assert prediction.strict_items == ("v10", "v11", "v16", "v18", "v20")
    assert prediction.final.judgment["v1"]["위반여부"] == 0
    assert prediction.final.judgment["v10"]["위반여부"] == 0
    assert not prediction.triage_parse_error
    assert not prediction.strict_recovery_used
    assert "사전검토" in prediction.triage_messages[0]["content"]
    assert "v10" in prediction.strict_messages[0]["content"]
    assert "- v1:" not in prediction.strict_messages[0]["content"]


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


def test_compliance_expert_role_directive_reinforces_cards_without_new_facts() -> None:
    item_table = {"v1": {"항목명": "항목 1", "비고": ""}}
    cards = {"v1": {"item_name": "항목 1", "prompt_text": "1 조건: A. 0 조건: B."}}
    prompt = build_system_prompt(
        item_table,
        decision_cards=cards,
        active_items=("v1",),
        role_directive="compliance_expert_v1",
    )
    assert "공공계약 법령 컴플라이언스 사전심사" in prompt
    assert "적용 전제, 1 조건, 0 조건" in prompt
    assert "공고 밖 사실이나" in prompt
    assert "제공되지 않은 법령 내용을 보충하지 않는다" in prompt


def test_source_first_role_directive_only_adds_reading_workflow() -> None:
    item_table = {"v1": {"항목명": "항목 1", "비고": ""}}
    prompt = build_system_prompt(
        item_table,
        active_items=("v1",),
        role_directive="source_first_v1",
    )
    assert "[판정 순서]" in prompt
    assert "공고 자료 원문에서 실제 제한·요구·불일치" in prompt
    assert "한 문구를 비슷한 여러 항목의 위반으로 넓혀 해석하지 말고" in prompt
    assert "법령 참조" not in prompt


def test_v23_specialist_role_requires_relationship_gates_without_new_threshold() -> None:
    item_table = {"v23": {"항목명": "현장설명회", "비고": ""}}
    cards = {"v23": {"item_name": "현장설명회", "prompt_text": "기존 10/20/40일 기준"}}
    prompt = build_system_prompt(
        item_table, decision_cards=cards, active_items=("v23",),
        profile="complete_fact_subset_v1", role_directive="v23_specialist_v1",
    )
    assert "[v23 전담 최종 판정 순서]" in prompt
    assert "가격입찰서·전자입찰서 제출, 개찰, 평가, 계약 날짜만으로는" in prompt
    assert "기존 10/20/40일 기준" in prompt
    assert "새" not in prompt[prompt.index("[v23 전담 최종 판정 순서]"):prompt.index("[v23 전담 최종 판정 순서]") + 700]


def test_v23_specialist_is_eligible_only_and_owns_only_final_v23_field() -> None:
    item_table = {
        item: {"항목명": item, "부재탐지": item in {"v10", "v11", "v16", "v18", "v20"},
               "국가계약법": "", "지방계약법": "", "비고": ""}
        for item in ITEMS
    }
    cards = {item: {"item_name": item, "prompt_text": "1 조건: A. 0 조건: B."} for item in ITEMS}
    pipeline = BaselinePipeline(
        item_table=item_table, client=MockClient(), max_document_chars=None,
        context_strategy="single", overflow_split_enabled=True,
        count_tokens=lambda messages: len(messages), prompt_budget_tokens=100,
        decision_cards=cards, prompt_profile="complete_fact_v1",
        metadata_style="official_lines", output_mode="labels_and_evidence",
    )
    eligible = _record("공고일: 2026. 1. 1. 제안서 제출: 2026. 1. 2.")
    eligible["meta"] = {"적용계약법": "지방계약법", "낙찰방법": "협상에의한계약"}
    result = pipeline.predict_with_fact_inventory_v23_specialist_final(eligible)
    assert result.eligible and result.specialist is not None
    assert not result.specialist_recovery_used
    assert set(result.final.judgment) == set(ITEMS)
    assert "[v23 전담 최종 판정 순서]" in result.specialist_messages_by_context[0][0]["content"]
    assert "지정 항목(v23)" in result.specialist_messages_by_context[0][0]["content"]

    ineligible = _record()
    ineligible["meta"] = {"적용계약법": "국가계약법", "낙찰방법": "협상에의한계약"}
    skipped = pipeline.predict_with_fact_inventory_v23_specialist_final(ineligible)
    assert not skipped.eligible and skipped.specialist is None
    assert skipped.final.judgment == skipped.base.final.judgment


def test_v23_proof_specialist_keeps_proof_observations_separate_from_model_label() -> None:
    payload = {
        "지방협상_근거": "지방 협상계약", "공고일_근거": "공고일: 2026. 1. 1.",
        "종료일_근거": "제안서 제출: 2026. 1. 2.", "종료일_역할": "제안서마감",
        "긴급재공고_근거": None,
        "판정": {"위반여부": 1, "근거문구": "제안서 제출: 2026. 1. 2."},
    }
    proof, judgment = parse_v23_proof_judgment_response(json.dumps(payload, ensure_ascii=False))
    assert proof["종료일_역할"] == "제안서마감"
    assert judgment == {"v23": {"위반여부": 1, "근거문구": "제안서 제출: 2026. 1. 2."}}
    payload["종료일_역할"] = "가격입찰"
    with pytest.raises(PredictionError, match="종료일_역할"):
        parse_v23_proof_judgment_response(json.dumps(payload, ensure_ascii=False))


def test_v23_proof_specialist_mock_has_complete_proof_contract() -> None:
    item_table = {
        item: {"항목명": item, "부재탐지": item in {"v10", "v11", "v16", "v18", "v20"},
               "국가계약법": "", "지방계약법": "", "비고": ""}
        for item in ITEMS
    }
    cards = {item: {"item_name": item, "prompt_text": "1 조건: A. 0 조건: B."} for item in ITEMS}
    pipeline = BaselinePipeline(
        item_table=item_table, client=MockClient(), max_document_chars=None,
        context_strategy="single", overflow_split_enabled=True,
        count_tokens=lambda messages: len(messages), prompt_budget_tokens=100,
        decision_cards=cards, prompt_profile="complete_fact_v1",
        metadata_style="official_lines", output_mode="labels_and_evidence",
    )
    record = _record("공고일: 2026. 1. 1. 제안서 제출: 2026. 1. 2.")
    record["meta"] = {"적용계약법": "지방계약법", "낙찰방법": "협상에의한계약"}
    result = pipeline.predict_with_fact_inventory_v23_proof_specialist_final(record)
    assert result.eligible and result.proof_mode and result.proof is not None
    assert result.proof["per_pass"][0]["종료일_역할"] == "없음"
    assert not result.specialist_recovery_used
    assert "[v23 proof-carrying 출력 형식]" in result.specialist_messages_by_context[0][0]["content"]


def test_absence_only_group_has_its_own_workflow_and_never_requests_evidence() -> None:
    item_table = {
        item: {"항목명": item, "부재탐지": item in {"v10", "v11", "v16", "v18", "v20"}, "비고": ""}
        for item in ITEMS
    }
    items = ("v10", "v11", "v16", "v18", "v20")
    prompt = build_system_prompt(item_table, active_items=items, layout="markdown_v2")
    message = build_messages(
        _record(), prompt, None, document_context="[공고문:D0]\\n본문", markdown_sections=True,
        task_profile="absence",
    )[1]["content"]
    assert "# 부재 항목 판정 순서" in prompt
    assert "근거문구는 항상 null" in prompt
    assert "1이면 공고 자료 원문의 근거문구" not in message
    assert "부재 항목은 1이어도 근거문구를 null" in message


def test_v24_only_group_has_field_by_field_comparison_workflow() -> None:
    item_table = {"v24": {"항목명": "상이", "부재탐지": False, "비고": ""}}
    prompt = build_system_prompt(item_table, active_items=("v24",), layout="markdown_v2")
    assert "# v24 대조 순서" in prompt
    assert "같은 의미 필드와 한 쌍씩 비교" in prompt


def test_official_baseline_profile_has_its_exact_context_and_message_contract() -> None:
    record = _record("A" * 50)
    record["docs"].append({"doc_id": "D1", "type": "규격서", "text": "규격"})
    record["meta"] = {"적용계약법": "국가계약법", "배정예산금액": None}
    context = build_official_baseline_context(record, 40)
    assert context.startswith("[공고문:D0]\n" + "A" * 31)
    assert "[절단] 공고문 뒷부분이 길이 예산으로 잘렸다" in context
    assert "[미수록 문서] 규격서 1건" in context
    assert format_official_baseline_meta(record) == "- 적용계약법: 국가계약법\n- 배정예산금액: 미기재"
    item_table = {item: {"항목명": item, "부재탐지": item == "v10", "비고": ""} for item in ITEMS}
    system = build_system_prompt(item_table, profile="official_baseline_v1")
    messages = build_messages(record, system, 40, prompt_profile="official_baseline_v1")
    assert "[공고 ID] test-id" in messages[1]["content"]
    assert "판정할 24개 항목" in system
    assert "v10: v10  [근거 없음 — null]" in system


def test_human_readable_metadata_removes_only_product_and_license_codes() -> None:
    record = _record()
    record["meta"] = {
        "세부품명번호목록": "축제기획및대행서비스[9015189001], 가구[5610151901]",
        "면허업종제한목록": "[기타자유업(행사대행업)(9901)]",
        "입찰추정가격": 327272727,
        "조항호내용": "제25조(예외 4개)",
        "정보화사업여부": "미입력",
        "낙찰하한율": None,
    }

    historical = format_official_baseline_meta(record)
    human = format_official_baseline_meta(record, human_readable_codes=True)

    assert "축제기획및대행서비스[9015189001]" in historical
    assert "(9901)" in historical
    assert "축제기획및대행서비스, 가구" in human
    assert "[기타자유업(행사대행업)]" in human
    assert "9015189001" not in human
    assert "5610151901" not in human
    assert "9901" not in human
    assert "- 입찰추정가격: 327272727" in human
    assert "- 조항호내용: 제25조(예외 4개)" in human
    assert "- 정보화사업여부: 미입력" in human
    assert "- 낙찰하한율: 미기재" in human


def test_complete_fact_human_metadata_style_keeps_source_codes_unchanged() -> None:
    record = _record("원문 세부품명번호 9015189001")
    record["meta"] = {"세부품명번호목록": "축제기획및대행서비스[9015189001]"}
    item_table = {
        item: {"항목명": item, "부재탐지": False, "비고": ""}
        for item in ITEMS
    }
    system = build_system_prompt(item_table, profile="complete_fact_v1")
    user = build_messages(
        record,
        system,
        None,
        prompt_profile="complete_fact_v1",
        metadata_style="official_lines_human_v2",
    )[1]["content"]

    metadata, source = user.split("[공고 자료 원문]", 1)
    assert "9015189001" not in metadata
    assert "축제기획및대행서비스" in metadata
    assert "9015189001" in source


def test_official_baseline_profile_supports_labels_only_without_evidence_contract() -> None:
    item_table = {item: {"항목명": item, "부재탐지": item == "v10", "비고": ""} for item in ITEMS}
    prompt = build_system_prompt(
        item_table, profile="official_baseline_v1", output_mode="labels_only"
    )
    message = build_messages(
        _record(), prompt, 4000, prompt_profile="official_baseline_v1", output_mode="labels_only"
    )[1]["content"]
    assert "근거 문구" not in prompt
    assert "[근거 없음]" in prompt
    assert "근거문구" not in message


def test_exact_organizer_control_prompt_matches_organizer_baseline() -> None:
    """Protect the immutable 24-item organizer control from rendering drift.

    Root ``config.yaml`` may select a disjoint item-group submission policy;
    the parity control itself remains versioned as EXP125A rather than being
    inferred from whichever submission policy is currently canonical.
    """
    from src.config import load_config
    from src.external.openrouter import MockClient

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "organizer_baseline_for_parity", root / "data/raw/open/baseline/script.py"
    )
    assert spec is not None and spec.loader is not None
    organizer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(organizer)
    config = load_config(root / "configs/config.exp125a-exact-baseline-ve-fast-panel.yaml")
    item_table = {
        item: {"항목명": item, "부재탐지": item == "v10", "비고": ""}
        for item in ITEMS
    }
    record = _record("공고 원문")
    record["meta"] = {"적용계약법": "국가계약법", "배정예산금액": None}
    pipeline = BaselinePipeline(
        item_table=item_table,
        client=MockClient(),
        max_document_chars=config.max_document_chars,
        prompt_mode=config.prompt_mode,
        context_strategy=config.context_strategy,
        notice_anchor_chars=config.notice_anchor_chars,
        overflow_split_enabled=config.overflow_split_enabled,
        prompt_budget_tokens=config.max_model_len - config.output_reserve_tokens,
        strict_document_evidence=config.strict_document_evidence,
        absence_detection_strategy=config.absence_detection_strategy,
        prompt_layout=config.prompt_layout,
        prompt_profile=config.prompt_profile,
        role_directive=config.role_directive,
        item_catalog_style=config.item_catalog_style,
        metadata_style=config.metadata_style,
        output_mode=config.output_mode,
    )
    expected = organizer.build_messages(
        record, organizer.build_system_prompt(item_table), config.max_document_chars
    )
    assert pipeline.messages_for_context(record, None) == expected


def test_official_baseline_subset_keeps_renderer_but_limits_output_items() -> None:
    """A diagnostic subset may not silently become a different prompt family."""
    item_table = {"v2": {"항목명": "실적제한", "부재탐지": False, "비고": ""}}
    system = build_system_prompt(
        item_table,
        active_items=("v2",),
        profile="official_baseline_subset_v1",
    )
    assert "아래 지정 항목(v2) 각각" in system
    assert "지정 항목(v2) 전부에 답한다" in system
    assert "키는 v2," in system
    assert "- v2: 실적제한" in system
    messages = build_messages(
        _record("공고 원문"), system, 4000,
        prompt_profile="official_baseline_subset_v1",
        metadata_style="official_lines",
    )
    assert messages[1]["content"].startswith("[공고 ID] test-id\n\n[나라장터 입력 메타]\n")


def test_complete_fact_subset_keeps_clean_input_and_limits_output_items() -> None:
    """Grouped complete-source runs must not inherit the full-24-item contract."""
    item_table = {"v9": {"항목명": "특정 모델", "부재탐지": False, "비고": ""}}
    system = build_system_prompt(
        item_table,
        active_items=("v9",),
        profile="complete_fact_subset_v1",
    )
    assert "아래 지정 항목(v9) 각각" in system
    assert "지정 항목(v9) 전부에 답한다" in system
    assert "키는 v9," in system
    messages = build_messages(
        _record("공고 원문"), system, None,
        prompt_profile="complete_fact_subset_v1",
        metadata_style="official_lines",
    )
    assert not messages[1]["content"].startswith("[공고 ID]")
    assert messages[1]["content"].startswith("[나라장터 입력 메타]\n")
    assert "[공고 자료 원문]\n[공고문:D0]" in messages[1]["content"]


def test_fact_inventory_contract_is_source_only_and_non_final() -> None:
    from src.prompt import append_fact_inventory, build_fact_inventory_system_prompt
    from src.schema import (
        FACT_INVENTORY_CATEGORIES,
        FACT_INVENTORY_CATEGORIES_V2,
        V6_GEOGRAPHY_FACT_FIELDS,
        fact_inventory_schema,
    )

    system = build_fact_inventory_system_prompt()
    assert "위반 여부" in system
    assert "판단하지 않는다" in system
    schema = fact_inventory_schema()
    assert tuple(schema["required"]) == FACT_INVENTORY_CATEGORIES
    assert schema["properties"][FACT_INVENTORY_CATEGORIES[0]]["maxItems"] == 3
    assert "최대 4개씩" in build_fact_inventory_system_prompt(4)
    assert fact_inventory_schema(4)["properties"][FACT_INVENTORY_CATEGORIES[0]]["maxItems"] == 4
    assert tuple(fact_inventory_schema(categories=FACT_INVENTORY_CATEGORIES_V2)["required"]) == FACT_INVENTORY_CATEGORIES_V2
    assert "예외_허용_적용범위" in build_fact_inventory_system_prompt(
        categories=FACT_INVENTORY_CATEGORIES_V2
    )
    payload = {category: ["원문1", "원문2", "원문3", "원문4"]
               for category in FACT_INVENTORY_CATEGORIES}
    text = json.dumps(payload, ensure_ascii=False)
    assert parse_fact_inventory_response(text, max_items=4) == payload
    with pytest.raises(PredictionError, match="up to 3 strings"):
        parse_fact_inventory_response(text)
    v2_payload = {category: [] for category in FACT_INVENTORY_CATEGORIES_V2}
    assert parse_fact_inventory_response(
        json.dumps(v2_payload, ensure_ascii=False), categories=FACT_INVENTORY_CATEGORIES_V2,
    ) == v2_payload
    v6_payload = {field: [] for field in V6_GEOGRAPHY_FACT_FIELDS}
    assert tuple(
        fact_inventory_schema(categories=V6_GEOGRAPHY_FACT_FIELDS)["required"]
    ) == V6_GEOGRAPHY_FACT_FIELDS
    assert parse_fact_inventory_response(
        json.dumps(v6_payload, ensure_ascii=False),
        categories=V6_GEOGRAPHY_FACT_FIELDS,
    ) == v6_payload
    v6_prompt = build_fact_inventory_system_prompt(
        categories=V6_GEOGRAPHY_FACT_FIELDS
    )
    assert "지역 참가자격의 관계" in v6_prompt
    assert "법령 위반 여부" in v6_prompt
    assert "판단하지 않는다" in v6_prompt
    messages = append_fact_inventory(
        [{"role": "system", "content": "final"}, {"role": "user", "content": "notice"}],
        {category: () for category in FACT_INVENTORY_CATEGORIES},
    )
    assert "후보가 없다는 것은 위반 없음이 아니다" in messages[-1]["content"]
    assert "최종 판정 아님" in messages[-1]["content"]
    before_source = append_fact_inventory(
        [{"role": "system", "content": "final"}, {"role": "user", "content": "메타\n\n[공고 자료 원문]\n원문"}],
        {category: () for category in FACT_INVENTORY_CATEGORIES}, position="before_source",
    )
    assert len(before_source) == 2
    assert before_source[-1]["content"].index("최종 판정 아님") < before_source[-1]["content"].index("[공고 자료 원문]")


def test_fact_inventory_keeps_relation_checklist_last_in_source_first_final() -> None:
    pipeline = BaselinePipeline(
        item_table={item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS},
        client=MockClient(), max_document_chars=None,
        prompt_mode="relation_checklist_after_source_v1",
        prompt_profile="complete_fact_v1",
    )
    base = pipeline.messages_for_context(_record("마지막 원문 문장"), None)
    inventory = {category: () for category in (
        "참가자격_실적_지역", "제품_기업_직접생산", "규격_모델_기술요구",
        "제출서류_확약서", "계약방식_공동계약", "일정_설명회", "금액_메타대조",
    )}
    messages = append_fact_inventory(base, inventory)
    rendered = "\n".join(message["content"] for message in messages)
    assert rendered.count("[판정 직전 관계 체크리스트]") == 1
    assert rendered.index("마지막 원문 문장") < rendered.index("[전체 공고 자료에서 수집한 원문 사실")
    assert rendered.index("[전체 공고 자료에서 수집한 원문 사실") < rendered.index("[판정 직전 관계 체크리스트]")


def test_shared_fact_inventory_keeps_only_source_substrings_and_survives_malformed() -> None:
    from src.schema import FACT_INVENTORY_CATEGORIES

    record = _record("서울특별시에  본사를 둔 업체로 제한한다\n실적 3억원 이상")
    first = {category: [] for category in FACT_INVENTORY_CATEGORIES}
    first[FACT_INVENTORY_CATEGORIES[0]] = [
        "서울특별시에 본사를 둔 업체로 제한한다",
        "원문에 없는 제한",
    ]
    second = {category: [] for category in FACT_INVENTORY_CATEGORIES}
    second[FACT_INVENTORY_CATEGORIES[0]] = ["실적 3억원 이상"]

    inventory, errors = collect_validated_fact_inventory(
        record,
        [
            (record["docs"][0]["text"], json.dumps(first, ensure_ascii=False)),
            (record["docs"][0]["text"], "malformed"),
            (record["docs"][0]["text"], json.dumps(second, ensure_ascii=False)),
        ],
    )

    assert inventory[FACT_INVENTORY_CATEGORIES[0]] == (
        ("D0", "서울특별시에  본사를 둔 업체로 제한한다"),
        ("D0", "실적 3억원 이상"),
    )
    assert len(errors) == 1
    assert all("원문에 없는 제한" not in excerpt for _, excerpt in inventory[FACT_INVENTORY_CATEGORIES[0]])


def test_shared_fact_inventory_final_plan_matches_direct_construction() -> None:
    from src.prompt import append_fact_inventory
    from src.schema import FACT_INVENTORY_CATEGORIES

    record = _record("공고 전체 원문")
    pipeline = BaselinePipeline(
        item_table={item: {"항목명": item, "부재탐지": False, "비고": ""} for item in ITEMS},
        client=MockClient(),
        max_document_chars=None,
        context_strategy="single",
        overflow_split_enabled=True,
        count_tokens=lambda messages: sum(len(message["content"]) for message in messages),
        prompt_budget_tokens=100_000,
        prompt_profile="complete_fact_v1",
    )
    inventory = {category: () for category in FACT_INVENTORY_CATEGORIES}

    def old_messages(context):
        return append_fact_inventory(
            pipeline.messages_for_context(record, context), inventory,
        )

    expected_contexts = pack_contexts_to_token_budget(
        record,
        pipeline.system_prompt_for_record(record),
        pipeline.count_tokens,
        pipeline.prompt_budget_tokens,
        pipeline.notice_anchor_chars,
        message_builder=old_messages,
    )
    expected_messages = [old_messages(context) for context in expected_contexts]

    contexts, messages = pipeline.fact_inventory_final_plan(record, inventory)

    assert contexts == expected_contexts
    assert messages == expected_messages


def test_timeline_navigation_is_role_grounded_and_never_a_final_label() -> None:
    from src.prompt import (
        append_timeline_fact_navigation,
        build_source_only_fact_messages,
        build_timeline_fact_system_prompt,
    )
    from src.schema import TIMELINE_FACT_ROLES, timeline_fact_schema

    prompt = build_timeline_fact_system_prompt()
    assert "최소 기간 계산" in prompt
    assert "위반 여부" in prompt
    source_only = build_source_only_fact_messages(prompt, "공고일: 2026. 1. 1.")
    assert len(source_only) == 2
    assert "나라장터 입력 메타" not in source_only[1]["content"]
    schema = timeline_fact_schema()
    assert tuple(schema["required"]) == TIMELINE_FACT_ROLES
    payload = {role: [] for role in TIMELINE_FACT_ROLES}
    payload["제안서_접수마감"] = ["제안서 제출: 2026. 1. 2."]
    assert parse_timeline_fact_response(json.dumps(payload, ensure_ascii=False)) == payload
    with pytest.raises(PredictionError, match="up to 2 strings"):
        parse_timeline_fact_response(json.dumps({role: ["x", "y", "z"] for role in TIMELINE_FACT_ROLES}))
    messages = append_timeline_fact_navigation(
        [{"role": "system", "content": "final"}, {"role": "user", "content": "source"}],
        {role: tuple() for role in TIMELINE_FACT_ROLES},
    )
    assert "후보가 없다고 0이 아니며" in messages[-1]["content"]
    assert "최종 판정 아님" in messages[-1]["content"]


def test_procedure_navigation_is_source_only_and_advisory() -> None:
    from src.prompt import (
        append_procedure_fact_navigation,
        build_procedure_fact_system_prompt,
    )
    from src.schema import PROCEDURE_FACT_FIELDS, procedure_fact_schema

    prompt = build_procedure_fact_system_prompt()
    assert "v 항목의 0/1" in prompt
    schema = procedure_fact_schema()
    assert tuple(schema["required"]) == PROCEDURE_FACT_FIELDS
    assert schema["properties"][PROCEDURE_FACT_FIELDS[0]]["maxItems"] == 2
    payload = {field: [] for field in PROCEDURE_FACT_FIELDS}
    assert parse_procedure_fact_response(json.dumps(payload, ensure_ascii=False)) == payload
    with pytest.raises(PredictionError, match="up to 2 strings"):
        parse_procedure_fact_response(json.dumps({field: ["x", "y", "z"] for field in PROCEDURE_FACT_FIELDS}))
    messages = append_procedure_fact_navigation(
        [{"role": "system", "content": "final"}, {"role": "user", "content": "source"}],
        {field: tuple() for field in PROCEDURE_FACT_FIELDS},
    )
    assert "최종 판정 아님" in messages[-1]["content"]
    assert "후보가 없다는 것은 위반 없음이 아니다" in messages[-1]["content"]


def test_official_profile_renders_product_context_and_full_context_when_requested() -> None:
    item_table = {
        item: {"항목명": item, "부재탐지": False, "국가계약법": "", "지방계약법": "", "비고": ""}
        for item in ITEMS
    }
    prompt = build_system_prompt(item_table, profile="official_baseline_v1", layout="markdown_v2")
    record = _record("첫 문서")
    record["docs"].append({"doc_id": "D1", "type": "규격서", "text": "둘째 문서"})
    messages = build_messages(
        record,
        prompt,
        None,
        competition_product_context="대회 제공 고시의 확인 결과입니다.",
        prompt_profile="official_baseline_v1",
    )
    assert "# 대회 제공 경쟁제품 고시 확인" in messages[1]["content"]
    assert "대회 제공 고시의 확인 결과입니다." in messages[1]["content"]
    assert "둘째 문서" in messages[1]["content"]


def test_single_no_split_rejects_over_budget_full_context() -> None:
    item_table = {
        item: {"항목명": item, "부재탐지": False, "국가계약법": "", "지방계약법": "", "비고": ""}
        for item in ITEMS
    }
    pipeline = BaselinePipeline(
        item_table=item_table,
        client=None,
        max_document_chars=None,
        context_strategy="single_no_split",
        count_tokens=lambda messages: 11,
        prompt_budget_tokens=10,
    )
    with pytest.raises(ContextAdmissionError, match="requires 11"):
        pipeline.contexts_for_record(_record())


def test_visible_document_types_limits_the_prompt_to_announcement() -> None:
    item_table = {"v1": {"항목명": "항목 1", "비고": ""}}
    record = _record("공고문 본문")
    record["docs"].append({"doc_id": "D1", "type": "규격서", "text": "첨부 규격 내용"})
    pipeline = BaselinePipeline(
        item_table=item_table,
        client=None,
        max_document_chars=None,
        active_items=("v1",),
        visible_document_types=("공고문",),
    )
    message = pipeline.messages_for_context(record, None)[1]["content"]
    assert "공고문 본문" in message
    assert "첨부 규격 내용" not in message


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


def test_competition_product_condition_mode_renders_condition_and_friendly_provenance() -> None:
    context = format_competition_product_context(
        _record(),
        {
            "status": "matched",
            "matched_products": [
                {
                    "세부품명번호": "9015189001",
                    "세부품명": "축제기획및대행서비스",
                    "특이사항": "추정가격 3억원 미만에 한함",
                    "metadata_match": True,
                    "document_match_sources": [
                        {"doc_id": "INTERNAL-D0", "type": "공고문"},
                        {"doc_id": "INTERNAL-R1", "type": "제안요청서"},
                    ],
                }
            ],
        },
        context_mode="conditions_and_provenance_v2",
    )

    assert "추정가격 3억원 미만에 한함" in context
    assert "나라장터 세부품명 목록" in context
    assert "공고 자료 공고문·제안요청서" in context
    assert "행 일치는 실제 적용 확정이 아니므로" in context
    assert "적용조건도 충족하는지 확인된 경우에만 경쟁제품 적용 근거" in context
    assert "정확히 매칭되면 경쟁제품 근거로 사용" not in context
    assert "9015189001" not in context
    assert "INTERNAL-D0" not in context
    assert "matched" not in context


def test_competition_product_condition_mode_marks_unconditional_row() -> None:
    context = format_competition_product_context(
        _record(),
        {
            "status": "matched",
            "matched_products": [
                {
                    "세부품명": "잡석",
                    "특이사항": "",
                    "metadata_match": False,
                    "document_match_sources": [{"doc_id": "D0", "type": "규격서"}],
                }
            ],
        },
        context_mode="conditions_and_provenance_v2",
    )

    assert "별도 적용조건 없음" in context
    assert "공고 자료 규격서" in context


def test_competition_product_full_catalog_is_readable_and_hides_codes() -> None:
    context = format_competition_product_context(
        _record(),
        {"status": "unknown", "matched_products": []},
        active_items=("v10",),
        context_mode="full_catalog_v1",
        product_catalog={
            "8014199001": {
                "세부품명": "기타행사기획및대행서비스",
                "특이사항": "추정가격 10억원 미만에 한함",
            },
            "1111169701": {"세부품명": "잡석", "특이사항": ""},
        },
    )

    assert "경쟁제품 전체 목록" in context
    assert "기타행사기획및대행서비스" in context
    assert "추정가격 10억원 미만에 한함" in context
    assert "- 잡석" in context
    assert "8014199001" not in context
    assert "unknown" not in context


def test_official_prompt_hides_internal_notice_id_and_separates_source_text() -> None:
    record = _record()
    record["id"] = "INTERNAL-ONLY-ID"
    messages = build_messages(
        record,
        "system",
        None,
        prompt_profile="complete_fact_v1",
        metadata_style="official_lines",
        competition_product_context="경쟁제품 확인 결과입니다.",
    )

    content = messages[-1]["content"]
    assert "INTERNAL-ONLY-ID" not in content
    assert "경쟁제품 확인 결과입니다.\n\n[공고 자료 원문]" in content


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


def test_product_context_is_supplied_for_every_product_classification_item() -> None:
    item_table = {
        item: {"항목명": item, "부재탐지": False, "국가계약법": "", "지방계약법": "", "비고": ""}
        for item in ITEMS
    }
    record = _record()
    record["meta"]["세부품명번호목록"] = "잡석[8014199001]"
    pipeline = BaselinePipeline(
        item_table=item_table,
        client=None,
        max_document_chars=None,
        competition_products={"8014199001": {"세부품명": "잡석"}},
        active_items=("v12", "v14", "v15", "v17"),
    )

    context = pipeline.competition_product_context_for_record(record)

    assert context is not None
    assert "v12·v14·v15·v17" in context


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


def test_v8_observation_contract_is_not_injected_into_groups_without_v8() -> None:
    item_table = {
        item: {"항목명": item, "부재탐지": item in {"v10", "v11", "v16", "v18", "v20"}, "비고": ""}
        for item in ITEMS
    }
    pipeline = BaselinePipeline(
        item_table=item_table, client=None, max_document_chars=4000,
        active_items=("v10", "v11", "v16", "v18", "v20"),
        v8_composite_merge_enabled=True, prompt_layout="markdown_v2",
    )
    assert "v8 문서 간 결합 관찰" not in pipeline.system_prompt


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
