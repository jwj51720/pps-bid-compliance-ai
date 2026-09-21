#!/usr/bin/env python3
"""Create an exact detail-product-code index from organizer-provided CSV."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data/derived/competition_products_v1.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _default_source() -> Path:
    candidates = list((ROOT / "data/raw/open/data").rglob("*.csv"))
    for path in candidates:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            if {"세부품명번호", "세부품명"} <= set((csv.DictReader(handle).fieldnames or [])):
                return path
    raise FileNotFoundError("organizer competition-product CSV was not found")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    source = args.source.resolve() if args.source else _default_source()
    with source.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    products = {
        row["세부품명번호"]: {
            "세부품명": row["세부품명"],
            "제품명번호": row["제품명번호"],
            "제품명": row["제품명"],
            "특이사항": row["특이사항"],
        }
        for row in rows
        if row["세부품명번호"].strip()
    }
    if any(len(code) != 10 or not code.isdigit() for code in products):
        raise ValueError("competition-product CSV has an invalid 세부품명번호")
    if len(products) != len({row["세부품명번호"] for row in rows if row["세부품명번호"].strip()}):
        raise ValueError("duplicate 세부품명번호 in competition-product CSV")
    payload = {
        "schema_version": 1,
        "artifact": "competition_products_v1",
        "source": str(source.relative_to(ROOT)),
        "source_sha256": _sha256(source),
        "products": products,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output} ({len(products)} exact product codes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
