#!/usr/bin/env python3
"""Build the concise, source-audited official-condition reference for EXP098.

The model-facing text is intentionally a small reading aid, not a raw-law RAG
bundle.  The accompanying manifest retains the organizer-law provenance from
the existing condition ledger so that a rule cannot silently lose its source.
"""

from __future__ import annotations

import hashlib
import json
import sys
import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LEDGER = ROOT / "data/derived/legal_condition_ledger_v1.json"
OUTPUT = ROOT / "data/derived/official_conditions_v2.txt"
MANIFEST = ROOT / "data/derived/official_conditions_v2.manifest.json"


# Each rule is limited to the missing legal comparison condition identified in
# the dev failure analysis.  It must be supported by the organizer-law chunks
# recorded in the ledger; it must not encode dev labels or notice-specific text.
RULES = {
    "v2": "실적 제한은 계약유형·금액·법정 허용 사유를 함께 본다. 제조·용역의 실적금액 또는 규모 제한은 원칙적으로 추정가격이 고시금액 이상인 계약에서만 허용되며, 지방 2인 이상 견적 수의계약 등 법정 예외는 별도로 확인한다.",
    "v5": "지역명이나 납품지는 지역제한이 아니다. 참가자격을 지역으로 제한한 경우에만 적용계약법·계약유형·금액 기준을 대조한다. 국가계약은 고시금액 기준을, 지방계약은 시행규칙의 계약유형별 기준을 적용한다.",
    "v6": "시·군·구 지역제한은 지방 2인 이상 견적 수의계약의 적용 여부와 허용 소재지 범위를 함께 확인한다. 고시금액 미만이라는 사실만으로 모든 지역제한이 허용되지는 않는다.",
    "v7": "지방 2인 이상 견적 수의계약의 지역제한은 법정 허용 범위를 넘겨 인접 지역까지 확대할 수 있는지 확인한다. 여러 지역명이 있더라도 실제 참가자격 제한인지와 소재지·특례를 함께 대조한다.",
    "v10": "직접생산 조건의 부재는 대회 제공 CSV의 정확 코드로 경쟁제품 또는 직접구매 적용대상임이 확인된 경우에만 검사한다. 적용대상에서 직접생산확인 요구 또는 법정 단서가 있으면 0이다.",
    "v11": "중소기업자 제한의 부재는 대회 제공 CSV의 정확 코드로 경쟁제품 또는 직접구매 적용대상임이 확인된 경우에만 검사한다. 적용대상에서 필요한 중소기업자간 경쟁 제한 또는 법정 특별사유가 있으면 0이다.",
    "v12": "직접생산확인을 실제 참가자격으로 요구했는지 확인한다. 대회 제공 CSV의 정확 코드로 경쟁제품이면 이 항목은 0이며, 일반제품 여부는 코드 사실과 공고 원문을 함께 본다.",
    "v13": "경쟁제품은 원칙적으로 중소기업자간 경쟁 대상이다. 정확 코드로 경쟁제품임이 확인된 뒤, 소기업·소상공인만으로 실제 참가자격을 한정했고 별도 법정 근거가 없는 경우를 판단한다.",
    "v14": "일반제품이면서 고시금액 이상인 경우에만 중소기업 제한의 허용 여부를 본다. 경쟁제품 여부, 우선구매·특수 성능·기술·품질의 법정 예외를 함께 확인한다.",
    "v15": "일반제품의 추정가격이 1억원 이상이고 고시금액 미만인 구간인지 먼저 확인한다. 그 뒤 소기업·소상공인 제한과 판로지원법 시행령의 예외를 함께 판단한다.",
    "v16": "일반제품의 추정가격이 1억원 이상이고 고시금액 미만인 적용대상에서만 필요한 중소기업 제한 또는 명시적 판로지원 예외의 부재를 검사한다. 경쟁제품 또는 적용 불명은 0이다.",
    "v17": "일반제품의 추정가격이 1억원 미만인 구간인지 먼저 확인한다. 이 구간의 소기업·소상공인 간 제한경쟁 원칙과 유찰·소수 공급자 등 법정 예외를 함께 판단한다.",
    "v18": "일반제품의 추정가격이 1억원 미만인 적용대상에서만 필요한 소기업·소상공인 제한 또는 명시적 판로지원 예외의 부재를 검사한다. 경쟁제품 또는 적용 불명은 0이다.",
    "v20": "SW 사업은 대기업 매출구간별 참여 하한을 적용한다: 매출 8천억원 이상 대기업은 80억원 이상, 그 밖의 대기업은 40억원 이상, 중소기업에서 중견기업이 된 뒤 5년이 지나지 않은 기업은 20억원 이상이다. 재공고·국가안보·민간투자·분리·분담발주 등 법정 예외를 함께 확인한다.",
    "v21": "공동계약의 최소지분은 계약방식별로 비교한다. 국가 공동이행은 원칙적으로 구성원별 10% 이상이고, 대형공사·주계약자관리 방식은 5% 이상 예외가 있다. 지방은 원칙적으로 5% 이상이며 정해진 조정·분담이행 예외를 함께 확인한다.",
    "v23": "지방 협상계약의 공고기간은 추정가격 10억원 이상 40일, 1억원 이상 10억원 미만 20일, 1억원 미만 10일이다. 긴급·재공고는 10일 기준을 적용한다. 공고일·설명회일·제안서 마감일을 실제 날짜로 비교한다.",
}


# v2a is the controlled follow-up to EXP098.  It retains only conditions whose
# subject matter does not require the separately planned product-CSV expansion,
# whose numeric premise is not still missing from the summary, and which do not
# require the separately planned date/field interpretation card.
VARIANTS = {
    "v2": tuple(RULES),
    "v2a": ("v5", "v6", "v7", "v20", "v21"),
}


def _source_keys_by_item(
    ledger: dict[str, object], rules: dict[str, str]
) -> dict[str, list[str]]:
    result: dict[str, set[str]] = {item: set() for item in rules}
    for entry in ledger["entries"].values():
        for item in entry["items"]:
            name = item["item"]
            if name in result:
                result[name].update(item["source_chunk_keys"])
    missing = sorted(item for item, keys in result.items() if not keys)
    if missing:
        raise ValueError(f"missing source coverage for: {', '.join(missing)}")
    return {item: sorted(keys) for item, keys in result.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=sorted(VARIANTS), default="v2")
    args = parser.parse_args()
    rules = {item: RULES[item] for item in VARIANTS[args.variant]}
    output = ROOT / f"data/derived/official_conditions_{args.variant}.txt"
    manifest_path = ROOT / f"data/derived/official_conditions_{args.variant}.manifest.json"
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    sources = _source_keys_by_item(ledger, rules)
    rendered = (
        "# 공식 판정 조건 요약\n"
        "아래는 대회 제공 법령·고시를 판정에 필요한 조건만 남겨 짧게 정리한 기준이다. "
        "이 기준만으로 1을 정하지 말고, 공고 자료 원문과 나라장터 입력 메타데이터의 사실이 해당 조건을 충족할 때만 1로 판단한다.\n\n"
        + "\n\n".join(f"## {item}\n{text}" for item, text in rules.items())
        + "\n"
    )
    output.write_text(rendered, encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "artifact": f"official_conditions_{args.variant}",
        "purpose": "fixed concise official-condition supplement for the criteria-missing ablation; not a raw-law RAG bundle",
        "source_ledger": str(LEDGER.relative_to(ROOT)),
        "items": [
            {"item": item, "model_text": text, "source_chunk_keys": sources[item]}
            for item, text in rules.items()
        ],
        "characters": len(rendered),
        "sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    print(manifest_path)
    print(f"rules={len(rules)} characters={len(rendered)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
