# EXP272–274 — v23 quantitative proof and V/E versus V-only

작성: 2026-09-15, dev / mac

## 실패 원인과 새 가설

현재 local-quality 최고인 EXP208 + EXP221(v4) + EXP231(v5) + EXP262(v14) composition에서
v23은 `TP 3 / FP 32 / FN 2`, F1 `.15`다. 입력 감사는 card, human-readable metadata와 모든
374 source documents가 final prompt에 있음을 확인했다. 병목은 날짜 문자열 누락보다 날짜의
역할·금액구간·최소기간·실제 기간을 한 truth condition으로 결합하지 못하는 데 있다.

기존 실험과의 경계는 명확하다.

- EXP180은 source-only 날짜 역할 발췌를 final에 추가했지만 fast v23 TP를 잃었다.
- EXP190은 prose checklist의 v23 specialist가 eligible 여섯 건을 모두 1로 과호출했다.
- EXP191은 공고일/종료일 역할 proof를 출력했지만 금액구간, 적용 최소일수와 계산 일수가
  관찰 불가능했고 v23 `1/3/0`으로 base와 같았다.

따라서 새 가설은 v23 하나의 같은 응답에서 다음 operand를 모두 observable하게 만들면 Gemma가
단순 `지방계약+협상` anchor를 최종 1로 바로 연결하지 않고 기간 비교를 실제로 수행한다는 것이다.

1. 적용 계약법과 계약방식
2. organizer metadata의 입찰추정가격
3. 카드상 금액구간과 적용 최소일수(40/20/10일)
4. 공고일 및 적격 종료일의 source substring과 종료일 역할
5. 모델이 계산한 두 날짜 사이의 달력일수
6. 긴급·재공고 예외와 최종 카드 대조

Python은 필드 type, enum, source substring/provenance와 결과 병합만 검증한다. 금액구간·일수·
예외로 v23을 계산하거나 override하지 않으며 final v23은 Gemma가 소유한다.

## Controlled arms

### EXP272 — ordinary v23-only V/E control

- base: `configs/config.exp205-relation-checklist-after-source-fast-panel-c4.yaml`.
- allowed changes: `prompt.active_items`, `prompt.profile`, `prompt.mode`.
- v23/e23만 판단하는 `complete_fact_subset_v1`, plain `baseline` one-stage control이다.
- current v10 card, metadata/product facts, organizer semantics, 모든 admitted original source,
  exact tokenizer admission, merge, postprocess와 provider parameters를 유지한다.

### EXP273 — quantitative-proof V/E

- base: EXP272.
- sole allowed change: `prompt.mode: baseline -> v23_quantitative_proof_v1`.
- proof object 뒤 `판정={위반여부, 근거문구}`를 출력한다.
- source proof 문자열과 e23은 기존 unchanged-substring validator를 통과해야 한다.

### EXP274 — quantitative-proof V-only

- base: EXP273.
- sole allowed change: `prompt.output_mode: labels_and_evidence -> labels_only`.
- EXP273과 user input, card, metadata/product facts, original documents, admission과 model parameters는
  동일하다. proof object는 같고 최종 `판정`에서 evidence 생성 의무만 제거한다.
- V-only label이 V/E보다 실제로 좋을 때만 검증된 proof source span에서 e23을 복구하는 별도
  evidence policy를 설계한다. 이 실험에서 Python evidence 선택이나 label rule을 섞지 않는다.

## Paid-run gates

1. 세 config의 base와 `allowed_policy_changes`를 preflight로 검증한다.
2. exact Gemma tokenizer로 dev200 source coverage/provenance, metadata/card/organizer semantics,
   over-budget와 call topology를 세 arm 모두 기록한다.
3. short complete, attachment, overflow notice와 fast v23-positive의 실제 rendered system/user
   message를 export하고 사람이 읽는다.
4. active-v23 적용사실, 1 조건, 중요 0 조건, metadata와 모든 source type의 semantic-input
   contract를 exact rendered prompt에서 추적한다.
5. complete/malformed proof, V/E와 V-only schema, source substring 검증, mock 49-column output과
   full tests를 통과한다.

Frozen fast20에는 v23 positive 한 건이 있다. EXP273/274 중 하나가 EXP272 대비 이 TP를
유지하면서 FP를 줄여 F1을 개선해야 independent holdout20으로 간다. V/E와 V-only 중 label
성능을 우선하고 동점이면 evidence를 보존하는 V/E를 선택한다. holdout에서도 같은 방향일 때만
dev200으로 확장한다. 실패하면 proof enum·날짜 계산 문구·예시를 fast 사례에 맞춰 재조정하지
않는다.

## Pre-provider gate (2026-09-15)

- preflight controlled differences는 EXP272의 active-items/subset-profile/baseline-mode,
  EXP273의 quantitative-proof mode, EXP274의 output mode만 각각 보고했다.
- exact Gemma tokenizer dev200 admission:
  - EXP272: 200 records × one pass = 200 calls.
  - EXP273/274: 199×1 + 1×2 = 201 calls. proof 고정 context 때문에 `PPS-DEV-11`만 두 pack이다.
  - 세 arm 모두 374/374 source documents, source omission 0이며 각 prompt는 30,268-token
    admission budget 이하다.
- short complete `PPS-DEV-062`, attachment `PPS-DEV-194`, long `PPS-DEV-169`, fast v23-positive
  `PPS-DEV-141`의 actual rendered messages를 세 arm에서 export해 읽었다. v23 card, 적용계약법,
  낙찰방법, 입찰추정가격, 공고게시일자, 긴급공고여부, organizer semantics와 존재하는 공고문·
  규격서·제안요청서가 모두 보존된다. raw metadata JSON/internal status/code와 raw law text는 없다.
- EXP273/274의 fast20 user messages는 전부 byte-identical하다. system/output schema에서 final
  evidence contract만 다르다.
- active-v23 semantic-input contract는 네 fixture에서 두 treatment와 control 모두 PASS했다.
- exact mock은 각 arm 20 rows, 49 ordered columns, unique IDs, parse error 0, validation PASS다.
  quantitative proof의 V/E와 V-only schema, malformed/type/enum parser와 두 source proof의
  substring validation을 regression test로 고정했다.
- full tests: `241 passed`.

따라서 frozen fast20의 세 provider arm만 승인한다.

## Fast20 result — rejected

| arm | v23 TP/FP/FN | precision / recall / F1 | completion | runtime | evidence validity |
|---|---:|---:|---:|---:|---:|
| EXP272 ordinary v23-only V/E | `1/12/0` | `.0769 / 1.0 / .142857` | 1,056 | 20.885s | `.384615` |
| EXP273 quantitative-proof V/E | `1/14/0` | `.0667 / 1.0 / .125000` | 5,279 | 24.168s | `.266667` |
| EXP274 quantitative-proof V-only | `1/17/0` | `.0556 / 1.0 / .105263` | 4,435 | 23.512s | `0` |

세 arm 모두 parse error 0이며 exact output validation을 통과했다. 그러나 quantitative proof는
control보다 FP를 V/E에서 2건, V-only에서 5건 더 만들었다. V-only는 proof object가 completion의
대부분을 차지해 EXP273 대비 completion을 16.0%만 줄였고 label 성능도 더 낮았다.

observable review는 실패 원인을 직접 드러냈다.

- EXP273은 `국가계약` 또는 계약방식 `기타`라고 스스로 기록한 사례도 `카드대조=1조건충족`,
  final v23=1로 냈다. 즉 applicability 0 조건을 관찰하고도 최종 논리에 사용하지 않았다.
- 18,181,818원을 `1억이상10억미만`, 60,000,000원을 같은 구간으로 쓰는 등 명백한 금액구간
  오류가 있었다.
- 계산일수가 적용 최소일수 이상인 사례와 국가계약 사례에서도 `카드대조=1조건충족`이 반복됐다.
- EXP273/274의 20개 review는 모두 `카드대조=1조건충족`이었다. 구조화 필드가 논리적 constraint로
  작동하지 않고 양성 anchor를 강화했다.

따라서 EXP273/274는 사전 gate를 실패했고 holdout/dev200을 실행하지 않는다. EXP180/190/191과
이번 결과를 합치면 v23에서 source 역할 발췌, prose checklist, 부분 proof, 완전한 수치 proof,
V/E와 V-only serialization 모두 일반화된 개선을 만들지 못했다. review를 Python의 날짜·금액
label rule로 바꾸거나 fast 사례에 맞춰 enum/문구를 조정하지 않는다. v23 branch는 종료한다.
