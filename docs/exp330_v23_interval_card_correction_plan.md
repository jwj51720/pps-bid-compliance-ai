# EXP330 — v23 기간 관계 카드 교정

작성: 2026-09-18, dev / mac

## 발견과 가설

v26 카드와 과거 v23 실험은 지방 협상계약의 서로 다른 기간 관계를 하나로 합쳤다. v26은
`공고일에서 설명회 또는 제안서 마감일까지 40/20/10일`이라고 했지만, 주최 측 제공 source는
다음 세 관계를 별도로 규정한다.

1. 공고→제안서 제출마감: 마감일 전날부터 기산하여 금액별 40/20/10일. 긴급·재공고는 10일.
2. 설명회→제안서 제출마감: 설명회를 실시할 때 같은 금액별 40/20/10일.
3. 공고→설명회: 설명일 전날부터 기산하여 7일.

source는 `legal_condition_ledger_v1.json`의
`local_negotiated/G04_procedure_and_consistency` 아래 `local_decree_35`와
`local_award_ch7_s3` exact chunk/hash다. 따라서 기존 카드는 공고→설명회에 잘못된 금액별 기간을
적용하게 만드는 의미 오류다. EXP330의 가설은 **이 한 카드 오류만 교정하면 다른 입력·출력·merge를
바꾸지 않고 v23 거짓 양성이 감소한다**는 것이다.

## 변경 통제

- base config: `configs/config.exp323-v26-ve-fast-panel-c4.yaml`
- candidate: `configs/config.exp330-v27-v23-interval-card-fast-panel-c4.yaml`
- allowed policy changes: `prompt.decision_cards_path` 하나
- v26→v27 card delta: v23 하나
- 유지: V/E, 24개 all-item, human-readable metadata, condition-aware exact-code 제품 사실,
  모든 tokenizer-admitted 원문, overflow merge, provider/temperature/max tokens
- 금지: Python 날짜 계산/label override, v23 specialist/grouping, V-only, navigation/proof schema,
  다른 카드 변경

## 사전 검증과 실행 gate

유료 실행 전에 다음을 모두 완료한다.

1. `preflight_experiment.py`가 card path 외 effective diff 0임을 확인한다.
2. v26→v27 변경 항목이 v23 하나임을 회귀테스트한다.
3. exact tokenizer dev200에서 제공 문서 omission 0과 call count를 기록한다.
4. short complete, attachment, overflow, 실제 v23 사례의 exact rendered system/user message를 읽는다.
5. 24-item semantic contract와 공고별 실제 metadata value/product/source delivery를 검사한다.
6. exact fast20 mock, 49열/evidence/parse recovery를 확인한다.

이후 fixed fast20에서 EXP323과 비교한다. v23 FP 감소 없이 TP를 잃거나 non-v23 손상이 있으면
중단한다. 통과하면 independent holdout20으로 FP 일반화를 확인한 뒤에만 dev200을 검토한다.
과거 v23 proof/navigation 결과는 잘못된 기간 카드 위에서 수행됐으므로 v27의 결과로 재해석하지
않지만, 그 구조를 다시 실행하지도 않는다.

## 사전 검증 결과

- preflight PASS: base 대비 effective diff는 `prompt.decision_cards_path` 하나다.
- card regression: v26→v27 변경은 v23 하나이며 decision-card test `17 passed`.
- exact tokenizer dev200: 200 records, 제공 문서 374개, omission 0, 170×1-pass +
  21×2-pass + 9×3-pass = 239 calls. v26의 237 calls보다 카드 길이로 2 calls 증가한다.
- 공고별 실제 값 전달 감사: 200 records / 239 final contexts에서 v1–v24 card 원문,
  required human-readable metadata의 해당 공고 실제 렌더값, condition-aware 제품 사실,
  제공 문서 원문 byte coverage가 모두 PASS다.
- upstream 한계: organizer 조립 전 제안요청서가 빠진 10 records/10 documents는 복구되지 않으며,
  `[미수록 문서]` 사실이 final input에 표시된다. 이는 pipeline omission이 아니다.
- metadata의 `미기재` 건수도 숨기지 않는다: 공동도급구성방식 159, 긴급공고여부 138,
  면허업종제한목록 78, 세부품명번호목록 122, 제한지역코드목록 113. 필드는 실제 값 또는
  `미기재`로 전달되지만 organizer가 주지 않은 값을 카드가 만들지는 않는다.
- exact fast20 admission: 20 records / 26 calls, 제공 문서 omission 0.
- exact mock: 20 rows, parse failure 0, 49열/evidence validation PASS.
- 24-item semantic contract: 062(short), 194(attachment), 143(3-pass overflow),
  141(fast v23 positive), 27(holdout v23 positive)에서 24/24 PASS.
- 사람이 읽은 exact rendered messages:
  `outputs/card-input-completeness-v27-20260918/rendered/` 아래 위 다섯 ID. 모든 pass에 v27
  카드와 실제 metadata/product context가 있고, 143의 분할 원문은 모든 byte가 pack 간 보존된다.
  141은 공고일 2026-01-16, 제안요청서 설명 2026-02-06, 제안서 제출 2026-02-26이 보이며,
  27은 공고일 2026-01-14, 실제 사업설명회 2026-02-03과 제안서 제출 일정을 함께 제공한다. 가격입찰·개찰
  및 과업 수행 중 주민 사업설명회가 법정 제안요청서 설명회로 자동 대체되지 않도록 카드에
  역할 구분이 명시돼 있다.

사전 gate는 충족했다. 다음 유료 실행은 EXP330 fixed fast20 한 arm뿐이며, V-only·proof·
navigation·다른 카드 변경을 섞지 않는다.

## Fast20 결과와 결정

EXP330을 실제 실행했다.

- Macro positive-F1: `.1756944444`
- base EXP323: `.1986111111`; delta `-.0229166667`
- runtime: `502.36s`
- usage: prompt `508,347`, completion `17,224`, total `525,571` tokens
- estimated cost: `$0.05761215`
- parse error: 0; 49열 validation PASS
- evidence validity: `.928571`; warning 1건(v8 positive의 유효 evidence 없음)

v23은 EXP323의 `TP/FP/FN=1/0/0`에서 EXP330 `0/0/1`로 악화했다. 유일한 fast positive
PPS-DEV-141은 추정가격 약 32.7억원, 공고일 2026-01-16, 제안요청서 설명 2026-02-06,
제안서 제출 2026-02-26이 모두 입력돼 있다. 40일 구간에서 설명회→제안서 마감 기간도
부족하므로 source-correct v27 카드의 1 조건과 양립하지만 Gemma는 최종 0을 냈다.

카드 외 정책은 동일했지만 non-v23 label도 8 cells 바뀌었다. 이는 all-item 생성 변동/attention
효과이며 v23 카드가 다른 항목의 truth condition을 바꾼 것이 아니다. 한 번의 provider repeat에서
이 변동을 개선으로 선택하지 않는다.

결론은 두 층으로 분리한다.

1. **입력 완결성:** v26의 기간 관계는 source와 불일치하므로 폐기하고, v27의 v23 관계를
   source-correct 카드로 보존한다.
2. **성능 승격:** EXP330은 fast gate를 실패했다. holdout/dev200 유료 실행은 하지 않으며,
   v27을 canonical 성능 정책으로 자동 승격하지 않는다.

즉 올바른 정보를 카드에 넣는 일은 완료했지만, Gemma가 그 세 날짜 관계를 all-item 응답에서
적용하지 못하는 실행 병목은 남았다. 이를 이유로 다시 틀린 v26 관계를 ‘성능 카드’로 유지하지
않는다.
