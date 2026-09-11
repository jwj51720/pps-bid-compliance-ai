from __future__ import annotations

import gzip
import json

from src.data import (
    competition_product_fact,
    load_competition_product_index,
    load_record_id_panel,
    load_records,
    profile_records,
    select_records_by_id,
)


def _record() -> dict:
    return {
        "id": "PPS-1",
        "docs": [{"doc_id": "D0", "type": "공고문", "text": "테스트"}],
        "meta": {"지역제한여부": None},
        "dropped_doc_counts": {},
        "input_completeness": {"fully_observed": True},
        "anon_applied": True,
        "assembly_policy_version": "test",
    }


def test_load_and_profile_jsonl_gzip(tmp_path) -> None:
    path = tmp_path / "records.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(json.dumps(_record(), ensure_ascii=False) + "\n")
    records = load_records(path)
    profile = profile_records(path)
    assert records[0]["id"] == "PPS-1"
    assert profile["record_count"] == 1
    assert profile["document_types"]["공고문"]["count"] == 1
    assert profile["meta"]["지역제한여부"]["null_rate"] == 1.0


def test_profile_recognizes_korean_completeness_flag(tmp_path) -> None:
    record = _record()
    record["input_completeness"] = {"완전관측": False}
    path = tmp_path / "records.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    assert profile_records(path)["records_not_fully_observed"] == 1


def test_record_id_panel_preserves_order(tmp_path) -> None:
    panel = tmp_path / "panel.json"
    panel.write_text(json.dumps({"ids": ["PPS-2", "PPS-1"]}), encoding="utf-8")
    records = [_record(), {**_record(), "id": "PPS-2"}]

    selected = select_records_by_id(records, load_record_id_panel(panel))

    assert [record["id"] for record in selected] == ["PPS-2", "PPS-1"]


def test_competition_product_fact_uses_exact_codes_conservatively(tmp_path) -> None:
    index_path = tmp_path / "products.json"
    index_path.write_text(
        json.dumps({"products": {"1111169701": {"세부품명": "잡석"}}}, ensure_ascii=False),
        encoding="utf-8",
    )
    products = load_competition_product_index(index_path)
    record = _record()
    record["meta"]["세부품명번호목록"] = "잡석[1111169701]"
    assert competition_product_fact(record, products)["status"] == "matched"
    record["meta"]["세부품명번호목록"] = "다른품명[9999999999]"
    assert competition_product_fact(record, products)["status"] == "not_matched"
    record["meta"]["세부품명번호목록"] = None
    assert competition_product_fact(record, products)["status"] == "unknown"


def test_competition_product_fact_preserves_conditions_and_source_provenance(
    tmp_path,
) -> None:
    index_path = tmp_path / "products.json"
    index_path.write_text(
        json.dumps(
            {
                "products": {
                    "9015189001": {
                        "세부품명": "축제기획및대행서비스",
                        "제품명번호": "901518",
                        "제품명": "축제",
                        "특이사항": "추정가격 3억원 미만에 한함",
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    products = load_competition_product_index(index_path)
    record = _record()
    record["meta"]["세부품명번호목록"] = "축제기획및대행서비스[9015189001]"
    record["docs"][0]["text"] = "세부품명번호 9015189001"

    fact = competition_product_fact(record, products)

    product = fact["matched_products"][0]
    assert product["특이사항"] == "추정가격 3억원 미만에 한함"
    assert product["metadata_match"] is True
    assert product["document_match_sources"] == [
        {"doc_id": "D0", "type": "공고문"}
    ]
