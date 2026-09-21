from src.config import load_config
from scripts.inspect_prompt import build_pipeline_for_preview
from scripts.inspect_grouped_prompt import build_grouped_previews
from src.prompt import append_untrusted_review_draft


def test_preview_pipeline_uses_configured_decision_cards():
    config = load_config("configs/config.exp121b-official-interpretations-panel.yaml")
    pipeline = build_pipeline_for_preview(config)
    assert "규격·가격 동시입찰 여부나 감점형 평가 방식은 0 조건이 아니다." in pipeline.system_prompt


def test_grouped_preview_reconstructs_each_configured_group():
    config = load_config("configs/config.exp091-three-group-v4-cards-all-full-fast20.yaml")
    record = {
        "id": "PPS-TEST-GROUP",
        "meta": {},
        "docs": [{"doc_id": "D0", "type": "공고문", "text": "공고문 원문"}],
    }
    previews = build_grouped_previews(config, record)
    assert {preview["group"] for preview in previews} == {
        "G01_presence_items", "G02_absence_items", "G03_document_metadata_consistency",
    }
    assert all(preview["token_count"] > 0 for preview in previews)
    assert all(preview["messages"][1]["content"] for preview in previews)


def test_grouped_preview_applies_cards_only_to_declared_group() -> None:
    config = load_config("configs/config.exp137-two-way-g02-card-v6-fast-panel.yaml")
    record = {
        "id": "PPS-TEST-GROUP-CARDS",
        "meta": {},
        "docs": [{"doc_id": "D0", "type": "공고문", "text": "공고문 원문"}],
    }
    previews = {value["group"]: value for value in build_grouped_previews(config, record)}
    assert "판정 카드:" not in previews["G01_remainder_items"]["messages"][0]["content"]
    assert "판정 카드:" in previews["G02_document_restrictions"]["messages"][0]["content"]


def test_overlay_preview_keeps_exact_full_profile_only_for_first_group() -> None:
    config = load_config("configs/config.exp139-two-call-g02-overlay-fast-panel.yaml")
    record = {
        "id": "PPS-TEST-GROUP-OVERLAY",
        "meta": {},
        "docs": [{"doc_id": "D0", "type": "공고문", "text": "공고문 원문"}],
    }
    previews = {value["group"]: value for value in build_grouped_previews(config, record)}
    full = previews["G01_full_baseline"]
    focused = previews["G02_document_restrictions_override"]
    assert full["prompt_profile"] == "official_baseline_v1"
    assert focused["prompt_profile"] == "official_baseline_subset_v1"
    assert "아래 24개 항목 각각에 대해" in full["messages"][0]["content"]
    assert "지정 항목(v6, v7, v8, v9, v19)" in focused["messages"][0]["content"]


def test_semantic_verifier_preview_keeps_control_clean_and_products_scoped() -> None:
    config = load_config("configs/config.exp142-semantic-verifier-preview.yaml")
    record = {
        "id": "PPS-TEST-SEMANTIC-VERIFIER",
        "meta": {"세부품명번호목록": "물품[0000000000]"},
        "docs": [{"doc_id": "D0", "type": "공고문", "text": "공고문 원문"}],
    }
    previews = {value["group"]: value for value in build_grouped_previews(config, record)}
    full = previews["G01_full_baseline"]
    qualification = previews["G02_qualification_document_procedure"]
    product = previews["G03_product_absence"]
    assert full["prompt_profile"] == "official_baseline_v1"
    assert "판정 카드:" not in full["messages"][0]["content"]
    assert "판정 카드:" in qualification["messages"][0]["content"]
    assert "판정 카드:" in product["messages"][0]["content"]
    assert "경쟁제품" not in full["messages"][1]["content"]
    assert "경쟁제품" not in qualification["messages"][1]["content"]


def test_untrusted_review_draft_carries_labels_but_never_first_pass_evidence() -> None:
    messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "[문서]\\n공고 원문"},
    ]
    judgment = {
        "v1": {"위반여부": 1, "근거문구": "원문 근거"},
        "v2": {"위반여부": 0, "근거문구": None},
    }
    reviewed = append_untrusted_review_draft(messages, judgment, ("v1", "v2"))
    assert reviewed[0] == messages[0]
    assert "[1차 검토 초안 — 공고 자료가 아님]" in reviewed[1]["content"]
    assert "- v1: 1" in reviewed[1]["content"]
    assert "- v2: 0" in reviewed[1]["content"]
    assert "원문 근거" not in reviewed[1]["content"]
    assert "공고 자료 원문에서만 그대로 복사" in reviewed[1]["content"]
