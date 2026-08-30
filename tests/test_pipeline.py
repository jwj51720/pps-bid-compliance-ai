from __future__ import annotations

import json

import pytest

from src.pipeline import PredictionError, parse_judgment, postprocess_judgment
from src.prompt import build_document_context, build_messages, build_system_prompt, normalize_notice_facts
from src.schema import ITEMS


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


def test_parse_judgment_accepts_fenced_json() -> None:
    expected = _judgment()
    parsed = parse_judgment(f"```json\n{json.dumps(expected, ensure_ascii=False)}\n```")
    assert parsed == expected


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


def test_normalized_facts_only_restate_notice_metadata() -> None:
    meta = {"세부품명번호목록": "과일류[5030990101]", "입찰추정가격": 10}
    facts = normalize_notice_facts(meta)

    assert facts["세부품명번호"] == ["5030990101"]
    assert facts["추정가격원"] == 10
