"""Official competition data loading, validation, and profiling."""

from __future__ import annotations

import csv
import gzip
import json
import statistics
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Iterator

REQUIRED_RECORD_KEYS = {
    "id",
    "docs",
    "meta",
    "dropped_doc_counts",
    "input_completeness",
    "anon_applied",
    "assembly_policy_version",
}
REQUIRED_DOC_KEYS = {"doc_id", "type", "text"}


def _open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open(encoding="utf-8")


def validate_record(record: Any) -> None:
    if not isinstance(record, dict):
        raise ValueError("record must be an object")
    missing = REQUIRED_RECORD_KEYS - record.keys()
    if missing:
        raise ValueError(f"record missing keys: {sorted(missing)}")
    if not isinstance(record["id"], str) or not record["id"]:
        raise ValueError("record id must be a non-empty string")
    if not isinstance(record["docs"], list) or not record["docs"]:
        raise ValueError(f"docs must be a non-empty list: {record['id']}")
    for document in record["docs"]:
        if not isinstance(document, dict) or not REQUIRED_DOC_KEYS <= document.keys():
            raise ValueError(f"invalid document schema: {record['id']}")
        if not all(isinstance(document[key], str) for key in REQUIRED_DOC_KEYS):
            raise ValueError(f"document values must be strings: {record['id']}")
    if not any(document["type"] == "공고문" for document in record["docs"]):
        raise ValueError(f"notice document missing: {record['id']}")
    if not isinstance(record["meta"], dict):
        raise ValueError(f"meta must be an object: {record['id']}")


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    for document in record["docs"]:
        for key in REQUIRED_DOC_KEYS:
            document[key] = unicodedata.normalize("NFC", document[key])
    return record


def iter_records(path: str | Path, limit: int | None = None) -> Iterator[dict[str, Any]]:
    source = Path(path)
    count = 0
    with _open_text(source) as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{source}:{line_number}: invalid JSON: {exc}") from exc
            validate_record(record)
            yield normalize_record(record)
            count += 1
            if limit is not None and count >= limit:
                return


def load_records(path: str | Path, limit: int | None = None) -> list[dict[str, Any]]:
    records = list(iter_records(path, limit=limit))
    ids = [record["id"] for record in records]
    if len(ids) != len(set(ids)):
        duplicates = sorted(key for key, count in Counter(ids).items() if count > 1)
        raise ValueError(f"duplicate record ids: {duplicates[:10]}")
    return records


def load_item_table(path: str | Path) -> dict[str, dict[str, Any]]:
    with Path(path).open(encoding="utf-8") as handle:
        data = json.load(handle)
    items = data.get("항목")
    if not isinstance(items, dict) or set(items) != {f"v{i}" for i in range(1, 25)}:
        raise ValueError("item table must define exactly v1 through v24")
    return items


def load_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def full_document_text(record: dict[str, Any]) -> str:
    return "\n".join(document["text"] for document in record["docs"])


def _quantile(values: list[int], probability: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _summary(values: list[int]) -> dict[str, float | int]:
    return {
        "mean": round(statistics.fmean(values), 2) if values else 0.0,
        "median": round(statistics.median(values), 2) if values else 0.0,
        "p90": round(_quantile(values, 0.90), 2),
        "p95": round(_quantile(values, 0.95), 2),
        "max": max(values, default=0),
    }


def profile_records(path: str | Path) -> dict[str, Any]:
    ids: list[str] = []
    record_keys: set[str] = set()
    document_counts: list[int] = []
    total_chars: list[int] = []
    document_type_counts: Counter[str] = Counter()
    document_type_chars: defaultdict[str, list[int]] = defaultdict(list)
    meta_types: defaultdict[str, Counter[str]] = defaultdict(Counter)
    meta_nulls: Counter[str] = Counter()
    meta_examples: defaultdict[str, list[Any]] = defaultdict(list)
    incomplete = 0
    dropped = 0

    for record in iter_records(path):
        ids.append(record["id"])
        record_keys.update(record.keys())
        lengths = [len(document["text"]) for document in record["docs"]]
        document_counts.append(len(lengths))
        total_chars.append(sum(lengths))
        for document, length in zip(record["docs"], lengths):
            document_type_counts[document["type"]] += 1
            document_type_chars[document["type"]].append(length)
        for key, value in record["meta"].items():
            meta_types[key][type(value).__name__] += 1
            if value is None:
                meta_nulls[key] += 1
            elif len(meta_examples[key]) < 3 and value not in meta_examples[key]:
                meta_examples[key].append(value)
        completeness = record.get("input_completeness", {})
        fully_observed = completeness.get("완전관측", completeness.get("fully_observed", True))
        incomplete += int(not bool(fully_observed))
        dropped += int(bool(record.get("dropped_doc_counts")))

    count = len(ids)
    return {
        "path": str(path),
        "record_count": count,
        "unique_id_count": len(set(ids)),
        "duplicate_id_count": count - len(set(ids)),
        "record_keys": sorted(record_keys),
        "records_with_dropped_documents": dropped,
        "records_not_fully_observed": incomplete,
        "documents_per_record": _summary(document_counts),
        "characters_per_record": _summary(total_chars),
        "document_types": {
            key: {"count": document_type_counts[key], "characters": _summary(document_type_chars[key])}
            for key in sorted(document_type_counts)
        },
        "meta": {
            key: {
                "types": dict(meta_types[key]),
                "null_count": meta_nulls[key],
                "null_rate": round(meta_nulls[key] / count, 6) if count else 0.0,
                "examples": meta_examples[key],
            }
            for key in sorted(meta_types)
        },
    }


def label_distribution(rows: Iterable[dict[str, str]]) -> dict[str, int]:
    materialized = list(rows)
    return {f"v{i}": sum(int(row[f"v{i}"]) for row in materialized) for i in range(1, 25)}
