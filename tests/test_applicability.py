from src.applicability import safe_inactive_items
from src.external.openrouter import MockClient
from src.pipeline import BaselinePipeline
from src.schema import ITEMS


def _record(meta: dict) -> dict:
    return {
        "id": "test",
        "meta": meta,
        "docs": [{"doc_id": "D0", "type": "공고문", "text": ""}],
    }


def test_safe_gate_uses_only_explicit_card_prerequisite_negations() -> None:
    products = {"1234567890": {"세부품명": "경쟁제품"}}
    inactive = safe_inactive_items(_record({
        "세부품명번호목록": "일반품[9999999999]",
        "입찰추정가격": "90000000",
        "낙찰방법": "적격심사제",
        "적용계약법": "국가계약법",
    }), products)
    assert {"v10", "v11", "v13"}.issubset(inactive)
    assert {"v15", "v16"}.issubset(inactive)
    assert inactive["v22"] == "explicit_non_negotiated"
    assert inactive["v23"] == "national_or_explicit_non_negotiated"
    assert "v6" not in inactive and "v12" not in inactive


def test_safe_gate_keeps_unknowns_and_competition_to_general_items_active() -> None:
    products = {"1234567890": {"세부품명": "경쟁제품"}}
    inactive = safe_inactive_items(_record({
        "세부품명번호목록": "경쟁품[1234567890]",
        "입찰추정가격": "가격 미상",
        "낙찰방법": "새로운 방식",
        "적용계약법": "",
    }), products)
    assert inactive == {}


def test_safe_gate_builds_a_complete_fact_subset_without_changing_unknown_items() -> None:
    products = {"1234567890": {"세부품명": "경쟁제품"}}
    item_table = {item: {"항목명": item, "비고": ""} for item in ITEMS}
    cards = {item: {"item_name": item, "prompt_text": "1 조건과 0 조건을 확인한다."} for item in ITEMS}
    record = _record({
        "세부품명번호목록": "일반품[9999999999]",
        "입찰추정가격": "90000000",
        "낙찰방법": "적격심사제",
        "적용계약법": "국가계약법",
    })
    pipeline = BaselinePipeline(
        item_table=item_table, client=MockClient(), max_document_chars=None,
        decision_cards=cards, competition_products=products,
        prompt_profile="complete_fact_v1", metadata_style="official_lines",
        applicability_gate_mode="safe_v1",
    )
    effective, inactive = pipeline.effective_pipeline_for_record(record)
    assert effective is not pipeline
    assert {"v10", "v11", "v13", "v15", "v16", "v22", "v23"}.issubset(inactive)
    assert "v1" in effective.active_items
    assert "v10" not in effective.active_items
