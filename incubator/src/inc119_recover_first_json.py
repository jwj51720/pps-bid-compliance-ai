#!/usr/bin/env python3
"""Recover a schema-valid first JSON object from an already recorded response.

This does not ask the model again.  For a repeated malformed row it deliberately
uses the earliest recorded raw response, so recovery cannot select a variant
after evaluating labels.
"""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "incubator/runs/inc119_gemma_legal_transfer16"
ITEMS = {f"v{index}" for index in range(1, 25)}


def first_json_object(text: str) -> dict[str, int]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
    decoder = json.JSONDecoder()
    value, _ = decoder.raw_decode(cleaned.lstrip())
    if set(value) != ITEMS or any(value[item] not in (0, 1) for item in ITEMS):
        raise ValueError("first object is not a 24-label schema")
    return value


def main() -> None:
    rows = [json.loads(line) for line in (RUN / "checkpoint.jsonl").read_text(encoding="utf-8").splitlines()]
    recovered = []
    seen_success = {(row["arm"], row["id"]) for row in rows if row.get("success")}
    seen_recovery: set[tuple[str, str]] = set()
    for row in rows:
        key = row["arm"], row["id"]
        if row.get("success") or key in seen_success or key in seen_recovery or not row.get("raw_response"):
            continue
        try:
            labels = first_json_object(row["raw_response"])
        except (ValueError, json.JSONDecodeError):
            continue
        seen_recovery.add(key)
        recovered.append({"id": row["id"], "arm": row["arm"], "labels": labels, "recovery": "earliest_raw_first_json_object", "source_checkpoint_order": rows.index(row)})
    (RUN / "deterministic_recovery.jsonl").write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in recovered) + ("\n" if recovered else ""), encoding="utf-8")
    print(json.dumps({"recovered": len(recovered), "rows": recovered}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
