"""Exact organizer product-code facts; no product applicability decision."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Mapping


CODE_PATTERN = re.compile(r"[0-9]{10}\Z")
ENTRY_PATTERN = re.compile(
    r"(?:^|,\s*)([^\[\]]+?)\s*\[([0-9]{10}|[0-9]{8})\](?=\s*(?:,|$))"
)


@dataclass(frozen=True)
class ProductCodeFact:
    code: str
    supplied_name: str
    csv_name: str | None
    special_note: str | None


def parse_supplied_product_codes(value: Any) -> tuple[tuple[str, str], ...]:
    """Read organizer metadata entries without guessing from product names."""
    if value is None or value == "":
        return ()
    if not isinstance(value, str):
        raise ValueError("product-code metadata must be a string or null")
    parsed: list[tuple[str, str]] = []
    seen: set[str] = set()
    cursor = 0
    for match in ENTRY_PATTERN.finditer(value):
        if match.start() != cursor:
            raise ValueError("unparseable product-code metadata entry")
        name, code = match.groups()
        name = name.strip()
        if not name:
            raise ValueError("product-code metadata entry has an empty name")
        if code not in seen:
            seen.add(code)
            parsed.append((code, name))
        cursor = match.end()
    if cursor != len(value) or not parsed:
        raise ValueError("unparseable product-code metadata entry")
    return tuple(parsed)


def load_product_index(path: str | Path) -> dict[str, dict[str, str]]:
    """Load only the organizer exact-code index, validating its shape."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("artifact") != "competition_products_v1":
        raise ValueError("unexpected organizer product-index artifact")
    products = raw.get("products")
    if not isinstance(products, dict):
        raise ValueError("product index must contain a products object")
    index: dict[str, dict[str, str]] = {}
    for code, row in products.items():
        if not isinstance(code, str) or CODE_PATTERN.fullmatch(code) is None:
            raise ValueError("invalid product-index code")
        if not isinstance(row, dict):
            raise ValueError("invalid product-index row")
        name = row.get("세부품명")
        note = row.get("특이사항")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("product-index row lacks 세부품명")
        if note is not None and not isinstance(note, str):
            raise ValueError("product-index 특이사항 must be text or null")
        index[code] = {"세부품명": name, "특이사항": note or ""}
    return index


def build_product_facts(
    metadata: Mapping[str, Any], index: Mapping[str, Mapping[str, str]],
) -> tuple[ProductCodeFact, ...]:
    facts: list[ProductCodeFact] = []
    for code, supplied_name in parse_supplied_product_codes(
        metadata.get("세부품명번호목록")
    ):
        row = index.get(code)
        facts.append(ProductCodeFact(
            code=code,
            supplied_name=supplied_name,
            csv_name=row["세부품명"] if row is not None else None,
            special_note=(row.get("특이사항") or None) if row is not None else None,
        ))
    return tuple(facts)


def render_product_facts(facts: tuple[ProductCodeFact, ...]) -> str:
    """Render source facts, not a product-applicability or violation label."""
    if not facts:
        return "공고 메타데이터에 세부품명번호가 제공되지 않았습니다."
    lines = ["공고 메타데이터와 주최측 경쟁제품 CSV의 세부품명번호 대조:"]
    for fact in facts:
        if fact.csv_name is None:
            lines.append(
                f"- 공고 제공 품명 {fact.supplied_name} ({fact.code}): "
                "CSV에 정확히 일치하는 행이 없습니다."
            )
            continue
        line = (
            f"- 공고 제공 품명 {fact.supplied_name} ({fact.code}): "
            f"CSV 세부품명 {fact.csv_name}과 정확히 일치합니다."
        )
        if fact.special_note:
            line += f" CSV 특이사항 원문: {fact.special_note}"
        lines.append(line)
    return "\n".join(lines)
