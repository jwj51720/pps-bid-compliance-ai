from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from evidence_resolver import resolve_quote


def test_exact_quote_is_unchanged_source() -> None:
    docs = [{"text": "입찰참가자격은 소기업으로 제한합니다."}]
    value, status = resolve_quote("소기업으로 제한", docs)
    assert status == "exact"
    assert value in docs[0]["text"]


def test_omitted_anonymization_tag_returns_original_source() -> None:
    source = "주된 영업소 소재지가 세종특별자치시 또는 충청남도 [지역:r1|단위=기초]에 있어야 합니다."
    quote = "주된 영업소 소재지가 세종특별자치시 또는 충청남도에 있어야 합니다."
    value, status = resolve_quote(quote, [{"text": source}])
    assert status == "anonymization_unique"
    assert value == source


def test_duplicate_exact_quote_is_still_valid_evidence() -> None:
    docs = [{"text": "같은 문장입니다. 같은 문장입니다."}]
    value, status = resolve_quote("같은 문장입니다.", docs)
    assert value == "같은 문장입니다."
    assert status == "exact"


def test_table_interleaving_resolves_to_original_window() -> None:
    source = "아. 최근 3년 이내 기업 굿즈 디자인 기획 및 제작 용역실적이\n수량 약 16,600개\n있는 업체"
    quote = "아. 최근 3년 이내 기업 굿즈 디자인 기획 및 제작 용역실적이 있는 업체"
    value, status = resolve_quote(quote, [{"text": source}])
    assert status == "ordered_anchor_unique"
    assert value == source
