# EXP285–289 — v19 확약서 역할·시점 proof, V/E 대 V-only

작성: 2026-09-15, dev / mac

## Source audit와 기존 실패

현재 local-quality composition의 v19는 `TP 6 / FP 9 / FN 0`, F1 `.571429`다. organizer
항목표는 `물품공급 확약서 입찰 시 제출`이며 비고는 입찰 전 발급·보유와 계약 시 제출 표현을
구분하라고 명시한다. 제공된 정부 집행기준 제5조의3은 발주기관이 규격서 작성 단계에서
제조사·기술지원사와 먼저 협약하고, 낙찰 후 낙찰자에게 협약 사본을 제공하여 낙찰자가
물품공급·기술지원 확약서를 발급받게 하는 정상 절차를 규정한다. 지방 집행기준도 발주 전
협약 없이 낙찰자에게 직접 협약서를 받게 하거나 계약체결 이전 제출을 요구하는 사례를
금지한다.

따라서 v19=1은 다음 관계가 함께 확인돼야 한다.

1. 대상 서류가 제조사·공급사·기술지원사의 물품공급 또는 기술지원 확약/협약 문서다.
2. 입찰자에게 입찰·제안 마감 전 발급·보유·제출을 요구하거나 그 불이행을 참가 배제와
   연결한다. DEV23/036처럼 입찰 전 보유 후 계약 시 제출하는 요구도 입찰 전 발급 의무 때문에
   1이다.
3. 일반 확약서 서식 목록, 청렴·안전 서약, `제출 가능 업체`처럼 실제 제출 시점·효과가
   불명확한 문구, 낙찰·계약·납품 단계만의 제출은 0이다.

기존 v19-only EXP246은 동일 card와 모든 원문을 줬지만 fast positive DEV036을 놓치고 일반
서식/목록 세 건을 FP로 냈다. 따라서 item attention이나 카드 문장만으로는 부족하며, 기존
7-category `제출서류_확약서`가 한 문자열 안의 문서종류·행위·시점·입찰효과 관계를 명시적으로
표현하지 못한다는 최소 item-level 근거가 있다.

## 가설

한 호출 안에서 최종 판정 전에 다음 source-grounded 관찰을 구조화하면 v19의 관계 혼동을 줄일
수 있다.

- `후보원문`: 가장 관련 있는 변경 없는 500자 이하 source substring 또는 null.
- `서류종류`: 물품공급·기술지원확약서 / 일반확약서 / 기타서류 / 없음 / 불명.
- `요구행위`: 발급·보유 / 제출 / 제출가능자격 / 언급만 / 없음 / 불명.
- `기준시점`: 입찰·제안전 / 입찰마감후·낙찰전 / 계약체결·납품 / 복수시점 / 없음 / 불명.
- `입찰효과`: 미제출·미보유시참가배제 / 필수제출 / 계약이행 / 목록·서식 / 없음 / 불명.
- `카드대조`: 1조건충족 / 0조건충족 / 판단불가.

이 review는 Python label rule이 아니다. Gemma가 review를 작성한 뒤 card, metadata와 모든 원문을
다시 대조해 최종 v19를 직접 출력한다. Python은 후보원문의 exact substring을 검증한다.

## Controlled arms

- EXP285 V/E: base EXP246; sole change `prompt.mode: baseline -> v19_role_proof_v1`.
- EXP286 V-only: base EXP285; sole change `prompt.output_mode`.
- 두 arm의 card, metadata, 모든 admitted source, model parameters와 user message는 동일하다.
- V-only에서 v19=1이고 `후보원문`이 exact substring 검증을 통과하면 Python은 그 substring을
  e19에 연결한다. 이는 evidence resolution일 뿐 label을 생성·변경하지 않는다. 검증 실패 시
  e19는 blank이며 v19는 모델 출력을 유지한다.

fast20에서 EXP246 `0/3/1`보다 TP/F1을 개선하고 malformed/source failure가 없어야 frozen
negative-only holdout20으로 간다. holdout에서는 FP 억제만 검증할 수 있으므로, fast sensitivity와
holdout specificity가 모두 확인된 winner만 dev200으로 확장한다. V/E와 V-only가 label 동률이면
유효 evidence와 completion을 비교한다. 동일 prompt 반복 majority나 item별 Python 판정은 하지
않는다.

각 paid 단계 전에 base/allowed changes preflight, exact tokenizer admission, short/attachment/
longest 및 positive rendered review, active-v19 semantic contract, exact mock, 49-column/evidence
validation을 완료한다.

## Fast20 실행 전 검증

2026-09-15에 EXP285/286의 유료 호출 전 검증을 완료했다.

- `scripts/preflight_experiment.py`는 EXP285에서 `prompt.mode`, EXP286에서
  `prompt.output_mode`만 effective policy change로 확인했다.
- dev200 exact-token admission은 두 arm 모두 notice 200건, 최종 context/call 200개,
  원문 문서 374/374, 문서 누락 0, overflow 0이다. 가장 큰 입력은 DEV11이며 EXP285는
  30,216/30,268 token, EXP286은 30,156/30,268 token으로 admission budget 안에 있다.
  프로파일은 각각 `outputs/exp285-preflight/admission.json`,
  `outputs/exp286-preflight/admission.json`에 있다.
- exact fast20 mock은 `outputs/exp-285-v19-role-proof-ve-fast-panel-c4-mock`와
  `outputs/exp-286-v19-role-proof-vonly-fast-panel-c4-mock`에 보존했다. 두 결과 모두 20개
  unique ID, 49개 ordered columns, validation warning 0이다.
- active-v19 semantic-input contract는 positive DEV036에서 두 arm 모두 PASS했다. 결과는
  `outputs/exp285-semantic-audit`, `outputs/exp286-semantic-audit`에 있다.
- rendered input은 short DEV062, positive DEV036, long DEV169, attachment DEV194를 직접
  확인했다. system에는 card와 서류종류×행위×시점×입찰효과 review contract가 있고,
  user에는 human-readable metadata, 실제 공고문과 첨부문서 경계, 원문 전체, final 재대조
  지시가 존재한다. item-only 입력이라 이 cohort와 dev200에는 overflow 사례가 없음을 별도로
  확인했다.
- 위 4건의 EXP285/286 user message SHA-256은 arm 사이에 각각 일치했다. 즉 final 입력은 같고
  출력 계약만 V/E 대 V-only로 다르다. V-only positive evidence recovery는 exact substring을
  요구하며 unit test로 검증했다.

따라서 fast20 provider 실행 요건은 충족됐다. EXP285와 EXP286을 순차 실행하고, DEV036 회복과
기존 EXP246의 `TP/FP/FN = 0/3/1` 대비 개선 여부를 먼저 판정한다.

## Fast20 결과와 holdout 승격

| 실험 | 출력 | TP/FP/FN | v19 F1 | 전체 macro | 결론 |
| --- | --- | ---: | ---: | ---: | --- |
| EXP246 | V/E, plain specialist | `0/3/1` | `0` | - | 기존 실패 |
| EXP285 | V/E, role proof | `0/1/1` | `0` | `.125000` | FP는 줄였지만 양성 실패 |
| EXP286 | V-only, role proof | `1/1/0` | `.666667` | `.152778` | 양성 회복, holdout 승격 |

EXP286은 DEV036의 `A/S확약서를 전자입찰서 제출 마감일 전일까지 보유하고, 계약체결 후 ...
제출` 원문을 exact substring으로 회수하고 v19=1을 냈다. 유일한 FP DEV051은 입찰 제출서류
목록의 `물품 공급 및 기술지원 확약서 ... 1부`를 실제 입찰 전 요구로 읽은 경우다. 즉 role
proof는 양성의 복수시점을 보존했지만 `단순 목록은 0` 경계는 완전히 해결하지 못했다.
EXP285는 같은 source/review에서도 DEV036을 0으로 유지했으므로 이 fast20에서는 V-only 출력
계약이 실질 label 차이를 만들었다.

두 arm 모두 parse error 0이고 20 calls다. EXP285는 prompt/completion `274,600/4,183`,
23.3초였고 EXP286은 `273,400/4,213`, 22.8초였다. EXP286 evidence validity가 `.9`인 이유는
positive DEV051의 후보원문이 생략부호를 포함해 exact substring 검증에 실패하여 e19가 blank인
것이며, Python은 label을 바꾸지 않았다. DEV036의 evidence는 유효하다.

EXP287/288 holdout 전 검증도 완료했다. 각 arm은 20 notices, 20 calls, source documents 41/41,
omission/overflow 0이며 최대 DEV27이 각각 28,896/30,268, 28,836/30,268 token이다. base 대비
policy difference는 없고, exact mock은 20개 ID·49열·validation warning 0이다. attachment/longest
DEV27의 active-v19 semantic-input contract도 두 arm 모두 PASS했다. 따라서 frozen negative-only
holdout provider 실행 요건을 충족했다.

## Independent holdout20 결과와 최종 판정

| 실험 | 출력 | holdout TP/FP/FN | v19 결론 | 호출/시간 |
| --- | --- | ---: | --- | ---: |
| EXP287 | V/E | `0/1/0` | DEV086 FP | `20 / 89.4초` |
| EXP288 | V-only | `0/3/0` | DEV050·090·086 FP | `20 / 23.9초` |

holdout20에는 v19 양성이 없으므로 specificity만 평가했다. V/E와 V-only 모두 DEV086의
`제조사 정품공급 확약서 제출 여부`를 양성으로 읽었다. V-only는 추가로 다음 두 절차를
오판했다.

- DEV050: 제조업체가 아닐 때의 납품·A/S확약서를 `적격심사 시` 제출하는 요구. 입찰 전 제출이
  아닌데도 v19=1로 냈고 후보원문 exact 검증에도 실패했다.
- DEV090: 하도급대금 직불조건부 입찰참가 확약서. 서류종류를 `기타서류`로 정확히 기록하고도
  v19=1로 냈으며 후보원문 exact 검증에도 실패했다.

EXP287의 긴 completion은 DEV044 한 건이 8,192 token까지 생성된 탓이며 label 결과에는 양성으로
복구되지 않았다. parse/validation warning은 0이지만 출력 효율이 불안정하다. EXP288의 validation
warning 2건은 positive label은 유지한 채 invalid candidate evidence를 blank 처리한 DEV050/090이다.

**최종 판정: EXP285–288 family를 기각하고 EXP289 dev200은 실행하지 않는다.** EXP286은 fast의
복수시점 양성을 회복했지만 independent holdout에서 V-only FP가 V/E보다 늘었다. 같은 prompt의
V-only 반복검증이나 `카드대조`를 Python label gate로 바꾸지 않는다. 이 결과는 카드 문구만의
결함이 아니라, 모델이 자신이 작성한 `기타서류`·`입찰마감후` 관찰을 최종 법률 판단에 일관되게
결합하지 못하는 실행 병목을 보여 준다.
