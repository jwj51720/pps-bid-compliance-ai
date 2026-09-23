from __future__ import annotations

from src.pps_ai.facts.regional_thresholds import classify_regional_threshold
from src.pps_ai.decisions.regional_thresholds import (
    apply_regional_threshold, guard_new_regional_positives,
)
from src.pps_ai.views.regional_participation import (
    build_regional_participation_candidates,
)


def _record(
    *, law: str = "지방계약법", procurement: str = "일반용역",
    category: str = "지방정부", text: str = "[수요기관(기초자치단체)] 공고",
) -> dict:
    return {
        "id": "PPS-TEST",
        "meta": {"적용계약법": law, "업무구분": procurement, "소관구분": category},
        "docs": [{"doc_id": "D1", "type": "공고문", "text": text}],
    }


def test_basic_local_government_uses_500m() -> None:
    fact = classify_regional_threshold(_record())
    assert fact.state == "CONFIRMED"
    assert fact.institution_type == "city_county_district"
    assert fact.threshold_won == 500_000_000


def test_education_metadata_uses_500m_without_document_guess() -> None:
    fact = classify_regional_threshold(_record(category="교육기관", text="입찰공고"))
    assert fact.state == "CONFIRMED"
    assert fact.institution_type == "education_or_school"
    assert fact.threshold_won == 500_000_000
    assert any(source.source_name == "소관구분" for source in fact.sources)


def test_local_public_enterprise_uses_500m() -> None:
    fact = classify_regional_threshold(_record(category="지방공기업", text="입찰공고"))
    assert fact.state == "CONFIRMED"
    assert fact.institution_type == "local_public_enterprise"
    assert fact.threshold_won == 500_000_000


def test_province_marker_stays_unknown_when_sejong_identity_is_absent() -> None:
    fact = classify_regional_threshold(
        _record(text="[수요기관(광역자치단체)] 공고 [공고번호]")
    )
    assert fact.state == "UNKNOWN"
    assert fact.institution_type == "province_or_sejong_unknown"
    assert fact.threshold_won is None


def test_explicit_safety_service_title_overrides_institution() -> None:
    fact = classify_regional_threshold(_record(
        text="용 역 명: 교량 정밀안전진단 용역\n[수요기관(광역자치단체)]",
    ))
    assert fact.state == "CONFIRMED"
    assert fact.service_type == "safety_inspection_or_precision_diagnosis"
    assert fact.threshold_won == 150_000_000


def test_technical_service_requires_title_relation() -> None:
    fact = classify_regional_threshold(_record(
        text="용 역 명: 청사 건축 설계용역\n[수요기관(광역자치단체)]",
    ))
    assert fact.state == "CONFIRMED"
    assert fact.service_type == "technical_design_supervision_engineering"
    assert fact.threshold_won == 330_000_000


def test_spaced_notice_title_identifies_design_service() -> None:
    fact = classify_regional_threshold(_record(
        category="지자체 출자출연기관",
        text="[수요기관(공공기관)] 공고\n"
             "공 고 명 : 복합공간 디자인 및 실시 설계 용역",
    ))
    assert fact.state == "CONFIRMED"
    assert fact.threshold_won == 330_000_000


def test_generic_safety_clause_does_not_change_general_service_branch() -> None:
    fact = classify_regional_threshold(_record(
        text="[수요기관(기초자치단체)] 공고\n용 역 명: 행사 운영 용역\n"
             "계약상대자는 매일 안전점검을 실시한다.",
    ))
    assert fact.service_type == "goods_or_general_services"
    assert fact.threshold_won == 500_000_000


def test_national_contract_is_outside_this_correction() -> None:
    fact = classify_regional_threshold(_record(law="국가계약법"))
    assert fact.state == "NOT_APPLICABLE"
    assert fact.threshold_won is None


def test_named_province_issuer_uses_350m() -> None:
    fact = classify_regional_threshold(_record(
        text="서울특별시 재무공고 [공고번호]\n입찰공고",
    ))
    assert fact.state == "CONFIRMED"
    assert fact.institution_type == "province_except_sejong"
    assert fact.threshold_won == 350_000_000


def test_named_sejong_issuer_uses_500m() -> None:
    fact = classify_regional_threshold(_record(
        text="세종특별자치시 공고 [공고번호]\n입찰공고",
    ))
    assert fact.state == "CONFIRMED"
    assert fact.institution_type == "sejong"
    assert fact.threshold_won == 500_000_000


def test_location_marker_in_body_does_not_become_issuer() -> None:
    fact = classify_regional_threshold(_record(
        text="[수요기관(지방정부)] 공고 [공고번호]\n"
             "납품장소: [수요기관(기초자치단체)] 지정장소",
    ))
    assert fact.state == "UNKNOWN"
    assert fact.threshold_won is None


def test_parametrized_issuer_marker_is_recognized() -> None:
    fact = classify_regional_threshold(_record(
        text="[수요기관(기초자치단체)|지역=r1] 공고 [공고번호]",
    ))
    assert fact.state == "CONFIRMED"
    assert fact.threshold_won == 500_000_000


def test_v5_is_inclusive_and_v6_v7_are_strictly_below_threshold() -> None:
    fact = classify_regional_threshold(_record(
        text="서울특별시 재무공고 [공고번호]",
    ))
    hits = {"v5": 1, "v6": 1, "v7": 1}
    base = {"v5": 0, "v6": 0, "v7": 0}
    below = apply_regional_threshold(
        fact, 349_999_999, hits, False, base,
    )
    at_cap = apply_regional_threshold(
        fact, 350_000_000, hits, False, base,
    )
    assert below.labels == {"v5": 0, "v6": 1, "v7": 1}
    assert at_cap.labels == {"v5": 1, "v6": 0, "v7": 0}


def test_small_quote_exception_only_clears_v6_v7() -> None:
    fact = classify_regional_threshold(_record())
    verdict = apply_regional_threshold(
        fact, 50_000_000, {"v5": 1, "v6": 1, "v7": 1}, True,
        {"v5": 0, "v6": 1, "v7": 1},
    )
    assert verdict.labels == {"v5": 0, "v6": 0, "v7": 0}


def test_unknown_threshold_preserves_base_labels() -> None:
    fact = classify_regional_threshold(_record(
        text="[수요기관(지방정부)] 공고 [공고번호]",
    ))
    base = {"v5": 1, "v6": 0, "v7": 1}
    verdict = apply_regional_threshold(
        fact, 400_000_000, {"v5": 1, "v6": 1, "v7": 1}, False, base,
    )
    assert verdict.applied is False
    assert verdict.labels == base


def test_new_v5_positive_needs_bidder_location_clause() -> None:
    fact = classify_regional_threshold(_record(
        text="서울특별시 재무공고 [공고번호]",
    ))
    base = {"v5": 0, "v6": 0, "v7": 0}
    raw = apply_regional_threshold(
        fact, 360_000_000, {"v5": 1, "v6": 0, "v7": 0}, False, base,
    )
    assert raw.labels["v5"] == 1
    assert guard_new_regional_positives(raw, base, ()).labels["v5"] == 0
    clause = (
        "입찰참가자격\n주된 영업소를 서울특별시에 둔 업체이어야 합니다."
    )
    view = build_regional_participation_candidates(_record(text=clause))
    assert guard_new_regional_positives(raw, base, view).labels["v5"] == 1


def test_new_v6_positive_needs_basic_region_in_same_clause() -> None:
    fact = classify_regional_threshold(_record())
    base = {"v5": 0, "v6": 0, "v7": 0}
    raw = apply_regional_threshold(
        fact, 300_000_000, {"v5": 0, "v6": 1, "v7": 0}, False, base,
    )
    province = build_regional_participation_candidates(_record(
        text="입찰참가자격\n본점 소재지를 전라남도에 둔 업체이어야 합니다.",
    ))
    basic = build_regional_participation_candidates(_record(
        text="입찰참가자격\n본점 소재지를 전라남도 "
             "[지역:r1|단위=기초|광역=전라남도]에 둔 업체이어야 합니다.",
    ))
    assert guard_new_regional_positives(raw, base, province).labels["v6"] == 0
    assert guard_new_regional_positives(raw, base, basic).labels["v6"] == 1
