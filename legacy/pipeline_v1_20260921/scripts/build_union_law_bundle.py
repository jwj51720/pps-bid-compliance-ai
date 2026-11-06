#!/usr/bin/env python3
"""Build the first auditable single-bundle law reference from organizer files."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAW_DIR = ROOT / "data/raw/open/data/법령패키지/법령"
OUTPUT = ROOT / "data/derived/legal_reference_union_v1.txt"
MANIFEST = ROOT / "data/derived/legal_reference_union_v1.manifest.json"

SOURCES = {
    "국가계약법 시행령": ("국가를 당사자로 하는 계약에 관한 법률 시행령.txt", ("12", "21", "43")),
    "국가계약법 시행규칙": ("국가를 당사자로 하는 계약에 관한 법률 시행규칙.txt", ("17", "25")),
    "지방계약법 시행령": ("지방자치단체를 당사자로 하는 계약에 관한 법률 시행령.txt", ("13", "20", "35", "43")),
    "지방계약법 시행규칙": ("지방자치단체를 당사자로 하는 계약에 관한 법률 시행규칙.txt", ("17", "24", "25")),
    "중소기업제품 구매촉진 및 판로지원법": ("중소기업제품 구매촉진 및 판로지원에 관한 법률.txt", ("7", "9")),
    "중소기업제품 구매촉진 및 판로지원법 시행령": ("중소기업제품 구매촉진 및 판로지원에 관한 법률 시행령.txt", ("2", "2조의2", "2조의3")),
    "소프트웨어 진흥법": ("소프트웨어 진흥법.txt", ("48",)),
}
WHOLE_FILES = ("국가를 당사자로 하는 계약에 관한 법률 등의 재정경제부장관이 정하는 고시금액.txt",)

RANGES = (
    ("정부 입찰·계약 집행기준 제2장", "(계약예규) 정부 입찰·계약 집행기준.txt", "제2장 제한경쟁입찰의 운용", "제3장"),
    ("지방 계약집행기준 제1장 주의사항", "지방자치단체 입찰 및 계약 집행기준.txt", "7. 계약담당자 주의사항", "8. "),
    ("지방 계약집행기준 제5장 수의계약", "지방자치단체 입찰 및 계약 집행기준.txt", "제3절 수의계약 대상과 운영요령\n1. 금액기준에 따른 2인 이상 견적서 제출 수의계약", "2. 금액기준에 따른 1인 견적서 제출 가능 수의계약"),
    ("지방 계약집행기준 제6장 공동계약", "지방자치단체 입찰 및 계약 집행기준.txt", "나. 구성원 수 등", "다. 공동수급체 구성의 제한"),
    ("지방 낙찰자 결정기준 제7장 제3절", "지방자치단체 입찰시 낙찰자 결정기준.txt", "제3절 입찰과 계약상대자 결정절차", "제4절"),
    ("중소 SW 참여지원 지침 제2~3조", "중소 소프트웨어사업자의 사업 참여 지원에 관한 지침.txt", "제2조(사업금액의 하한)", "제4조(사업금액의 하한을 적용하지 않는 공공기관)"),
    ("중소 SW 참여지원 지침 별표 1", "중소 소프트웨어사업자의 사업 참여 지원에 관한 지침.txt", "[별표 1]", "[별표 2]"),
)


def article(text: str, number: str) -> str:
    heading = f"제{number}" if "조의" in number else f"제{number}조"
    start = re.search(rf"^{re.escape(heading)}\([^\n]+", text, re.M)
    if not start:
        raise ValueError(f"missing article {number}")
    end = re.search(r"^제[0-9]+조(?:의[0-9]+)?\(", text[start.end():], re.M)
    return text[start.start(): start.end() + end.start() if end else len(text)].strip()


def source_range(text: str, start: str, end: str) -> str:
    starts = [match.start() for match in re.finditer(re.escape(start), text)]
    if not starts:
        raise ValueError(f"missing range start: {start}")
    begin = starts[-1]
    finish = text.find(end, begin + len(start))
    if finish < 0:
        raise ValueError(f"missing range end: {end}")
    return text[begin:finish].strip()


def main() -> int:
    chunks: list[str] = []
    manifest: list[dict[str, str]] = []
    for title, (filename, articles) in SOURCES.items():
        path = LAW_DIR / filename
        raw = path.read_text(encoding="utf-8")
        for number in articles:
            text = article(raw, number)
            chunks.append(f"[출처: {title} 제{number}조]\n{text}")
            manifest.append({"source": filename, "selector": f"article_{number}", "sha256": hashlib.sha256(text.encode()).hexdigest()})
    for filename in WHOLE_FILES:
        text = (LAW_DIR / filename).read_text(encoding="utf-8").strip()
        chunks.append(f"[출처: {filename}]\n{text}")
        manifest.append({"source": filename, "selector": "whole_document", "sha256": hashlib.sha256(text.encode()).hexdigest()})
    for title, filename, start, end in RANGES:
        text = source_range((LAW_DIR / filename).read_text(encoding="utf-8"), start, end)
        chunks.append(f"[출처: {title}]\n{text}")
        manifest.append({"source": filename, "selector": f"{start} .. {end}", "sha256": hashlib.sha256(text.encode()).hexdigest()})
    OUTPUT.write_text("\n\n".join(chunks) + "\n", encoding="utf-8")
    MANIFEST.write_text(json.dumps({"version": "v1", "chunks": manifest}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
