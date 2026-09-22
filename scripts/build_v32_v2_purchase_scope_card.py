#!/usr/bin/env python3
"""Derive the N007 v2-only card candidate from the frozen v31 card file."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/derived/decision_cards_v31_v4_organizer_definition_resolution.json"
TARGET = ROOT / "data/derived/decision_cards_v32_v2_purchase_scope.json"

V2_PROMPT = (
    "판정 순서: 1) 공고의 과거 완료 실적 금액·규모·수량이 실제 입찰 "
    "참가자격인지 확인한다. 평가점수·특별신인도·적격심사·낙찰자 심사자료·"
    "단순 경력 소개는 참가제한이 아니다. 2) 주최측 입력 메타와 공고의 "
    "적용계약법·실제 적용 기관규칙·업무 내용을 대조하고, 물품 제조·구매/공급·"
    "용역에 적용되는 고시금액과 입찰추정가격을 비교한다. 일반 물품·용역 "
    "고시금액은 2억 3천만원이고, 공기업·준정부기관 계약사무규칙이 실제 "
    "적용될 때만 7억 1천만원이다. 지방계약 물품제조·용역도 지역제한용 "
    "행정안전부 고시금액이나 5억원이 아니라 기획재정부장관의 일반 "
    "물품·용역 고시금액 2억 3천만원을 기준으로 한다. 배정예산금액·"
    "기초금액·투찰금액을 입찰추정가격 대신 쓰지 않는다. 3) 실적 제한의 "
    "명시적 허용 근거를 확인한다. 물품 구매·공급은 제조가 아니라는 이유만으로 "
    "0으로 처리하지 않는다. 국가·지방계약의 제조·용역 실적 허용사항은 "
    "특수 설비·기술 필요 및 고시금액 조건과 함께 검토하고, 지방 소액수의 "
    "등 공고상 실제 적용되는 별도 허용 근거도 확인한다. 계약유형·기관명·"
    "기술 단어의 존재만으로 허용 근거를 추정하지 않는다. "
    "1 조건: 적용 고시금액 미만인 물품 제조·구매/공급 또는 용역에서 "
    "과거 실적이 실제 입찰 참가자격을 제한하고, 그 제한의 명시적 허용 "
    "근거가 확인되지 않은 경우다. "
    "0 조건: 고시금액 이상, 실제 참가제한 아님, 적용 계약법·기관규칙·"
    "입찰추정가격·실적 역할 등 필요한 사실이 불명인 경우, 또는 해당 "
    "제한의 명시적 허용 근거가 확인되는 경우다. 고시금액 이상 지방계약의 "
    "특수 설비·기술 요건 위반을 v2의 고시금액 미만 조건으로 만들지 않는다."
)


def main() -> None:
    cards = json.loads(BASE.read_text(encoding="utf-8"))
    if "v2" not in cards.get("cards", {}) or len(cards["cards"]) != 24:
        raise ValueError("unexpected base card structure")
    if TARGET.exists():
        raise FileExistsError(TARGET)
    cards["artifact"] = "decision_cards_v32_v2_purchase_scope"
    cards["purpose"] = "N007 v2 purchase/supply scope candidate; other cards unchanged"
    cards["cards"]["v2"]["prompt_text"] = V2_PROMPT
    TARGET.write_text(
        json.dumps(cards, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(TARGET)


if __name__ == "__main__":
    main()
