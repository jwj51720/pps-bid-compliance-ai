"""Strict organizer JSONL loader and source-ledger constructor."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

from ..domain import NoticeDocument, NoticeRecord


def load_notice_records(path: str | Path) -> list[NoticeRecord]:
    records: list[NoticeRecord] = []
    seen: set[str] = set()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            raw: dict[str, Any] = json.loads(line)
            notice_id = raw.get("id")
            if not isinstance(notice_id, str) or not notice_id:
                raise ValueError(f"line {line_number}: invalid notice id")
            if notice_id in seen:
                raise ValueError(f"duplicate notice id: {notice_id}")
            seen.add(notice_id)
            docs_raw = raw.get("docs")
            if not isinstance(docs_raw, list) or not docs_raw:
                raise ValueError(f"{notice_id}: docs must be a nonempty list")
            documents = tuple(
                NoticeDocument.from_raw(notice_id, order, document)
                for order, document in enumerate(docs_raw)
            )
            if len({document.doc_id for document in documents}) != len(documents):
                raise ValueError(f"{notice_id}: duplicate document id")
            metadata = raw.get("meta")
            if not isinstance(metadata, dict):
                raise ValueError(f"{notice_id}: meta must be an object")
            records.append(NoticeRecord(
                notice_id=notice_id,
                documents=documents,
                metadata=metadata,
                input_completeness=raw.get("input_completeness") or {},
                dropped_document_counts=raw.get("dropped_doc_counts") or {},
                raw=raw,
            ))
    if not records:
        raise ValueError("input JSONL is empty")
    return records
