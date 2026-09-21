#!/usr/bin/env python3
"""Build auditable, metadata-routable official-law bundles from organizer files.

The output is fixed context for a notice.  It intentionally excludes the
competition-product listing: the shared pipeline already converts the exact
organizer CSV lookup for each notice into a small, auditable product context.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.legal_groups import LEGAL_ITEM_GROUPS, validate_groups


LAW_DIR = ROOT / "data/raw/open/data/법령패키지/법령"
OUTPUT_DIR = ROOT / "data/derived/legal_reference_bundles_v1"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"


@dataclass(frozen=True)
class Chunk:
    key: str
    title: str
    source: str
    selector: str
    text: str


def _read(filename: str) -> str:
    return (LAW_DIR / filename).read_text(encoding="utf-8")


def _article(filename: str, number: str) -> str:
    text = _read(filename)
    heading = f"제{number}" if "조의" in number else f"제{number}조"
    start = re.search(rf"^{re.escape(heading)}\([^\n]+", text, re.MULTILINE)
    if start is None:
        raise ValueError(f"missing article {number}: {filename}")
    end = re.search(
        r"^제[0-9]+조(?:의[0-9]+)?\(", text[start.end() :], re.MULTILINE
    )
    return text[start.start() : start.end() + end.start() if end else len(text)].strip()


def _last_heading_range(filename: str, start: str, end: str) -> str:
    """Extract the final body occurrence, ignoring a preceding table of contents."""
    text = _read(filename)
    matches = list(re.finditer(re.escape(start), text))
    if not matches:
        raise ValueError(f"missing range start {start!r}: {filename}")
    begin = matches[-1].start()
    finish = text.find(end, begin + len(start))
    if finish < 0:
        raise ValueError(f"missing range end {end!r}: {filename}")
    return text[begin:finish].strip()


def _chunk_article(
    key: str, title: str, filename: str, number: str
) -> Chunk:
    return Chunk(key, title, filename, f"article_{number}", _article(filename, number))


def _chunk_range(
    key: str, title: str, filename: str, start: str, end: str
) -> Chunk:
    selector = f"last:{start} .. {end}"
    return Chunk(key, title, filename, selector, _last_heading_range(filename, start, end))


def _chapter_section_range(
    filename: str,
    chapter_heading: str,
    section_heading: str,
    next_section_heading: str,
) -> str:
    """Extract a section within one named chapter, not a same-named later section.

    Several government-guidance files repeat headings such as ``제3절`` in
    multiple chapters.  Selecting the last global occurrence silently chose
    chapter 10 for v23 although the item table names chapter 7.  Anchor the
    search to the final actual chapter body first, then locate its section.
    """
    text = _read(filename)
    # Ignore the table of contents and appendices which repeat the chapter
    # title.  The operative chapter body is followed immediately by 제1절.
    chapter_positions = [
        match.start()
        for match in re.finditer(
            re.escape(chapter_heading) + r"\n제1절", text
        )
    ]
    if not chapter_positions:
        raise ValueError(f"missing chapter {chapter_heading!r}: {filename}")
    chapter_start = chapter_positions[-1]
    section_start = text.find(section_heading, chapter_start)
    if section_start < 0:
        raise ValueError(f"missing section {section_heading!r}: {filename}")
    # The first next-section heading after the selected section is the end;
    # this deliberately does not search the whole file before locating it.
    section_end = text.find(next_section_heading, section_start + len(section_heading))
    if section_end < 0:
        raise ValueError(f"missing next section {next_section_heading!r}: {filename}")
    return text[section_start:section_end].strip()


def _chunks() -> dict[str, Chunk]:
    result: dict[str, Chunk] = {}

    def add(value: Chunk) -> None:
        if value.key in result:
            raise ValueError(f"duplicate chunk key: {value.key}")
        result[value.key] = value

    national_decree = "국가를 당사자로 하는 계약에 관한 법률 시행령.txt"
    national_rule = "국가를 당사자로 하는 계약에 관한 법률 시행규칙.txt"
    local_decree = "지방자치단체를 당사자로 하는 계약에 관한 법률 시행령.txt"
    local_rule = "지방자치단체를 당사자로 하는 계약에 관한 법률 시행규칙.txt"
    sme_law = "중소기업제품 구매촉진 및 판로지원에 관한 법률.txt"
    sme_decree = "중소기업제품 구매촉진 및 판로지원에 관한 법률 시행령.txt"

    for number in ("12", "21", "43"):
        add(_chunk_article(f"national_decree_{number}", "국가계약법 시행령", national_decree, number))
    for number in ("17", "24", "25"):
        add(_chunk_article(f"national_rule_{number}", "국가계약법 시행규칙", national_rule, number))
    for number in ("13", "20", "35", "43"):
        add(_chunk_article(f"local_decree_{number}", "지방계약법 시행령", local_decree, number))
    for number in ("17", "24", "25"):
        add(_chunk_article(f"local_rule_{number}", "지방계약법 시행규칙", local_rule, number))
    for number in ("7", "7조의2", "9"):
        add(_chunk_article(f"sme_law_{number}", "중소기업제품 구매촉진 및 판로지원에 관한 법률", sme_law, number))
    for number in ("2", "2조의2", "2조의3", "7", "10"):
        add(_chunk_article(f"sme_decree_{number}", "중소기업제품 구매촉진 및 판로지원에 관한 법률 시행령", sme_decree, number))
    add(_chunk_article("sw_law_48", "소프트웨어 진흥법", "소프트웨어 진흥법.txt", "48"))
    add(
        Chunk(
            "price_notice",
            "국가계약법 등의 재정경제부장관이 정하는 고시금액",
            "국가를 당사자로 하는 계약에 관한 법률 등의 재정경제부장관이 정하는 고시금액.txt",
            "whole_document",
            _read("국가를 당사자로 하는 계약에 관한 법률 등의 재정경제부장관이 정하는 고시금액.txt").strip(),
        )
    )
    add(_chunk_range("government_guide_chapter_2", "정부 입찰·계약 집행기준 제2장", "(계약예규) 정부 입찰·계약 집행기준.txt", "제2장 제한경쟁입찰의 운용", "제3장"))
    add(_chunk_range("national_joint_article_9", "공동계약운용요령 제9조", "(계약예규) 공동계약운용요령.txt", "제9조(공동수급체의 구성)", "제10조("))
    add(_chunk_range("local_guide_c1_item_7", "지방 계약집행기준 제1장 7. 계약담당자 주의사항", "지방자치단체 입찰 및 계약 집행기준.txt", "7. 계약담당자 주의사항", "8. "))
    add(_chunk_range("local_guide_small_contract", "지방 계약집행기준 제5장 수의계약", "지방자치단체 입찰 및 계약 집행기준.txt", "제3절 수의계약 대상과 운영요령\n1. 금액기준에 따른 2인 이상 견적서 제출 수의계약", "2. 금액기준에 따른 1인 견적서 제출 가능 수의계약"))
    add(_chunk_range("local_guide_joint", "지방 계약집행기준 제6장 공동계약", "지방자치단체 입찰 및 계약 집행기준.txt", "나. 구성원 수 등", "다. 공동수급체 구성의 제한"))
    local_award = "지방자치단체 입찰시 낙찰자 결정기준.txt"
    add(
        Chunk(
            "local_award_ch7_s3",
            "지방 낙찰자 결정기준 제7장 제3절",
            local_award,
            "chapter_7/section_3",
            _chapter_section_range(
                local_award,
                "제7장 협상에 의한 계약 낙찰자 결정기준",
                "제3절 입찰과 계약상대자 결정절차",
                "제4절",
            ),
        )
    )
    add(_chunk_range("sw_guideline_articles_2_3", "중소 SW사업자 참여지원 지침 제2조·제3조", "중소 소프트웨어사업자의 사업 참여 지원에 관한 지침.txt", "제2조(사업금액의 하한)", "제4조(사업금액의 하한을 적용하지 않는 공공기관)"))
    add(_chunk_range("sw_guideline_appendix_1", "중소 SW사업자 참여지원 지침 별표 1", "중소 소프트웨어사업자의 사업 참여 지원에 관한 지침.txt", "[별표 1]", "[별표 2]"))
    return result


COMMON = (
    "sme_law_7", "sme_law_7조의2", "sme_law_9", "sme_decree_2",
    "sme_decree_2조의2", "sme_decree_2조의3", "sme_decree_7",
    "sme_decree_10",
    "sw_law_48", "price_notice",
    "sw_guideline_articles_2_3", "sw_guideline_appendix_1",
)
NATIONAL = (
    "national_decree_12", "national_decree_21", "national_decree_43",
    "national_rule_17", "national_rule_24", "national_rule_25",
    "government_guide_chapter_2",
    "national_joint_article_9",
)
LOCAL = (
    "local_decree_13", "local_decree_20", "local_decree_35", "local_decree_43",
    "local_rule_17", "local_rule_24", "local_rule_25", "local_guide_c1_item_7",
    "local_guide_joint",
)
BUNDLE_KEYS = {
    "national_complete": COMMON + NATIONAL,
    "local_general_complete": COMMON + LOCAL,
    "local_small_complete": COMMON + LOCAL + ("local_guide_small_contract",),
    "local_negotiated_complete": COMMON + LOCAL + ("local_award_ch7_s3",),
    "local_small_negotiated_complete": COMMON + LOCAL + (
        "local_guide_small_contract", "local_award_ch7_s3",
    ),
}

# Reference keys needed by each v under each contract-law direction.  This is
# intentionally the same audited mapping rendered in docs/legal_reference_mapping.md.
ITEM_KEYS = {
    "national": {
        "v1": ("national_decree_12", "national_decree_21"), "v2": ("national_decree_21", "national_rule_25", "price_notice"),
        "v3": ("national_decree_21", "national_rule_25", "government_guide_chapter_2"), "v4": ("government_guide_chapter_2",),
        "v5": ("national_decree_21", "national_rule_24", "price_notice"), "v6": ("national_decree_21", "national_rule_24", "national_rule_25", "price_notice"), "v7": ("national_decree_21", "national_rule_24", "national_rule_25", "price_notice"), "v8": ("national_rule_25",),
        "v9": ("government_guide_chapter_2",), "v10": ("sme_law_9", "sme_decree_10"), "v11": ("national_decree_21", "sme_law_7", "sme_decree_7"),
        "v12": ("national_decree_21", "sme_law_9", "sme_decree_10"), "v13": ("national_decree_21", "sme_law_7조의2"),
        "v14": ("national_decree_21", "sme_decree_2조의2", "sme_decree_2조의3", "price_notice"), "v15": ("national_decree_21", "sme_decree_2조의2", "sme_decree_2조의3", "price_notice"),
        "v16": ("national_decree_21", "sme_decree_2조의2", "sme_decree_2조의3", "price_notice"), "v17": ("national_decree_21", "sme_decree_2조의2", "sme_decree_2조의3", "price_notice"),
        "v18": ("national_decree_21", "sme_decree_2조의2", "sme_decree_2조의3", "price_notice"), "v19": ("national_decree_12", "national_rule_17", "government_guide_chapter_2"),
        "v20": ("sw_law_48", "sw_guideline_articles_2_3", "sw_guideline_appendix_1"), "v21": ("national_joint_article_9",), "v22": ("national_decree_43",), "v23": (), "v24": (),
    },
    "local": {
        "v1": ("local_decree_13", "local_decree_20"), "v2": ("local_decree_20", "local_rule_25", "local_guide_c1_item_7", "price_notice"),
        "v3": ("local_decree_20", "local_rule_25"), "v4": ("local_guide_c1_item_7",), "v5": ("local_decree_20", "local_rule_24", "price_notice"),
        "v6": ("local_decree_20", "local_rule_24", "local_rule_25", "local_guide_small_contract", "price_notice"), "v7": ("local_decree_20", "local_rule_24", "local_rule_25", "local_guide_small_contract", "price_notice"), "v8": ("local_rule_25", "local_guide_small_contract"),
        "v9": ("local_guide_c1_item_7",), "v10": ("sme_law_9", "sme_decree_10"), "v11": ("local_decree_20", "sme_law_7", "sme_decree_7"), "v12": ("local_decree_20", "sme_law_9", "sme_decree_10"), "v13": ("local_decree_20", "sme_law_7조의2"),
        "v14": ("local_decree_20", "sme_decree_2조의2", "sme_decree_2조의3", "price_notice"), "v15": ("local_decree_20", "sme_decree_2조의2", "sme_decree_2조의3", "price_notice"),
        "v16": ("local_decree_20", "sme_decree_2조의2", "sme_decree_2조의3", "price_notice"), "v17": ("local_decree_20", "sme_decree_2조의2", "sme_decree_2조의3", "price_notice"),
        "v18": ("local_decree_20", "sme_decree_2조의2", "sme_decree_2조의3", "price_notice"), "v19": ("local_decree_13", "local_rule_17", "local_guide_c1_item_7"),
        "v20": ("sw_law_48", "sw_guideline_articles_2_3", "sw_guideline_appendix_1"), "v21": ("local_guide_joint",), "v22": ("local_decree_43",), "v23": ("local_decree_35", "local_award_ch7_s3"), "v24": (),
    },
}


def _render(chunk: Chunk) -> str:
    return f"[출처: {chunk.title} | {chunk.source} | {chunk.selector}]\n{chunk.text}"


def main() -> int:
    validate_groups()
    chunks = _chunks()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    bundle_manifest: dict[str, object] = {
        "schema_version": 1,
        "purpose": "fixed official-law context selected solely by organizer metadata",
        "competition_product_list": {
            "included": False,
            "reason": "shared pipeline supplies the exact organizer CSV lookup per notice",
        },
        "bundles": {},
    }
    for name, keys in BUNDLE_KEYS.items():
        selected = [chunks[key] for key in keys]
        text = "\n\n".join(_render(chunk) for chunk in selected) + "\n"
        output = OUTPUT_DIR / f"{name}.txt"
        output.write_text(text, encoding="utf-8")
        bundle_manifest["bundles"][name] = {
            "path": str(output.relative_to(ROOT)),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "chunk_count": len(selected),
            "characters": len(text),
            "chunks": [
                {
                    "key": chunk.key,
                    "title": chunk.title,
                    "source": chunk.source,
                    "selector": chunk.selector,
                    "source_sha256": hashlib.sha256(_read(chunk.source).encode("utf-8")).hexdigest(),
                    "chunk_sha256": hashlib.sha256(chunk.text.encode("utf-8")).hexdigest(),
                }
                for chunk in selected
            ],
        }
    group_dir = OUTPUT_DIR / "groups"
    group_dir.mkdir(exist_ok=True)
    group_manifest: dict[str, object] = {}
    for profile, profile_keys in BUNDLE_KEYS.items():
        direction = "national" if profile == "national_complete" else "local"
        for group in LEGAL_ITEM_GROUPS:
            requested = {
                key for item in group.items for key in ITEM_KEYS[direction][item]
            }
            keys = tuple(key for key in profile_keys if key in requested)
            selected = [chunks[key] for key in keys]
            text = "\n\n".join(_render(chunk) for chunk in selected)
            if text:
                text += "\n"
            filename = f"{profile}__{group.group_id}.txt"
            output = group_dir / filename
            output.write_text(text, encoding="utf-8")
            group_manifest[f"{profile}/{group.group_id}"] = {
                "path": str(output.relative_to(ROOT)), "items": list(group.items),
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "chunk_keys": list(keys), "characters": len(text),
            }
    bundle_manifest["group_bundles"] = group_manifest
    MANIFEST_PATH.write_text(
        json.dumps(bundle_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(MANIFEST_PATH)
    for name, entry in bundle_manifest["bundles"].items():
        print(f"{name}: {entry['chunk_count']} chunks, {entry['characters']} chars")
    return 0


if __name__ == "__main__":  # pragma: no cover - command-line entry point
    raise SystemExit(main())
