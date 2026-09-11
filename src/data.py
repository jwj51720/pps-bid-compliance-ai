"""Official competition data loading, validation, and profiling."""

from __future__ import annotations

import csv
import gzip
import json
import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Iterator

PRODUCT_CODE = re.compile(r"\[(\d{10})\]")
DOCUMENT_CODE = re.compile(r"(?<!\d)(\d{10})(?!\d)")

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


def load_record_id_panel(path: str | Path) -> list[str]:
    """Load an ordered, versioned local-evaluation record panel."""
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    ids = payload.get("ids") if isinstance(payload, dict) else payload
    if not isinstance(ids, list) or not ids or not all(isinstance(value, str) for value in ids):
        raise ValueError("record ID panel must contain a non-empty JSON string list or an object with ids")
    if len(ids) != len(set(ids)):
        raise ValueError("record ID panel contains duplicate IDs")
    return ids


def select_records_by_id(records: list[dict[str, Any]], ids: list[str]) -> list[dict[str, Any]]:
    """Select records in the panel's fixed order, rejecting stale IDs."""
    records_by_id = {record["id"]: record for record in records}
    missing_ids = [record_id for record_id in ids if record_id not in records_by_id]
    if missing_ids:
        raise ValueError(f"record ID panel contains IDs absent from input: {missing_ids[:10]}")
    return [records_by_id[record_id] for record_id in ids]


def load_item_table(path: str | Path) -> dict[str, dict[str, Any]]:
    with Path(path).open(encoding="utf-8") as handle:
        data = json.load(handle)
    items = data.get("항목")
    if not isinstance(items, dict) or set(items) != {f"v{i}" for i in range(1, 25)}:
        raise ValueError("item table must define exactly v1 through v24")
    return items


def load_decision_cards(
    path: str | Path,
    item_table: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Load versioned prompt policy cards tied exactly to the official items."""
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    cards = payload.get("cards") if isinstance(payload, dict) else None
    if not isinstance(cards, dict) or set(cards) != set(item_table):
        raise ValueError("decision cards must define exactly the item-table v1 through v24 keys")
    for item, card in cards.items():
        if not isinstance(card, dict):
            raise ValueError(f"decision card must be an object: {item}")
        if card.get("item_name") != item_table[item]["항목명"]:
            raise ValueError(f"decision card item_name does not match item table: {item}")
        if not isinstance(card.get("prompt_text"), str) or not card["prompt_text"].strip():
            raise ValueError(f"decision card prompt_text must be non-empty: {item}")
        if "merge_contract" in card and not isinstance(card["merge_contract"], dict):
            raise ValueError(f"decision card merge_contract must be an object: {item}")
    return cards


def load_competition_product_index(path: str | Path) -> dict[str, dict[str, str]]:
    """Load an exact-code index derived from the organizer's product CSV."""
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    products = payload.get("products") if isinstance(payload, dict) else None
    if not isinstance(products, dict) or not products:
        raise ValueError("competition product index must contain a non-empty products mapping")
    for code, value in products.items():
        if not isinstance(code, str) or not re.fullmatch(r"\d{10}", code):
            raise ValueError("competition product index has an invalid detail product code")
        if not isinstance(value, dict) or not isinstance(value.get("세부품명"), str):
            raise ValueError("competition product index entry must contain 세부품명")
        for field in ("제품명번호", "제품명", "특이사항"):
            if field in value and not isinstance(value[field], str):
                raise ValueError(
                    f"competition product index entry {field} must be a string"
                )
    return products


def competition_product_fact(
    record: dict[str, Any], products: dict[str, dict[str, str]]
) -> dict[str, Any]:
    """Return a conservative organizer-data-only product applicability fact.

    Metadata codes establish both match and known non-match. Document codes are
    used only to establish a positive exact CSV match: an arbitrary ten-digit
    number in prose must not turn an unknown notice into a known non-match.
    """
    metadata_value = str(record["meta"].get("세부품명번호목록") or "")
    metadata_codes = sorted(set(PRODUCT_CODE.findall(metadata_value)))
    document_matches: dict[str, list[str]] = defaultdict(list)
    document_match_sources: dict[str, list[dict[str, str]]] = defaultdict(list)
    for document in record["docs"]:
        for code in set(DOCUMENT_CODE.findall(document["text"])) & set(products):
            document_matches[code].append(document["doc_id"])
            document_match_sources[code].append(
                {"doc_id": document["doc_id"], "type": document["type"]}
            )
    matched_codes = sorted((set(metadata_codes) | set(document_matches)) & set(products))
    if matched_codes:
        status = "matched"
    elif metadata_codes:
        status = "not_matched"
    else:
        status = "unknown"
    return {
        "status": status,
        "metadata_codes": metadata_codes,
        "matched_codes": matched_codes,
        "matched_products": [
            {
                "세부품명번호": code,
                "세부품명": products[code]["세부품명"],
                "제품명번호": products[code].get("제품명번호", ""),
                "제품명": products[code].get("제품명", ""),
                "특이사항": products[code].get("특이사항", ""),
                "metadata_match": code in metadata_codes,
                "document_match_sources": sorted(
                    document_match_sources.get(code, []),
                    key=lambda value: (value["type"], value["doc_id"]),
                ),
            }
            for code in matched_codes
        ],
        "document_match_doc_ids": {code: sorted(ids) for code, ids in document_matches.items()},
    }


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
