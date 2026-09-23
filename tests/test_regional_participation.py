from __future__ import annotations

from src.pps_ai.views.regional_participation import (
    build_regional_participation_candidates,
)


def _record(text: str) -> dict:
    return {
        "id": "PPS-TEST",
        "docs": [{"doc_id": "D1", "type": "공고문", "text": text}],
        "meta": {},
    }


def test_explicit_bidder_head_office_restriction_is_selected() -> None:
    text = "입찰참가자격\n주된 영업소가 서울특별시에 소재하고 있는 업체이어야 합니다."
    candidates = build_regional_participation_candidates(_record(text))
    assert len(candidates) == 1
    assert candidates[0].exact_text in text


def test_basic_region_marker_remains_attached_to_bidder_clause() -> None:
    text = (
        "입찰공고일 전일부터 계약체결일까지 주된 영업소가 "
        "서울특별시 [지역:r1|단위=기초|광역=서울특별시] 내에 소재하고 있는 업체이어야 합니다."
    )
    candidates = build_regional_participation_candidates(_record(text))
    assert len(candidates) == 1
    assert candidates[0].basic_region is True


def test_evaluation_bonus_is_not_participation_restriction() -> None:
    text = "지역업체참여도(3점): 서울지역으로 참여비율 평가"
    assert not build_regional_participation_candidates(_record(text))


def test_delivery_location_is_not_participation_restriction() -> None:
    text = "배출현장으로부터 처리업체 사업장 소재지까지의 운반거리를 평가합니다."
    assert not build_regional_participation_candidates(_record(text))


def test_subcontractor_local_preference_is_not_participation_restriction() -> None:
    text = "낙찰자는 전라남도 관내업체를 최대한 이용하도록 협조 바랍니다."
    assert not build_regional_participation_candidates(_record(text))


def test_long_wrapped_clause_has_exact_offsets_and_retains_region_role() -> None:
    text = (
        "3. 입찰 참가자격\n"
        "법인등기부상 본점 소재지(개인사업자인 경우 등록서류의 사업장 소재지)를 "
        + "계약체결일까지 계속하여 " * 20
        + "경기도에 둔 업체이어야 합니다.\n"
    )
    candidates = build_regional_participation_candidates(_record(text))
    assert len(candidates) == 1
    candidate = candidates[0]
    assert text[candidate.start:candidate.end] == candidate.exact_text
    assert len(candidate.exact_text) <= 500
