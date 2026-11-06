# S008 — v16 positive-only full-source verifier 계획

상태: 설계 완료, manifest/runner/API 실행 전

## 문제와 가장 작은 가설

S007은 v16의 frozen lexical scope detector가 줄바꿈·가운데점·`중소기업` 표현을 놓치는 실제
population 사례를 확인했다. 그러나 organizer `조항호내용`만으로 실제 제한 존재를 단정할 수
없음도 dev label로 확인했다.

가장 작은 가설은 다음이다.

> S001이 이미 v16=1로 판정한 notice에만, card v6의 v16 계약 + 필요한 human-readable metadata +
> exact-code 제품 사실 + 모든 원문을 Gemma가 다시 읽게 하면, 실제 중소기업 참가제한 또는
> 명시적 판로지원 예외가 있는 false positive를 1→0으로 안전하게 제거할 수 있다.

v16=0은 재검토하지 않으므로 이 verifier는 신규 양성을 만들지 않는다. v13/v18, 카드, 제품
parser, base 23개 item은 바꾸지 않는다.

## 입력 계약

message 순서는 다음으로 고정한다.

1. 입찰 법령 점검 역할과 불확실성 원칙
2. V-only JSON `{"v16": 0|1}` 계약
3. decision card v6의 v16 원문
4. v16에 필요한 human-readable metadata: 업무구분, 계약방법, 입찰추정가격, 조항호내용
5. organizer CSV exact-code 제품 대조 사실과 특이사항
6. 공고문 → 규격서 → 과업지시서 → 제안요청서 → 예외공표서 전체 원문

raw JSON/internal status/code array와 raw 법령은 넣지 않는다. `조항호내용`은 참고 사실일 뿐
그 자체를 제한 존재 증거로 취급하지 말라고 명시한다.

## overflow와 merge

- fixed context를 먼저 tokenizer로 계산한다.
- 모든 문서가 한 context에 들어가면 1 call이다.
- 넘으면 문서 순서를 보존한 notice-level context로 분리한다. 단일 문서가 넘으면 tokenizer
  binary admission으로 원문을 빠짐없이 연속 chunk로 나눈다.
- 각 pass는 해당 원문 조각에서 실제 참가제한/예외의 존재를 검증한다.
- 최종 v16은 pass-level v16의 AND다. 어느 pass든 실제 제한/예외를 확인해 0이면 최종 0이다.
- malformed pass는 최대 2회 같은 task로 재시도하고, 끝까지 invalid면 base v16=1을 유지한다.
  invalid를 임의 0으로 바꾸지 않는다.

## 단계와 gate

### 0-call preflight

- S001 dev200에서 base v16=1인 9건만 route되는지 확인
- 모든 제공 문서 byte coverage 100%, source ledger 100%
- exact tokenizer admission, context×group call 수, rendered short/attachment/overflow 입력 저장
- 24-item semantic contract 중 변경 항목은 v16 하나임을 audit
- staged mock과 isolated output path

### micro 4~8 calls

label을 보지 않고 다음 source 유형을 고정한다.

- 실제 broad qualification이 있는 population 사례 2건
- metadata clause만 있고 source qualification은 확인되지 않는 사례 2건
- 계약 후 확인서 제출 사례 1건
- 명시적 판로지원 예외 사례 1건

role/stage 구분과 malformed/token을 검사한다. 성능 점수로 부르지 않는다.

### fixed panels와 dev200

micro가 통과하면 fixed fast20 → 기존 dev holdout20 → dev200 순으로 실행한다. 두 panel이 이미
adaptive하므로 일반화 증거가 아니라 회귀/파서 gate로만 사용한다. dev200에서는 v16 이외 cell
변화 0, 기존 v16 TP 손실 0을 요구한다.

## 기대 비용

dev200 base v16 positive는 9건이다. population no-BGE 상한 2.415%를 test 1,853건에 단순
대입하면 약 45건이며, 이는 실제 BGE veto 전 상한이다. 모든 문서가 한 context에 들어간다면
추가 logical calls는 약 45회다. 실제 예산은 preflight의 context 수로 다시 계산한다.

현재 제출 95분 27초에 순차 verifier batch 하나 이상이 추가되므로, 품질 gate와 함께 예상
backend batches 및 120분 상한을 반드시 기록한다. S008과 runtime serialization 변경은 섞지 않는다.

## 승격 조건

1. v16 이외 verdict/evidence cell difference 0
2. source-present micro role 정확성 100%, invalid 0
3. dev200 기존 v16 TP 손실 0
4. base v16 FP 감소 또는 최소한 source-grounded counterfactual 개선
5. projected test total이 2시간 한도 안에 있음
6. public 후보로 만들 경우 S005 v3 revert나 지역금액 correction을 함께 넣지 않음

## 2026-09-23 zero-call preflight와 rendered review

manifest `experiments/manifests/clean_exp_s008_v16_full_source_verifier_v1.json`은 S001 대비
undeclared policy difference 0으로 PASS했다.

- micro: 6 notices, 14 documents, 153,004/153,004 source characters, 9 contexts
- dev200 route: base v16=1인 9 notices, 12 documents, 121,058/121,058 characters, 10 contexts
- token range: micro 7,976~14,521; dev 2,691~14,848
- API/BGE calls: 0

사람이 읽은 exact rendered paths:

- short complete:
  `outputs/clean-exp-s008-v16-full-source-verifier-v1/dev200/rendered_inputs/short_complete_PPS-DEV-062__p01.json`
- attachment:
  `outputs/clean-exp-s008-v16-full-source-verifier-v1/dev200/rendered_inputs/attachment_PPS-DEV-20__p01.json`
- overflow/largest:
  `outputs/clean-exp-s008-v16-full-source-verifier-v1/micro/rendered_inputs/largest_or_overflow_PPS-D-021659__p02.json`

검토 결과 카드 v6, 필요한 네 metadata fact, metadata·문서 exact-code 제품 사실, 실제 원문과
doc-id/type/offset가 순서대로 존재했다. raw metadata JSON, raw 법령, internal status는 없었다.
system message는 `조항호내용` 단독 추론 금지와 낙찰·계약 후 서류의 참가자격 오인을 명시했다.
overflow 원문은 source ledger상 gap/overlap 0이다. v1~v15/v17~v24는 S001 owner 불변,
v16만 별도 semantic contract로 trace했다.
