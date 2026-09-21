from __future__ import annotations

from src.pps_ai.views.v4_requirements import build_v4_requirement_view


def _record(texts: list[str]) -> dict[str, object]:
    return {
        "id": "N1",
        "docs": [
            {
                "doc_id": f"D{index}",
                "type": "공고문" if index == 0 else "제안요청서",
                "text": text,
            }
            for index, text in enumerate(texts)
        ],
    }


def test_view_inspects_every_document_and_preserves_exact_offsets() -> None:
    record = _record([
        "입찰참가자격\n최근 3년 이내 공공기관 수행실적이 있는 업체",
        "평가표\n유사용역 수행 경험이 있으면 가점",
        "관련 문구가 없는 문서",
    ])
    view = build_v4_requirement_view(record)
    assert len(view["document_coverage"]) == 3
    assert all(row["inspected"] for row in view["document_coverage"])
    assert len(view["candidates"]) == 2
    for candidate in view["candidates"]:
        document = record["docs"][candidate.document_order]
        assert document["text"][candidate.start:candidate.end] == candidate.text
        assert candidate.document_sha256 == view["document_coverage"][candidate.document_order]["sha256"]


def test_nearby_anchors_form_one_requirement_candidate() -> None:
    record = _record(["실적 제한: 납품경험 또는 이행경험이 있는 업체"])
    view = build_v4_requirement_view(record)
    assert len(view["candidates"]) == 1
    assert view["candidates"][0].trigger_surfaces == ("실적", "납품경험", "이행경험")


def test_distant_anchors_remain_separate_instances() -> None:
    record = _record(["실적 조건" + ("가" * 400) + "평가용 실적"])
    view = build_v4_requirement_view(record)
    assert len(view["candidates"]) == 2


def test_no_anchor_is_explicitly_not_found_without_candidate_limit() -> None:
    view = build_v4_requirement_view(_record(["일반 공고", "일반 첨부"]))
    assert not view["candidates"]
    assert [row["state"] for row in view["document_coverage"]] == ["NOT_FOUND", "NOT_FOUND"]
    assert view["omission_policy"]["candidate_limit"] is None
