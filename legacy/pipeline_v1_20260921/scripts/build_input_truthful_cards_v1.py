#!/usr/bin/env python3
"""Build a card-v6 derivative that never claims unavailable prompt inputs.

This is a prompt-truthfulness control, not a product-CSV, law-RAG, threshold,
or rule change.  The generated artifact remains ignored under data/derived;
this builder and its exact replacements are tracked for reproduction.
"""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data/derived/decision_cards_v6.json"
DEFAULT_OUTPUT = ROOT / "data/derived/decision_cards_v6_input_truthful_v1.json"

REPLACEMENTS = {
    "v10": (
        "판정 순서: 1) 공고 자료와 세부품명 메타에서 경쟁제품·직접구매 적용대상을 명시적으로 확인할 수 있는지, 2) 적용대상일 때 직접생산 확인 요구가 있는지 확인한다. "
        "1 조건: 적용대상으로 확인되고 현재 제공된 공고 자료가 전체 문서임을 확인할 수 있으며 필요한 직접생산 조건이 없을 때다. "
        "0 조건: 적용대상·전체 문서 여부가 불명이거나 직접생산 조건이 있으면 0."
    ),
    "v11": (
        "판정 순서: 1) 공고 자료와 세부품명 메타에서 경쟁제품 적용대상을 명시적으로 확인할 수 있는지, 2) 적용대상일 때 중소기업자간 경쟁 제한이 있는지 확인한다. "
        "1 조건: 적용대상으로 확인되고 현재 제공된 공고 자료가 전체 문서임을 확인할 수 있으며 필요한 중소기업자 제한이 없을 때다. "
        "0 조건: 적용대상·전체 문서 여부가 불명이거나 필요한 제한이 있으면 0."
    ),
    "v12": (
        "판정 순서: 1) 공고 자료와 세부품명 메타에서 경쟁제품이 아닌 일반제품임을 명시적으로 확인할 수 있는지, 2) 직접생산확인증명서가 실제 참가자격인지, 3) 별도 허용 사유가 있는지 확인한다. "
        "1 조건: 일반제품으로 확인되고 직접생산 확인을 실제 참가자격으로 요구하며 허용 사유가 없는 경우다. "
        "0 조건: 제품분류·참가제한·예외가 불명이거나 경쟁제품이거나 허용 사유가 있으면 0."
    ),
    "v13": (
        "판정 순서: 1) 공고 자료와 세부품명 메타에서 경쟁제품 적용대상임을 명시적으로 확인할 수 있는지, 2) 소기업·소상공인만으로 실제 참가자격을 한정하는지, 3) 별도 허용 사유가 있는지 확인한다. "
        "1 조건: 경쟁제품 적용대상으로 확인되고 소기업·소상공인 한정을 실제 참가자격으로 두며 허용 사유가 없는 경우다. "
        "0 조건: 제품분류·참가제한·예외가 불명이거나 비경쟁제품이거나 단순 우대·권고 문구이면 0."
    ),
    "v16": (
        "판정 순서: 1) 일반제품이며 1억원 이상·고시금액 미만인지, 2) 현재 제공된 공고 자료가 전체 문서임을 확인할 수 있는지, 3) 필요한 중소기업 제한 또는 판로지원 예외가 있는지 확인한다. "
        "1 조건: 적용대상이고 전체 문서에서 필요한 제한·예외가 없을 때다. "
        "0 조건: 경쟁제품·적용대상·전체 문서 여부가 불명이거나 필요한 제한·예외가 있으면 0."
    ),
    "v18": (
        "판정 순서: 1) 일반제품이며 1억원 미만인지, 2) 현재 제공된 공고 자료가 전체 문서임을 확인할 수 있는지, 3) 필요한 소기업 제한 또는 판로지원 예외가 있는지 확인한다. "
        "1 조건: 적용대상이고 전체 문서에서 필요한 제한·예외가 없을 때다. "
        "0 조건: 경쟁제품·적용대상·전체 문서 여부가 불명이거나 필요한 제한·예외가 있으면 0."
    ),
    "v20": (
        "판정 순서: 1) 실제 SW 사업인지, 2) 사업금액과 대기업 구간(20억·40억·80억)을 확인하고, 3) 현재 제공된 공고 자료가 전체 문서임을 확인할 수 있는지, 4) 적용 구간의 참여제한 또는 명시 예외가 있는지 확인한다. "
        "1 조건: 적용대상이고 전체 문서에서 필요한 제한·예외가 없을 때다. "
        "0 조건: SW 업종·등록 문구만 있거나 금액구간·예외·전체 문서 여부가 불명이거나 필요한 조건이 있으면 0."
    ),
    "v24": (
        "판정 순서: 1) 공고 원문의 명시 값, 2) 나라장터 입력 메타의 대응 값, 3) 같은 의미의 필드인지 차례로 비교한다. "
        "비교 대상은 예산·계약방법·지역제한·업종의 값 자체다. "
        "1 조건: 같은 필드의 두 실제 값이 양립 불가능한 경우다. "
        "0 조건: 문서 값이 없거나 다른 필드를 비교했거나 표현·분류만 다르거나 제한 문구만 있는 경우다."
    ),
}


def build(source: Path = DEFAULT_SOURCE) -> dict:
    payload = deepcopy(json.loads(source.read_text(encoding="utf-8")))
    if set(REPLACEMENTS) - set(payload["cards"]):
        raise ValueError("source card artifact is missing a required item")
    for item, text in REPLACEMENTS.items():
        payload["cards"][item]["prompt_text"] = text
    payload["artifact"] = "decision_cards_v6_input_truthful_v1"
    payload["purpose"] = (
        "EXP123 card-v6 derivative: removes claims that an exact competition-product lookup "
        "or complete notice is available when the selected prompt does not supply it; no new facts"
    )
    payload["input_truthful_replacements"] = sorted(REPLACEMENTS)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(build(Path(args.source)), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
