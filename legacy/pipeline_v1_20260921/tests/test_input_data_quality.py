from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path

from scripts.audit_input_data_quality import (
    EXPECTED_LABEL_COLUMNS,
    REQUIRED_META_KEYS,
    audit_dataset,
)


def _record(record_id: str = "PPS-1") -> dict:
    return {
        "id": record_id,
        "docs": [{"doc_id": "D0", "type": "공고문", "text": "참가자격 문구"}],
        "meta": {key: None for key in REQUIRED_META_KEYS},
        "dropped_doc_counts": {},
        "input_completeness": {
            "공고문_실재": True,
            "추출_성공": True,
            "무탈락": True,
            "완전관측": True,
        },
        "anon_applied": True,
        "assembly_policy_version": "test",
    }


def _write_input(path: Path, records: list[dict]) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _write_labels(path: Path, record_id: str) -> None:
    row = {column: "" for column in EXPECTED_LABEL_COLUMNS}
    row["id"] = record_id
    for number in range(1, 25):
        row[f"v{number}"] = "0"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPECTED_LABEL_COLUMNS)
        writer.writeheader()
        writer.writerow(row)


def test_input_quality_audit_accepts_complete_organizer_record(tmp_path: Path) -> None:
    input_path = tmp_path / "input.jsonl.gz"
    labels_path = tmp_path / "labels.csv"
    _write_input(input_path, [_record()])
    _write_labels(labels_path, "PPS-1")

    result = audit_dataset(input_path, labels_path)

    assert result["status"] == "pass"
    assert result["record_count"] == 1
    assert result["labels"]["id_join_exact"] is True


def test_input_quality_audit_reports_upstream_drop_without_calling_it_pipeline_error(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "input.jsonl.gz"
    record = _record()
    record["dropped_doc_counts"] = {"제안요청서": 1}
    record["input_completeness"]["무탈락"] = False
    record["input_completeness"]["완전관측"] = False
    _write_input(input_path, [record])

    result = audit_dataset(input_path)

    assert result["status"] == "pass"
    assert result["upstream_missingness"]["affected_notice_count"] == 1
    assert result["upstream_missingness"]["dropped_document_counts"] == {"제안요청서": 1}
    assert result["upstream_missingness"]["is_pipeline_error"] is False


def test_input_quality_audit_rejects_schema_drift_and_bad_label_join(tmp_path: Path) -> None:
    input_path = tmp_path / "input.jsonl.gz"
    labels_path = tmp_path / "labels.csv"
    record = _record()
    record["meta"].pop("적용계약법")
    _write_input(input_path, [record])
    _write_labels(labels_path, "PPS-OTHER")

    result = audit_dataset(input_path, labels_path)

    assert result["status"] == "fail"
    assert any("meta schema drift" in error for error in result["errors"])
    assert any("ID mismatch" in error for error in result["errors"])
