#!/usr/bin/env python3
"""Offline audit for citation-bounded legal context (INC-023).

This script makes no model/API calls.  It turns the organizer item table into a
conservative review manifest: an article is emitted as resolved only when the
cited source and its ``제N조`` header each occur uniquely in the organizer's
law corpus.  Everything else is explicitly left for manual boundary review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

ARTICLE_HEADER = re.compile(r"(?m)^제(?P<article>\d+조(?:의\d+)?)(?:\s*\([^\n]*\))?")
ARTICLE_CITATION = re.compile(r"제(\d+조(?:의\d+)?)")

# Citation aliases are organizer-table wording -> organizer file name.  The
# mapping is deliberately narrow: an unknown or compound citation is review
# work, not an invitation to synthesize a legal context.
SOURCE_ALIASES = {
    "국가를 당사자로 하는 계약에 관한 법률 시행령": "국가를 당사자로 하는 계약에 관한 법률 시행령.txt",
    "국가계약법 시행령": "국가를 당사자로 하는 계약에 관한 법률 시행령.txt",
    "국가를 당사자로 하는 계약에 관한 법률 시행규칙": "국가를 당사자로 하는 계약에 관한 법률 시행규칙.txt",
    "국가계약법 시행규칙": "국가를 당사자로 하는 계약에 관한 법률 시행규칙.txt",
    "국가를 당사자로 하는 계약에 관한 법률": "국가를 당사자로 하는 계약에 관한 법률.txt",
    "지방자치단체를 당사자로 하는 계약에 관한 법률 시행령": "지방자치단체를 당사자로 하는 계약에 관한 법률 시행령.txt",
    "지방계약법 시행령": "지방자치단체를 당사자로 하는 계약에 관한 법률 시행령.txt",
    "지방계약법시행령": "지방자치단체를 당사자로 하는 계약에 관한 법률 시행령.txt",
    "지방자치단체를 당사자로 하는 계약에 관한 법률 시행규칙": "지방자치단체를 당사자로 하는 계약에 관한 법률 시행규칙.txt",
    "지방계약 법시행규칙": "지방자치단체를 당사자로 하는 계약에 관한 법률 시행규칙.txt",
    "지방계약법 시행규칙": "지방자치단체를 당사자로 하는 계약에 관한 법률 시행규칙.txt",
    "지방자치단체를 당사자로 하는 계약에 관한 법률": "지방자치단체를 당사자로 하는 계약에 관한 법률.txt",
    "중소기업제품 구매촉진 및 판로지원에 관한 법률 시행령": "중소기업제품 구매촉진 및 판로지원에 관한 법률 시행령.txt",
    "중소기업제품 구매촉진 및 판로지원에 관한 법률 시행규칙": "중소기업제품 구매촉진 및 판로지원에 관한 법률 시행규칙.txt",
    "중소기업제품 구매촉진 및 판로지원에 관한 법률": "중소기업제품 구매촉진 및 판로지원에 관한 법률.txt",
    "중소기업자간 경쟁제품 및 공사용자재 직접구매 대상 품목 지정 내역": "중소기업자간 경쟁제품 및 공사용자재 직접구매 대상 품목 지정 내역.txt",
    "중소기업자간 경쟁제품 직접생산 확인기준": "중소기업자간 경쟁제품 직접생산 확인기준.txt",
    "중소 소프트웨어사업자의 사업 참여 지원에 관한 지침": "중소 소프트웨어사업자의 사업 참여 지원에 관한 지침.txt",
    "소프트웨어 진흥법 시행령": "소프트웨어 진흥법 시행령.txt",
    "소프트웨어 진흥법": "소프트웨어 진흥법.txt",
    "소프트웨어진흥법": "소프트웨어 진흥법.txt",
    "지방자치단체 입찰 및 계약 집행기준": "지방자치단체 입찰 및 계약 집행기준.txt",
    "(계약예규) 정부 입찰·계약 집행기준": "(계약예규) 정부 입찰·계약 집행기준.txt",
    "정부 입찰·계약 집행기준": "(계약예규) 정부 입찰·계약 집행기준.txt",
    "정부입찰계약집행기준": "(계약예규) 정부 입찰·계약 집행기준.txt",
    "(계약예규) 공동계약운용요령": "(계약예규) 공동계약운용요령.txt",
    "공동계약운용요령": "(계약예규) 공동계약운용요령.txt",
    "국가를 당사자로하는 계약에 관한 법률 등의 재정경제부장관이 정하는 고시금액": "국가를 당사자로 하는 계약에 관한 법률 등의 재정경제부장관이 정하는 고시금액.txt",
    "지방자치단체 입찰시 낙찰자 결정기준": "지방자치단체 입찰시 낙찰자 결정기준.txt",
}


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def source_mentions(citation: str) -> list[tuple[int, int, str, str]]:
    """Return non-overlapping longest aliases in citation order."""
    matches: list[tuple[int, int, str, str]] = []
    occupied: list[tuple[int, int]] = []
    for alias in sorted(SOURCE_ALIASES, key=len, reverse=True):
        for found in re.finditer(re.escape(alias), citation):
            span = found.span()
            if any(span[0] < end and start < span[1] for start, end in occupied):
                continue
            occupied.append(span)
            matches.append((span[0], span[1], alias, SOURCE_ALIASES[alias]))
    return sorted(matches)


def active_body(text: str) -> str:
    """Ignore historical appendices after the first current-law supplementary act."""
    marker = re.search(r"(?m)^부칙", text)
    return text[:marker.start()] if marker else text


def article_headers(text: str, article: str) -> list[re.Match[str]]:
    return [match for match in ARTICLE_HEADER.finditer(active_body(text)) if match.group("article") == article]


def load_sources(law_dir: Path) -> dict[str, str]:
    return {path.name: path.read_text(encoding="utf-8") for path in law_dir.glob("*.txt")}


def audit_citation(
    item: str,
    jurisdiction: str,
    citation: str,
    sources: dict[str, str],
) -> list[dict[str, Any]]:
    if not citation.strip():
        return [{"item": item, "jurisdiction": jurisdiction, "citation": citation, "status": "no_citation"}]
    mentions = source_mentions(citation)
    if not mentions:
        return [{"item": item, "jurisdiction": jurisdiction, "citation": citation, "status": "unmapped_source"}]
    rows: list[dict[str, Any]] = []
    for index, (start, end, alias, filename) in enumerate(mentions):
        segment_end = mentions[index + 1][0] if index + 1 < len(mentions) else len(citation)
        section = citation[start:segment_end]
        cited_articles = ARTICLE_CITATION.findall(section)
        base = {
            "item": item,
            "jurisdiction": jurisdiction,
            "citation": citation,
            "citation_alias": alias,
            "source_file": filename,
        }
        if filename not in sources:
            rows.append({**base, "status": "source_file_missing"})
            continue
        if not cited_articles:
            rows.append({**base, "status": "manual_boundary_required", "reason": "citation_has_no_article_number"})
            continue
        for article in cited_articles:
            headers = article_headers(sources[filename], article)
            if len(headers) != 1:
                rows.append({
                    **base,
                    "article": f"제{article}",
                    "status": "article_not_found" if not headers else "ambiguous_article_number",
                    "header_match_count": len(headers),
                })
                continue
            header = headers[0]
            body = active_body(sources[filename])
            all_headers = list(ARTICLE_HEADER.finditer(body))
            header_index = next(
                index for index, candidate in enumerate(all_headers)
                if candidate.start() == header.start()
            )
            end_offset = all_headers[header_index + 1].start() if header_index + 1 < len(all_headers) else len(body)
            unit = body[header.start():end_offset].strip()
            rows.append({
                **base,
                "article": f"제{article}",
                "status": "resolved_unique_article",
                "start_offset": header.start(),
                "end_offset": end_offset,
                "unit_char_count": len(unit),
                # Exact token admission is a property of the packaged Gemma
                # runtime.  It is deliberately not approximated by character
                # length when that tokenizer is unavailable in this workspace.
                "unit_token_count": None,
                "token_count_status": "pending_submission_tokenizer",
                "unit_sha256": sha256(unit),
            })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config_path = root() / args.config
    config = json.loads(config_path.read_text(encoding="utf-8"))
    data_root = root() / config["data_root"]
    law_dir = root() / config["law_directory"]
    table_path = data_root / "data/항목표.json"
    table = json.loads(table_path.read_text(encoding="utf-8"))["항목"]
    sources = load_sources(law_dir)
    rows: list[dict[str, Any]] = []
    for item, value in table.items():
        for jurisdiction in ("국가계약법", "지방계약법"):
            rows.extend(audit_citation(item, jurisdiction, value.get(jurisdiction, ""), sources))
    statuses = Counter(row["status"] for row in rows)
    by_item = {
        item: dict(Counter(row["status"] for row in rows if row["item"] == item))
        for item in table
    }
    report = {
        "experiment_id": config["experiment_id"],
        "method": "offline conservative citation-to-complete-article audit; no API calls",
        "policy": "Only a unique cited article in an organizer source is resolved. Compound/no-article citations require manual boundary review.",
        "submission_tokenizer": config["model_tokenizer"],
        "token_count_note": "Exact token counts are pending the submission runtime tokenizer; character counts are recorded only as source-unit audit facts, never as admission thresholds.",
        "source_sha256": {
            "item_table": sha256(table_path.read_text(encoding="utf-8")),
            **{name: sha256(text) for name, text in sorted(sources.items())},
        },
        "status_counts": dict(sorted(statuses.items())),
        "by_item": by_item,
        "records": rows,
    }
    output = root() / config["output_path"]
    write_json(output, report)
    print(json.dumps({"output": str(output), "status_counts": report["status_counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
