# EXP269–271 — v1 qualification-scope repair, V/E versus V-only

작성: 2026-09-15, dev / mac

## Organizer-source audit

항목표의 v1 이름은 `참가자격 특정기관 제한`이고 국가 시행령 제12조·제21조, 지방 시행령
제13조·제20조를 가리킨다. 현재 v10 card는 이를 `대학·연구기관·특정 법인 등 기관 종류만`
참여시키는 경우로 좁혀 쓴다. 그러나 organizer 법령의 일반 참가자격과 제한입찰 조문은
법령상 등록·허가·기술·실적·지역 등 허용된 자격/제한사항을 열거한다. 따라서 핵심은 대학이라는
단어가 아니라, 허용 근거 없는 특정 기관군 또는 입찰자 조직·시설·인력 속성을 실제
참가자격으로 추가해 일반 적격자를 배제하는지다.

이 해석은 label을 만들기 전에 organizer source에서 도출했고, 그 뒤 dev와 충돌을 점검했다.
EXP208 v1은 `TP 4 / FP 1 / FN 3`, F1 `.666667`이다.

- 기존 card가 잡은 양성에는 대학·4년제 대학·특정 연구기관군 한정이 있다.
- 놓친 세 양성에는 전국 광역단체 수리센터 보유, 50명 이상 보안인력 보유, 특정 지역의
  교육시설 보유를 참가자격으로 요구하는 문구가 있다. 이들은 카드의 대학/연구기관 예시에
  없지만, 법정 등록·면허 자체가 아닌 입찰자 조직·시설·인력 속성으로 참가를 닫는다.
- 유일한 FP는 대학이나 연구기관뿐 아니라 `컨설팅기관(회사)`도 대안으로 허용하고, 실제
  업무수행 인력 요건을 별도로 두었다. 단순 기관명 나열과 일반 회사도 참가 가능한 대안을
  “특정 기관군만”으로 올리지 않는 0 조건이 필요하다.

이 감사는 위 dev 문구나 ID를 카드에 넣지 않는다. card는 organizer 법령의 허용 자격/제한
경계와 semantic role만 압축한다.

## 가설과 세 arm

가설: v1 card의 누락된 조직·시설·인력 참가제한 범위를 보완하면 item-only Gemma가 기존
대학/연구기관 TP를 유지하면서 세 FN을 회복하고, 일반 회사까지 실질적으로 열어 둔 문구는
0으로 구분할 수 있다.

### EXP269 — existing-card V/E control

- base: `configs/config.exp205-relation-checklist-after-source-fast-panel-c4.yaml`.
- allowed changes: `prompt.active_items`, `prompt.profile`, `prompt.mode`.
- v1/e1 only, current v10 card, complete-fact subset, plain baseline.

### EXP270 — corrected-card V/E

- base: EXP269.
- sole allowed change: `prompt.decision_cards_path`.
- 새 artifact는 v10 대비 v1 text만 변경한다.
- Gemma가 v1/e1을 소유하고 Python은 substring/provenance와 merge만 담당한다.

### EXP271 — corrected-card V-only

- base: EXP270.
- sole allowed change: `prompt.output_mode`.
- EXP270과 user input, card, metadata/product facts, original documents, admission, model/seed가
  같다. system/output schema에서 evidence 생성 의무만 제거한다.
- label 성능이 V/E보다 좋아질 때만 별도 source-grounded evidence recovery를 설계한다.

## Card boundary

수정 card는 다음 순서를 요구한다.

1. 원문 문구가 실제 참가 가능 여부를 정하는가.
2. 특정 기관 종류·법인 형태 또는 입찰자 자체의 조직·상시 인력·보유 시설·서비스망 같은
   속성으로 일반 적격자를 배제하는가.
3. 그 속성이 법정 등록·면허·신고, 카드상 별도 실적·지역·제품·기술 기준, 또는 특수 기술·
   안전·이행 필요에 직접 연결된 허용 제한인가.

일반 회사까지 실질적으로 참가 가능한 대안, 평가 배점, 낙찰 후 이행계획, 제품/과업 규격,
법정 등록·면허는 0 조건이다. 특정 기관 또는 임의 조직속성 한정이고 명시 허용 근거가 없는
경우만 1이다.

## Gates and promotion

세 arm 모두 card structural diff, declared preflight, exact dev200 source coverage/provenance와
call topology, short/attachment/overflow 및 fast v1-positive rendered messages, active-v1
semantic contract, exact mock, 49-column/evidence validation, tests를 provider 전에 완료한다.

fast20에는 v1 positive 3건이 있다. corrected arm이 control 대비 TP/F1을 개선하고 precision을
파괴하지 않아야 independent holdout20으로 간다. V/E와 V-only 중 label 성능을 우선하며 동점은
evidence를 보존하는 V/E를 고른다. holdout 방향이 같을 때만 dev200으로 확장한다. fast 실패 시
문구를 panel에 맞춰 재조정하지 않는다.

## Pre-provider gate (2026-09-15)

- v18 artifact는 v10 대비 v1 card text만 다르다. 특정 기관군뿐 아니라 bidder 자체의
  조직·상시인력·보유시설·서비스망 참가제한과 일반 회사 대안/법정자격/평가·이행 역할의
  0 조건을 포함한다.
- preflight controlled differences:
  - EXP269: active items, subset profile, relation mode 제거만.
  - EXP270: card path만.
  - EXP271: output mode만.
- exact-token dev200 admission은 세 arm 모두 200×single-pass, 374/374 source documents,
  source/metadata/card/organizer-semantics omission 0, over-budget 0이다. fast20은 각 20 calls다.
- short `PPS-DEV-062`, attachment `PPS-DEV-194`, overflow `PPS-DEV-169`, fast v1-positive
  `PPS-DEV-049/058/072`의 actual rendered messages를 세 arm에서 읽었다. corrected card,
  human-readable metadata, organizer semantics와 공고문 및 존재하는 규격서·제안요청서가
  보존되고 raw metadata/law text는 없다.
- active-v1 semantic-input contract는 세 arm×여섯 fixture에서 모두 1/1 통과했다.
- 세 arm user messages의 전체 fast20 hash가 동일했다. EXP270/271 system diff는 evidence
  지시와 output JSON shape뿐이고 card text는 같다.
- exact mock은 각 20/20, parse error 0, 49-column/evidence validation PASS다.
- full tests: `235 passed`.

따라서 세 fast20 provider arm만 승인한다.

## Fast20 result (2026-09-15)

| arm | v1 TP/FP/FN | v1 positive-F1 | prompt / completion tokens | wall time | evidence warnings |
|---|---:|---:|---:|---:|---:|
| EXP269 existing-card V/E | 3 / 3 / 0 | 0.666667 | 248,355 / 1,762 | 21.565s | 0 |
| EXP270 corrected-card V/E | 3 / 3 / 0 | 0.666667 | 251,535 / 2,255 | 21.513s | 0 |
| EXP271 corrected-card V-only | 3 / 3 / 0 | 0.666667 | 250,055 / 160 | 20.248s | 6 |

세 arm의 20개 v1 label vector와 여섯 positive ID는 완전히 동일했다. 수정 카드가 기존
card의 세 FP를 제거하거나 새 TP를 만들지 못했고, 같은 수정 카드를 사용한 V-only도 V/E와
판정을 하나도 바꾸지 않았다. V-only completion은 EXP270 대비 92.9% 감소했지만 OpenRouter
wall time은 5.9%만 감소했다. positive 여섯 건의 e1이 모두 비어 validation warning 여섯
건이 발생한 것은 의도한 labels-only contract이며, 별도 evidence recovery가 없으면 제출
가능한 결과가 아니다.

따라서 EXP270/271은 fast promotion gate를 통과하지 못했다. independent holdout과 dev200은
실행하지 않는다. 이 결과는 V-only가 serialization 비용을 크게 줄일 수 있다는 증거이지만,
현재까지처럼 label vector가 V/E보다 좋아지지 않는 한 별도 evidence-recovery 호출을 추가할
성능상 근거는 아니다. v1의 남은 FP는 단순 card 범위 누락보다는 서로 다른 제한 유형을 v1로
겹쳐 읽는 item-boundary 문제이므로, fast 사례에 맞춘 문구 재조정 없이 source/gold 정의를
다시 감사해야 한다.
