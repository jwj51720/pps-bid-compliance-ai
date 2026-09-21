# EXP-C004 — v3 참가자격 실적금액 관계 owner

작성일: 2026-09-21

## 1. 결론과 실험 단위

Clean L41을 기준선으로 고정하고, `v3`만 새 native owner로 교체한다. 이번 실험은 v3 전체를
일반화한 거대 schema가 아니다. 현재 dev200 오류 7건(FP 1, FN 6) 모두에서 확인된 가장 작은
공통 결함인 **실제 참가자격 실적금액과 입찰추정가격의 관계**만 구조화한다.

- base manifest: `experiments/manifests/reference_l41_openrouter_dev200_v1.json`
- base output: `outputs/clean-reference-l41-openrouter-dev200-v1/`
- baseline v3:
  - fast20: TP 1 / FP 0 / FN 2 / F1 `0.500000`
  - holdout20: TP 0 / FP 0 / FN 1 / F1 `0.000000`
  - dev200: TP 2 / FP 1 / FN 6 / F1 `0.363636`
- allowed policy changes:
  - v3 final owner: `hybrid.r10` → `hybrid.native_v3_monetary_v1`
  - v3 전용 source view, prompt, structured observation, reducer
  - candidate-bearing 공고에만 v3 specialist 1회를 추가한다. 전체 logical calls는
    `기존 3N + monetary_candidate_notice_count`다.
- 고정:
  - v1–v2, v4–v24 final cells
  - frozen L41의 세 기존 호출과 response
  - metadata 값, retrieval, provider/generation parameter, evidence resolver
  - r10 schema와 prompt는 이번 실험에서 변경하지 않는다.

Legacy 파일은 import·실행·복사·생성하지 않는다. 구현은 `src/pps_ai`의 새 module과 clean
entrypoint만 사용한다. Hash-pinned L41 artifact는 기존 baseline cell을 읽는 격리 loader로만
사용한다.

## 2. 오류 분해

기존 r10은 v3를 `{q, x, id}` 하나로 압축하고 final reducer가 다음 conjunction을 사용한다.

```text
v3 = (q = Y) AND (x = Y) AND source_id_is_qualification
```

이 계약에는 두 독립 결함이 있다.

1. 자격조항과 금액 판단을 단일 `id`가 동시에 증명해야 한다. `PPS-DEV-051`,
   `PPS-DEV-059`는 모델이 `q=Y, x=Y`를 맞혔지만 `id=null`이라 FN이 됐다.
2. 모델이 숫자 비교까지 수행한다. `PPS-DEV-054`는 참가자격 실적 `1억원`이
   입찰추정가격 `327,272,727원`보다 작은데 `x=Y`로 출력해 유일한 FP가 됐다.

dev200의 v3 양성 8건과 유일한 FP를 원문 대조한 결과는 다음과 같다.

| 구분 | notice | 참가자격 실적금액 | 입찰추정가격 | 관계 |
| --- | --- | ---: | ---: | --- |
| TP | PPS-DEV-04 | 455,000,000 | 318,181,818 | `>` |
| TP | PPS-DEV-042 | 100,000,000 | 61,264,545 | `>` |
| FN | PPS-DEV-05 | 500,000,000 | 327,636,364 | `>` |
| FN | PPS-DEV-051 | 300,000,000 | 245,454,545 | `>` |
| FN | PPS-DEV-053 | 100,000,000 | 22,690,000 | `>` |
| FN | PPS-DEV-059 | 200,000,000 | 83,454,545 | `>` |
| FN | PPS-DEV-062 | 300,000,000 | 227,272,727 | `>` |
| FN | PPS-DEV-071 | 500,000,000 | 427,272,727 | `>` |
| FP | PPS-DEV-054 | 100,000,000 | 327,272,727 | `<` |

이는 label 문자열을 규칙으로 넣는 근거가 아니다. 오류 panel은 기존 계약이 잃은 변수를
식별하는 데만 사용한다. selector와 parser는 notice ID, 업종명, 지역명, 특정 금액 목록을
포함하지 않는 일반 규칙이어야 한다.

## 3. organizer truth condition과 수학식

Organizer 항목표는 v3를 `실적제한 1배수 이상`, 비교 기준을 `사업예산 기준`이라고 표기한다.
Organizer 법령 source와 source-concordant v30 card는 실제 비교값을 다음처럼 구체화한다.

- 금액 제한: 국가·지방 모두 `입찰추정가격`과 같은 범위로 비교한다.
- 정확히 1배: 항목명의 `이상`과 시행규칙의 `1배 이내`가 충돌하므로 임의 양성화하지 않는다.
- 지방 규모·양: 원칙 1/3과 필요시 1배까지의 별도 조건이며, 금액 관계와 섞지 않는다.

이번 monetary owner가 확정하는 식은 다음뿐이다.

```text
Q_j = observation j가 실제 입찰 참가자격의 단일 과거실적 금액 요구
R_j = exact source surface에서 Python이 원 단위로 정규화한 요구금액
T   = organizer metadata의 입찰추정가격

positive_proof = EXISTS j: Q_j AND R_j > T
negative_proof = candidate coverage가 완전하고
                 EXISTS j: Q_j AND verified(R_j)
                 AND FOR ALL such j: R_j <= T

v3 = 1                  if positive_proof
     0                  if negative_proof
     baseline_v3        otherwise
```

`R_j = T`는 이번 정책에서 0이다. 누적실적, 평가점수, 특별신인도, 제출서식의 과거 실적란,
단순 경력 소개는 `Q_j=false`다. 비교값으로 배정예산이나 기초금액을 대체하지 않는다.

Python은 법률 역할을 keyword로 확정하지 않는다. Gemma가 각 후보의 역할을 분류하고 원문
금액 surface와 source ID를 반환한다. Python은 후보 전수 응답, exact substring, 단위 변환,
metadata 숫자와 위 부등식만 검증한다.

## 4. source view와 observation 계약

### 4.1 label-blind source view

- 제공된 모든 문서를 문서 순서대로 inspect한다.
- `실적`과 금액 표현이 같은 bounded section/window에 있는 후보를 high-recall로 만든다.
- 표의 header/value가 다른 줄이면 하나의 병합 exact-window candidate로 보존한다.
- 각 candidate는 notice/document identity, exact offsets, SHA-256, source ID를 갖는다.
- 모든 문서에 inspected ledger를 남기고 candidate가 없는 문서는 그 사실을 구분한다.
- 후보 수가 prompt budget을 넘으면 문서를 누락하지 않고 notice-level 추가 context로 나눈다.

Selector 미탐지는 v3=0의 근거가 아니다. candidate가 없거나 coverage가 불완전하면 baseline v3로
돌아가며 specialist 호출도 만들지 않는다. 따라서 모든 공고를 일률적으로 네 번 호출하지 않는다.

### 4.2 Gemma observation

모델은 모든 admitted candidate ID를 정확히 한 번씩 분류한다.

```text
candidate_id
role = BID_QUALIFICATION | EVALUATION | FORM | EXPERIENCE_DESCRIPTION | OTHER
requirement_basis = SINGLE_CONTRACT | AGGREGATE | UNKNOWN
mandatory = YES | NO | UNKNOWN
amount_surface = exact source substring | null
source_id
```

모델은 최종 v3 label과 정규화된 정수 금액을 출력하지 않는다. `amount_surface`는 해당
source span의 변경 없는 substring이어야 한다. Python parser는 일반적인 원/천원/만원/억원
표기와 쉼표·공백만 정규화하며, surface에 없는 배수를 추론하지 않는다.

## 5. 사전 검증과 단계별 gate

### 5.1 구현 전/로컬 gate

1. 금액 parser fixture: 원, 천원, 만원, 억원, 소수 억원, 쉼표/공백, 범위·비율 거부.
2. role fixture: 참가자격 / 평가 / 제출서식 / 경력소개를 최소 2건씩 구분.
3. dev200 label-blind coverage:
   - supplied document inspected 100%
   - 위 오류 panel 9건의 실제 참가자격 금액 문장 candidate recall 100%
   - foreign span 0, exact span validation 100%
4. short complete, attachment, largest/overflow, 오류 panel의 exact rendered messages를 저장하고
   사람이 읽어 candidate, 입찰추정가격, 역할 계약을 확인한다.
5. semantic-input contract: v3의 적용 사실, 1 조건, 주요 0 조건, 필요한 문서와 metadata exact
   span을 trace한다.
6. active preflight, mock, 49열/evidence validation, 다른 23개 final cell equality를 통과한다.

### 5.2 paid gate

1. **fast20** (`configs/dev_fast_panel_v1.json`만 사용)
   - positives: PPS-DEV-042, 051, 062
   - baseline TP 1 / FP 0 / FN 2
   - 승격: TP >= 2, FP = 0, malformed/fallback = 0
   - 목표: TP 3 / FP 0 / FN 0, v3 F1 1.0
2. **independent holdout20** (`configs/dev_prompt_holdout_v1.json`)
   - positive: PPS-DEV-053
   - baseline TP 0 / FP 0 / FN 1
   - 승격: TP 1, FP = 0, malformed/fallback = 0
3. **dev200**
   - 최소: TP >= 6, FP <= 1, FN <= 2
   - 목표: TP 8, FP 0, FN 0
   - 다른 23개 final cell exact equality

목표 v3 F1 1.0이면 다른 항목 고정 시 dev200 Macro의 산술 상한은 다음과 같다.

```text
0.7796736645 + (1.0 - 0.3636363636) / 24 = 0.8061888161
```

최소 gate의 보수적 예 `TP=6, FP=1, FN=2`는 v3 F1 `0.800000`이고 예상 Macro는
`0.797855`다.

## 6. 중단 조건과 후속 분리

- fast20에서 FP가 생기면 holdout을 실행하지 않는다.
- candidate 누락을 발견하면 prompt를 고치기 전에 source view만 보수하고 별도 revision으로 남긴다.
- role 오류와 숫자 parser 오류를 같은 revision에서 동시에 고치지 않는다.
- 이번 실험에서 v3를 r10 schema에서 제거하지 않는다. 성공 뒤 별도 C003/C004B에서 dead-output
  removal과 logical-call/runtime 재구성을 검증한다.
- 금액이 아닌 규모·양 관계는 실제 오류 사례와 organizer 적용 사실을 먼저 확보한 후 별도 owner로
  확장한다. 이번 결과를 v3 전체 truth condition의 완결 증명이라고 부르지 않는다.

## 7. 2026-09-21 구현·유료 실행 전 검증

Clean native 구현과 manifest preflight를 완료했다.

- manifest: `experiments/manifests/clean_exp_c004_v3_monetary_v1.json`
- active modules:
  - `src/pps_ai/views/v3_monetary.py`
  - `src/pps_ai/decisions/v3_monetary.py`
  - `src/pps_ai/v3_monetary_experiment.py`
- manifest diff: 선언되지 않은 변경 0, 사용되지 않은 선언 0, PASS
- dev200 source coverage:
  - 200 notices, organizer 제공 374 documents 전부 inspected
  - uninspected 0
  - candidate-bearing notices 61, exact candidates 100
  - specialist tokens: min 1,030 / p95 3,028 / max 3,676 / sum 100,041
  - total logical calls: baseline 600 + specialist 61 = 661
- 오류 panel 9건의 실제 참가자격 금액 문장 recall: 9/9
- dev200 v3 양성 8건 중 monetary candidate가 없는 건: 0
- active tests: 37 passed
- fast20 mock: 20 rows, 49-column export/evidence validation PASS, baseline cell 재현

정확한 rendered message를 다음 경로에서 직접 읽었다.

- short complete:
  `outputs/clean-exp-c004-v3-monetary-v1/dev200/rendered_inputs/short_PPS-DEV-02.json`
- attachment:
  `outputs/clean-exp-c004-v3-monetary-v1/dev200/rendered_inputs/attachment_PPS-DEV-03.json`
- largest candidate prompt:
  `outputs/clean-exp-c004-v3-monetary-v1/dev200/rendered_inputs/largest_PPS-DEV-138.json`
- error panel 9건:
  `outputs/clean-exp-c004-v3-monetary-v1/dev200/rendered_inputs/error_panel_*.json`

사람 검토 결론:

1. 모든 message에 입찰추정가격 실제 값, 실제 참가자격/평가/서식 구분, `요구금액 >
   입찰추정가격`의 엄격 부등식, 같거나 작을 때의 0 조건이 존재한다.
2. short `PPS-DEV-02`는 참가자격 `3천만원`과 추정가격 `83,100,000원`을 함께 보존한다.
3. attachment `PPS-DEV-03`은 공고문의 실제 자격요건 `3천만원`을 보존하고, 제공 과업지시서도
   inspected ledger에 존재한다. 첫 후보의 사업예산/`총액, 실적` 문구와 실제 자격 후보가 분리돼
   있어 role observation의 필요성도 확인된다.
4. largest `PPS-DEV-138`은 제안요청서의 평가·서식 실적 후보 네 개를 모두 포함하며, 공고문과
   제안요청서 모두 inspected다. 이 사례는 qualification observation이 없으면 강제 0이 아니라
   baseline fallback하는 계약을 검증한다.
5. 오류 panel의 actual requirement/estimate 쌍은 모두 message에 존재한다. 특히 기존 FP
   `PPS-DEV-054`는 `1억원`과 `327,272,727원`, fast FN `051/062`는 각각 `3억원`과
   `245,454,545/227,272,727원`을 정확히 전달한다.
6. 다른 23개 item은 L41 cell을 그대로 읽고 final equality를 검사한다. 이 실험이 변경하는
   semantic-input contract는 v3 하나뿐이다.

따라서 fast20 유료 실행에 필요한 source coverage, exact tokenizer admission, rendered-input
review, semantic-input contract, mock, isolated output path가 모두 갖춰졌다. 다음 gate는 fast20
specialist 10호출이며, TP >= 2 / FP = 0 / malformed·fallback = 0을 통과하기 전에는 holdout을
실행하지 않는다.
