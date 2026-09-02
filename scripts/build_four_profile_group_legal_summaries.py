#!/usr/bin/env python3
"""Build concise, auditable legal guardrail bundles for the 4 x 4 routing map.

Unlike the raw-law bundles, these are a *derived reading aid*.  Every statement
has one or more organizer-law chunk keys in the manifest.  The text is concise
Korean intended to expose applicability conditions and exceptions which the
decision cards alone cannot safely carry.  It never replaces the source map:
the manifest retains source file, selector, and chunk hashes for every item.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_four_profile_group_law_bundles import PROFILES, _keys_for
from scripts.build_routed_law_bundles import ITEM_KEYS, _chunks
from src.legal_groups import FOUR_WAY_ITEM_GROUPS, validate_groups


OUTPUT_DIR = ROOT / "data/derived/legal_guardrail_profile_group_v1"
ROUTING_VERSION = "metadata_profile_group_v2"


# These sentences deliberately state only the operational boundary already
# present in the item table and the audited official chunks.  They are not
# label-derived exceptions.  Source keys are separately audited below.
NATIONAL_SUMMARIES = {
    "v1": "법령에 따른 면허 등록 신고 등 일반 자격은 허용되는 참가자격이다. 일반 자격을 넘어 특정 기관군만 참여하게 하는 별도 제한인지 구분한다.",
    "v2": "실적 제한은 제한경쟁의 허용 사유와 제한기준 안에서만 가능하다. 고시금액 미만 여부와 허용 예외를 먼저 확인한다.",
    "v3": "제조 또는 용역의 실적금액 제한은 추정가격이 고시금액 이상인 계약에서만 적용할 수 있고 기준금액의 1배 이내인지 확인한다.",
    "v4": "특수 기술 공법 성능 또는 품질이 실제로 필요한 계약인지 확인한다. 필요성이 없는 특정 기관 또는 특정 실적 한정은 허용 근거가 아니다.",
    "v5": "지역제한은 제한경쟁의 허용 범위와 고시금액을 함께 확인한다. 지역명 자체가 아니라 참가자격 제한인지 판단한다.",
    "v6": "고시금액 미만이라는 이유만으로 모든 지역제한이 허용되는 것은 아니다. 계약 방식과 법령상 허용 범위를 함께 확인한다.",
    "v7": "지역제한의 범위가 허용되는지 확인한다. 여러 지역명이 있어도 인접 지역 확대가 실제 제한인지와 적용 예외를 함께 본다.",
    "v8": "실적 제한과 지역 제한은 같은 참가자격에 함께 적용되는지 확인한다. 둘 중 하나만 있거나 서로 다른 조건이면 중복 제한으로 판단하지 않는다.",
    "v9": "특수 성능 또는 품질이 필요한 경우만 제한 기준을 적용할 수 있다. 특정 모델명은 동등품 허용과 실제 필수 요구 여부를 함께 확인한다.",
    "v10": "경쟁제품 적용대상은 대회 제공 품목 CSV의 정확 코드 조회로 확인한다. 적용대상일 때만 직접생산 조건의 부재를 검사한다.",
    "v11": "경쟁제품은 원칙적으로 중소기업자간 경쟁 방식으로 계약한다. 정확 코드로 경쟁제품 적용대상인지 확인한 뒤 중소기업자 제한의 부재를 검사한다.",
    "v12": "일반제품인지 경쟁제품인지 정확 코드 조회와 공고 자료로 먼저 구분한다. 일반제품에 직접생산확인을 실제 참가자격으로 요구했는지 확인한다.",
    "v13": "경쟁제품 여부를 정확 코드로 확인한 뒤 소기업 소상공인 한정이 실제 참가자격인지 본다. 경쟁제품이라는 이유만으로 소기업 한정이 자동으로 허용되지는 않는다.",
    "v14": "일반제품인지와 고시금액 이상 여부를 먼저 확인한다. 중소기업 제한의 허용 여부는 판로지원법 시행령의 적용 요건과 예외를 함께 확인한다.",
    "v15": "일반제품의 1억원 이상 고시금액 미만 구간인지 먼저 확인한다. 소기업 소상공인 제한과 판로지원 예외를 함께 확인한다.",
    "v16": "일반제품의 1억원 이상 고시금액 미만 구간에서만 필요한 중소기업 제한 또는 판로지원 예외의 부재를 검사한다.",
    "v17": "일반제품의 1억원 미만 구간인지 먼저 확인한다. 중소기업 제한의 허용 여부와 판로지원 예외를 함께 확인한다.",
    "v18": "일반제품의 1억원 미만 구간에서만 필요한 소기업 제한 또는 판로지원 예외의 부재를 검사한다.",
    "v19": "일반 참가자격 외 요건은 특별한 법령 근거가 있을 때만 제한할 수 있다. 확약서가 계약 또는 납품 단계가 아니라 입찰 전 제출 요건인지 확인한다.",
    "v20": "SW 사업이면 대기업 참여 하한을 적용한다. 매출 8천억원 이상 대기업은 80억원 이상, 그 미만 대기업은 40억원 이상, 중소기업에서 중견기업이 된 뒤 5년이 지나지 않은 대기업은 20억원 이상 사업에 참여할 수 있다. 재공고, 국가안보, 민간투자 등 법정 예외와 소프트웨어 외 부분의 분리·분담 발주 예외를 함께 확인한다.",
    "v21": "공동이행은 원칙적으로 5인 이하와 구성원별 10퍼센트 이상이다. 추정가격 1천억원 이상 공사는 10인 이하와 5퍼센트 이상이며, 주계약자관리 방식은 10인 이하와 5퍼센트 이상이다. 계약 특성·규모에 따른 20퍼센트 범위 조정이 가능한지 확인한다.",
    "v22": "협상계약의 설명회 개최 자체는 가능하다. 설명회 참석자만 제안 또는 입찰할 수 있게 실제 참가자격을 제한했는지 별도로 확인한다.",
    "v23": "국가계약 건에서는 이 항목을 적용하지 않는다.",
    "v24": "이 항목은 법령 요약을 적용하지 않는다. 공고 자료 원문과 나라장터 입력 메타데이터의 같은 의미 필드 값을 직접 비교한다.",
}

LOCAL_SUMMARIES = {
    **NATIONAL_SUMMARIES,
    "v1": "법령에 따른 면허 등록 신고 등 일반 자격은 허용되는 참가자격이다. 일반 자격을 넘어 특정 기관군만 참여하게 하는 별도 제한인지 구분한다.",
    "v2": "실적 제한은 제한입찰의 허용 사유와 제한기준 안에서만 가능하다. 지방 소액수의 등 예외 적용 여부를 먼저 확인한다.",
    "v3": "실적금액 제한은 추정가격 기준의 1배 이내인지 확인한다. 계약목적물과 다른 기준금액을 섞어 비교하지 않는다.",
    "v4": "계약 이행에 불필요한 등록 면허 자격 또는 특정 발주실적만의 요구는 부당한 제한 사례다. 일반 자격과 별도 한정을 구분한다.",
    "v5": "지역제한은 지방 시행규칙의 계약 유형별 금액 기준을 함께 확인한다. 지역명 자체가 아니라 실제 참가자격 제한인지 판단한다.",
    "v6": "2인 이상 견적 수의계약에서 시 군 구 제한은 정해진 범위 안에서만 가능하다. 계약 방식과 금액 구간을 먼저 확인한다.",
    "v7": "2인 이상 견적 수의계약의 지역제한은 허용 범위를 넘겨 인접 지역까지 확대할 수 있는지 확인한다.",
    "v8": "2인 이상 견적 수의계약에서는 실적 등 추가 제한과 지역제한의 결합 허용 범위를 함께 확인한다. 같은 참가자격에 두 제한이 모두 적용되는지 확인한다.",
    "v9": "특정 규격 모델 상표를 부당하게 제한하는 것은 금지 사례다. 동등품 허용과 실제 필수 요구 여부를 함께 확인한다.",
    "v19": "일반 입찰참가자격 외 요건은 특별한 법령 근거가 있을 때만 제한할 수 있다. 확약서가 입찰 전 제출 요건인지 계약 또는 납품 단계인지 구분한다.",
    "v21": "구성원별 최소 지분율은 원칙적으로 5퍼센트 이상이다. 공사 특성·규모로 20퍼센트 범위에서 4퍼센트부터 6퍼센트까지 조정할 수 있고, 분담이행 방식과 서로 다른 법령에 따른 업종 간 공동수급체에는 최소지분율을 적용하지 않는다.",
    "v22": "협상계약의 설명회 개최 자체는 가능하다. 설명회 참석자만 제안 또는 입찰할 수 있게 실제 참가자격을 제한했는지 별도로 확인한다.",
    "v23": "지방 협상계약에서만 제안서 마감일 전날부터 공고 기간을 계산한다. 추정가격 10억원 이상은 40일, 1억원 이상 10억원 미만은 20일, 1억원 미만은 10일이다. 긴급 또는 재공고는 10일까지 가능하다. 제안요청서 설명을 하면 설명일 전날부터도 같은 40일·20일·10일 기준을 적용한다.",
}


def _summary_for(direction: str, item: str) -> str:
    return (NATIONAL_SUMMARIES if direction == "national" else LOCAL_SUMMARIES)[item]


def main() -> int:
    validate_groups(FOUR_WAY_ITEM_GROUPS)
    chunks = _chunks()
    groups_dir = OUTPUT_DIR / "groups"
    groups_dir.mkdir(parents=True, exist_ok=True)
    bundles: dict[str, object] = {}
    coverage: dict[str, object] = {}

    for profile, profile_spec in PROFILES.items():
        direction = profile_spec["direction"]
        for group in FOUR_WAY_ITEM_GROUPS:
            per_item, selected_keys = _keys_for(profile, group.items)
            statements = []
            coverage_rows = []
            for item in group.items:
                source_keys = per_item[item]
                text = _summary_for(direction, item)
                if item == "v24":
                    if source_keys:
                        raise ValueError("v24 must not have a legal source chunk")
                elif not source_keys:
                    inactive = profile_spec["inactive_items"].get(item)
                    if not inactive:
                        raise ValueError(f"missing source coverage: {profile}/{item}")
                statements.append(f"## {item}\n{text}")
                coverage_rows.append({
                    "item": item,
                    "summary": text,
                    "source_chunk_keys": source_keys,
                    "inactive_reason": profile_spec["inactive_items"].get(item),
                })
            rendered = (
                "# 판정 보충 규칙\n"
                "대회 제공 법령을 읽기 쉽게 정리한 요약이다. "
                "이 요약과 공고 자료를 대조하되 공고 자료 원문만 근거문구로 사용한다.\n\n"
                + "\n\n".join(statements)
                + "\n"
            )
            relative_path = Path("groups") / f"{profile}__{group.group_id}.txt"
            path = OUTPUT_DIR / relative_path
            path.write_text(rendered, encoding="utf-8")
            chunk_rows = [
                {
                    "key": key,
                    "title": chunks[key].title,
                    "source": chunks[key].source,
                    "selector": chunks[key].selector,
                    "source_sha256": hashlib.sha256(
                        (ROOT / "data/raw/open/data/법령패키지/법령" / chunks[key].source).read_bytes()
                    ).hexdigest(),
                    "chunk_sha256": hashlib.sha256(chunks[key].text.encode("utf-8")).hexdigest(),
                }
                for key in selected_keys
            ]
            key = f"{profile}/{group.group_id}"
            bundles[key] = {
                "path": str(relative_path),
                "items": list(group.items),
                "item_chunk_keys": per_item,
                "chunk_keys": selected_keys,
                "chunks": chunk_rows,
                "sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
                "characters": len(rendered),
            }
            coverage[key] = coverage_rows

    manifest = {
        "schema_version": 1,
        "routing_version": ROUTING_VERSION,
        "purpose": "concise derived legal guardrails; every statement is traceable to organizer source chunks, while model text excludes source paths, selectors, and routing metadata",
        "source_root": "data/raw/open/data/법령패키지/법령",
        "profile_count": 4,
        "group_count": 4,
        "bundle_count": len(bundles),
        "profile_group_bundles": bundles,
        "coverage": coverage,
        "limitations": [
            "This is a reading aid, not verbatim official-law context.",
            "Competition-product applicability remains the exact organizer CSV lookup.",
            "v24 is a document-to-metadata comparison and has no legal source chunk.",
        ],
    }
    (OUTPUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(OUTPUT_DIR / "manifest.json")
    print(f"built {len(bundles)} concise legal guardrail bundles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
