"""Final V/E validation without hidden label mutation."""

from __future__ import annotations

from collections import Counter
import unicodedata
from typing import Any, Mapping, Sequence


ABSENCE = {"v10", "v11", "v16", "v18", "v20"}
COLUMNS = ["id"] + [f"v{i}" for i in range(1, 25)] + [f"e{i}" for i in range(1, 25)]


def clean_final_rows(
    records: Sequence[Mapping[str, Any]],
    candidate: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ids = [str(record["id"]) for record in records]
    if set(candidate) != set(ids):
        raise ValueError("candidate/input ID coverage differs")
    removed: Counter[str] = Counter()
    missing: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []
    for record in records:
        notice_id = str(record["id"])
        source_texts = [str(document["text"]) for document in record["docs"]]
        source = candidate[notice_id]
        row: dict[str, Any] = {"id": notice_id}
        for index in range(1, 25):
            item = f"v{index}"
            value = source.get(item)
            if type(value) is not int or value not in (0, 1):
                raise ValueError(f"{notice_id}/{item}: verdict is not binary int")
            row[item] = value
        for index in range(1, 25):
            item, key = f"v{index}", f"e{index}"
            original = source.get(key, "")
            if not isinstance(original, str):
                raise ValueError(f"{notice_id}/{key}: evidence is not a string")
            text = unicodedata.normalize("NFC", original)
            valid = bool(
                row[item] == 1 and item not in ABSENCE and text
                and len(text) <= 500 and not text.startswith(("=", "+", "@"))
                and any(text in source_text for source_text in source_texts)
            )
            row[key] = text if valid else ""
            removed[item] += int(bool(original) and not row[key])
            missing[item] += int(row[item] == 1 and item not in ABSENCE and not row[key])
        if list(row) != COLUMNS:
            raise ValueError("final row column order differs")
        rows.append(row)
    return rows, {
        "removed_invalid": dict(+removed),
        "positive_without_evidence": dict(+missing),
        "label_mutations": 0,
    }
