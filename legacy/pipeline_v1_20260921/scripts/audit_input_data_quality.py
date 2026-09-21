#!/usr/bin/env python3
"""Audit organizer input integrity separately from downstream prompt coverage."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, TextIO

DOCUMENT_TYPES = ("공고문", "규격서", "과업지시서", "제안요청서", "예외공표서")
DOCUMENT_ORDER = {name: index for index, name in enumerate(DOCUMENT_TYPES)}
REQUIRED_RECORD_KEYS = {
    "id", "docs", "meta", "dropped_doc_counts", "input_completeness",
    "anon_applied", "assembly_policy_version",
}
REQUIRED_META_KEYS = {
    "적용계약법", "업무구분", "계약방법", "낙찰방법", "낙찰하한율",
    "배정예산금액", "입찰추정가격", "소관구분", "공동도급구성방식",
    "정보화사업여부", "세부품명번호목록", "제한지역코드목록", "지역제한여부",
    "면허업종제한목록", "업종제한여부", "조항호내용", "공고게시일자",
    "개찰예정일자", "긴급공고여부", "입찰방법", "조달방식",
}
EXPECTED_LABEL_COLUMNS = (
    ["id"] + [f"v{i}" for i in range(1, 25)] + [f"e{i}" for i in range(1, 25)]
)
ABSENCE_ITEMS = {10, 11, 16, 18, 20}


def _open_text(path: Path) -> TextIO:
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open(encoding="utf-8")


def _append(errors: list[str], message: str, limit: int = 50) -> None:
    if len(errors) < limit:
        errors.append(message)


def audit_dataset(input_path: Path, labels_path: Path | None = None) -> dict[str, Any]:
    ids: list[str] = []
    texts_by_id: dict[str, str] = {}
    errors: list[str] = []
    document_types: Counter[str] = Counter()
    dropped: Counter[str] = Counter()
    affected_by_drop = 0
    empty_documents = 0
    duplicate_doc_id_notices = 0
    non_nfc_documents = 0
    unordered_notices = 0
    incomplete_notices = 0
    anonymous_notices = 0

    with _open_text(input_path) as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                _append(errors, f"line {line_number}: invalid JSON: {exc}")
                continue
            if not isinstance(record, dict):
                _append(errors, f"line {line_number}: record is not an object")
                continue
            missing_record = REQUIRED_RECORD_KEYS - set(record)
            if missing_record:
                _append(errors, f"line {line_number}: missing record keys {sorted(missing_record)}")
                continue
            record_id = record.get("id")
            if not isinstance(record_id, str) or not record_id:
                _append(errors, f"line {line_number}: invalid id")
                continue
            ids.append(record_id)
            meta = record.get("meta")
            if not isinstance(meta, dict):
                _append(errors, f"{record_id}: meta is not an object")
            else:
                missing_meta = REQUIRED_META_KEYS - set(meta)
                extra_meta = set(meta) - REQUIRED_META_KEYS
                if missing_meta or extra_meta:
                    _append(
                        errors,
                        f"{record_id}: meta schema drift missing={sorted(missing_meta)} "
                        f"extra={sorted(extra_meta)}",
                    )

            documents = record.get("docs")
            if not isinstance(documents, list) or not documents:
                _append(errors, f"{record_id}: docs is not a non-empty list")
                continue
            doc_ids: list[str] = []
            ordered_types: list[int] = []
            texts: list[str] = []
            for index, document in enumerate(documents):
                if not isinstance(document, dict):
                    _append(errors, f"{record_id}: document {index} is not an object")
                    continue
                if not {"doc_id", "type", "text"} <= set(document):
                    _append(errors, f"{record_id}: document {index} schema is incomplete")
                    continue
                doc_id, doc_type, text = (
                    document.get("doc_id"), document.get("type"), document.get("text")
                )
                if not all(isinstance(value, str) for value in (doc_id, doc_type, text)):
                    _append(errors, f"{record_id}: document {index} values must be strings")
                    continue
                doc_ids.append(doc_id)
                document_types[doc_type] += 1
                if doc_type not in DOCUMENT_ORDER:
                    _append(errors, f"{record_id}: unsupported document type {doc_type!r}")
                else:
                    ordered_types.append(DOCUMENT_ORDER[doc_type])
                if not text.strip():
                    empty_documents += 1
                    _append(errors, f"{record_id}/{doc_id}: empty document text")
                if text != unicodedata.normalize("NFC", text):
                    non_nfc_documents += 1
                    _append(errors, f"{record_id}/{doc_id}: document text is not NFC")
                texts.append(text)
            if len(doc_ids) != len(set(doc_ids)):
                duplicate_doc_id_notices += 1
                _append(errors, f"{record_id}: duplicate doc_id within notice")
            if not any(document.get("type") == "공고문" for document in documents if isinstance(document, dict)):
                _append(errors, f"{record_id}: announcement document missing")
            if ordered_types != sorted(ordered_types):
                unordered_notices += 1
            texts_by_id[record_id] = "\n".join(texts)

            dropped_counts = record.get("dropped_doc_counts")
            if not isinstance(dropped_counts, dict):
                _append(errors, f"{record_id}: dropped_doc_counts is not an object")
                dropped_counts = {}
            dropped_total = 0
            for doc_type, value in dropped_counts.items():
                if doc_type not in DOCUMENT_ORDER or not isinstance(value, int) or value < 0:
                    _append(errors, f"{record_id}: invalid dropped count {doc_type}={value!r}")
                    continue
                dropped[doc_type] += value
                dropped_total += value
            if dropped_total:
                affected_by_drop += 1
            completeness = record.get("input_completeness")
            if not isinstance(completeness, dict):
                _append(errors, f"{record_id}: input_completeness is not an object")
            else:
                expected_complete = dropped_total == 0
                if completeness.get("공고문_실재") is not True:
                    _append(errors, f"{record_id}: 공고문_실재 is not true")
                if completeness.get("추출_성공") is not True:
                    _append(errors, f"{record_id}: 추출_성공 is not true")
                if completeness.get("무탈락") is not expected_complete:
                    _append(errors, f"{record_id}: 무탈락 conflicts with dropped_doc_counts")
                if completeness.get("완전관측") is not expected_complete:
                    _append(errors, f"{record_id}: 완전관측 conflicts with dropped_doc_counts")
                if not expected_complete:
                    incomplete_notices += 1
            if record.get("anon_applied") is True:
                anonymous_notices += 1

    duplicates = sorted(key for key, count in Counter(ids).items() if count > 1)
    if duplicates:
        _append(errors, f"duplicate record ids: {duplicates[:10]}")

    label_result: dict[str, Any] | None = None
    if labels_path is not None:
        with labels_path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            label_rows = list(reader)
            columns = reader.fieldnames or []
        label_ids = [row.get("id", "") for row in label_rows]
        label_errors: list[str] = []
        if columns != EXPECTED_LABEL_COLUMNS:
            _append(label_errors, f"unexpected label columns: {columns}")
        if len(label_ids) != len(set(label_ids)):
            _append(label_errors, "duplicate label ids")
        missing_labels = sorted(set(ids) - set(label_ids))
        orphan_labels = sorted(set(label_ids) - set(ids))
        if missing_labels or orphan_labels:
            _append(
                label_errors,
                f"input/label ID mismatch missing={missing_labels[:10]} orphan={orphan_labels[:10]}",
            )
        invalid_v = 0
        invalid_evidence = 0
        blank_positive_evidence = 0
        for row in label_rows:
            record_id = row.get("id", "")
            source = texts_by_id.get(record_id, "")
            for number in range(1, 25):
                value = row.get(f"v{number}", "")
                evidence = row.get(f"e{number}", "")
                if value not in {"0", "1"}:
                    invalid_v += 1
                if value == "0" and evidence:
                    invalid_evidence += 1
                if number in ABSENCE_ITEMS and evidence:
                    invalid_evidence += 1
                if evidence and (
                    len(evidence) > 500
                    or evidence not in source
                    or evidence != unicodedata.normalize("NFC", evidence)
                    or evidence[0] in "=+@"
                ):
                    invalid_evidence += 1
                if value == "1" and number not in ABSENCE_ITEMS and not evidence:
                    blank_positive_evidence += 1
        if invalid_v:
            _append(label_errors, f"invalid v cells: {invalid_v}")
        if invalid_evidence:
            _append(label_errors, f"invalid nonblank evidence cells: {invalid_evidence}")
        errors.extend(label_errors)
        label_result = {
            "row_count": len(label_rows),
            "column_count": len(columns),
            "id_join_exact": set(ids) == set(label_ids),
            "invalid_v_cells": invalid_v,
            "invalid_nonblank_evidence_cells": invalid_evidence,
            "blank_nonabsence_positive_evidence_cells": blank_positive_evidence,
        }

    return {
        "input": str(input_path),
        "status": "pass" if not errors else "fail",
        "record_count": len(ids),
        "unique_id_count": len(set(ids)),
        "document_count": sum(document_types.values()),
        "document_type_counts": dict(document_types),
        "empty_document_count": empty_documents,
        "duplicate_doc_id_notice_count": duplicate_doc_id_notices,
        "non_nfc_document_count": non_nfc_documents,
        "source_order_notices": unordered_notices,
        "anonymous_notice_count": anonymous_notices,
        "upstream_missingness": {
            "affected_notice_count": affected_by_drop,
            "affected_notice_rate": affected_by_drop / len(ids) if ids else 0.0,
            "not_fully_observed_count": incomplete_notices,
            "dropped_document_counts": dict(dropped),
            "is_pipeline_error": False,
        },
        "labels": label_result,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--labels")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = audit_dataset(
        Path(args.input), Path(args.labels) if args.labels else None
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
