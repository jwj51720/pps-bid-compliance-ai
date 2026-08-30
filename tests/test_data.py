from __future__ import annotations

import gzip
import json

from src.data import load_records, profile_records


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
