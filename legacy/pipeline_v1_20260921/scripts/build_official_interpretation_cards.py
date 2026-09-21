#!/usr/bin/env python3
"""Build the source-provenance-limited official-interpretation card variant."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "incubator/submission_candidates/exp120_card_v6/decision_cards_v6.json"
DEFAULT_OUTPUT = ROOT / "data/derived/decision_cards_v8_official_interpretations.json"
DEFAULT_BASE_OUTPUT = ROOT / "data/derived/decision_cards_v6.json"

UPDATES = {
    "v9": (
        "판정 순서: 1) 규격서·과업지시서 등 공고 자료에 특정 제조사명 또는 모델명이 "
        "실제 납품·제출·사용 요구로 명시됐는지, 2) 단순 기존 장비 설명이나 실제 요구가 "
        "아닌 일반 성능 설명인지 구분한다. 1 조건: 특정 제조사 또는 모델명을 실제 요구사항으로 "
        "명시한 경우다. 규격·가격 동시입찰 여부나 감점형 평가 방식은 0 조건이 아니다. "
        "0 조건: 특정 제조사·모델명이 없거나, 명칭이 실제 요구가 아닌 기존 장비·일반 설명이면 0."
    ),
    "v13": (
        "판정 순서: 1) 제공된 경쟁제품 조회와 공고 명시로 경쟁제품 경쟁입찰 적용대상인지, "
        "2) 소기업·소상공인만으로 실제 참가자격을 한정해 중기업을 배제하는지, 3) 소액수의 "
        "견적입찰의 별도 예외인지 확인한다. 1 조건: 경쟁제품 경쟁입찰에서 소기업·소상공인 "
        "한정을 실제 참가자격으로 두어 중기업을 배제한 경우다. 금액 구간만으로 0이나 1을 "
        "정하지 않는다. 0 조건: 비경쟁제품·적용 불명이거나 단순 우대·권고 문구이거나 "
        "소액수의 견적입찰 예외이면 0."
    ),
}


def build(base_path: Path = BASE) -> dict:
    payload = json.loads(base_path.read_text(encoding="utf-8"))
    result = json.loads(json.dumps(payload, ensure_ascii=False))
    for item, prompt_text in UPDATES.items():
        result["cards"][item]["prompt_text"] = prompt_text
    result["schema_version"] = "v8_official_interpretations"
    result["artifact"] = "official interpretation alignment candidate"
    result["purpose"] = (
        "EXP121 candidate: only v9/v13 card wording aligned to official DACON "
        "public interpretations; see docs/official_interpretations_v1.md"
    )
    result["base_card_sha256"] = hashlib.sha256(base_path.read_bytes()).hexdigest()
    result["changed_items"] = sorted(UPDATES)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--materialize-base",
        action="store_true",
        help="copy the archived EXP120 v6 static asset into data/derived",
    )
    args = parser.parse_args()
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.materialize_base:
        DEFAULT_BASE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_BASE_OUTPUT.write_bytes(BASE.read_bytes())
        print(DEFAULT_BASE_OUTPUT)
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
