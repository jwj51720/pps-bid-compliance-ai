# EXP-123 이후 전략 재설정

작성일: 2026-09-07 (mac / dev)

## 새 공개 관측

| 제출 | 정책 | dev-200 Macro positive-F1 | Public Macro positive-F1 | runtime |
| --- | --- | ---: | ---: | ---: |
| EXP-120 | 4,000자 ordered context + card v6 + 단일 Gemma V/E | 0.248932 | 0.244317 | 기록 참조 |
| EXP-123 | EXP-120 + v2/v3/v21 source-grounded fixed rules | 0.317797 | 0.260446 | 37분 14초 |
| 외부 관측 | 별도 팀의 상이한 rule-based 전략 | 재현 대상으로 사용하지 않음 | 참고치만 존재 | 미확인 |

EXP-123은 public에서 EXP-120보다 +0.016129 상승했다. 따라서 세 fixed
rule이 전혀 무의미했다고 볼 수는 없다. 그러나 dev에서의 +0.068865와 비교하면
증가분의 대부분은 일반화되지 않았다. v2/v3/v21처럼 dev 오류를 보고 발견한
item별 rule을 더 추가하는 전략은 여기서 종료한다.

Public은 1,853개 전체 평가 자료의 24개 v positive-class F1 평균이다. 따라서 이
차이는 작은 public sample의 단순 분산으로 설명해서는 안 된다. e 열은 leaderboard
점수에는 반영되지 않지만, 제출 원본이 보존되어 2차 정성평가에 쓰인다. 모든
후보는 source-substring evidence 계약을 보존해야 한다.

## 종료한 가설

다음은 반복하지 않는다. 각각 이미 품질 또는 runtime에서 반증됐다.

- 법령 원문ㆍ요약 bundle을 prompt에 추가하는 RAG
- 문서별 full split과 v-grouping의 곱셈 호출, OR/AND를 통한 광범위한 merge
- generic BGE 사례 retrieval, lexical/template case RAG
- dev label 오류를 보고 특정 v의 숫자ㆍ키워드ㆍ후처리 규칙을 누적하는 방식
- raw V-only를 곧바로 제출하는 방식

특히 full split × grouping은 2시간을 초과했고, 카드/법령/문서를 더 넣는 방식은
Gemma의 positive recall을 없애 Macro-F1을 자주 낮췄다. "더 많은 문맥"은 현재
증거에서 기본 해법이 아니다.

## 2026-09-07 추가 gate 결과

전략 재설정 뒤에도 다음 세 가지를 별도로 확인했다. 이들은 이후 재시도의 근거가
아니라, 다음 설계에서 피해야 할 정보 topology를 확정하는 결과다.

| 가설 | 검증 | 결과 | 결정 |
| --- | --- | --- | --- |
| source-grounded dev precedent | source-valid 양성 54개, LOO BGE, 4,668 source fragment | localization 45.45%, positive/negative AUC 0.511 | 사례 RAG/teacher casebook 확장 금지 |
| stochastic Gemma ensemble | exact organizer baseline V/E, fast-20, temperature 0.2 | F1 0.17196→0.20853이지만 26/480 cells만 변화, JSON whitespace stream 1회·8,192 completion tokens | seed 추가·vote·dev200 금지 |
| unlabeled template/product transfer | 기존 20k exact-template 및 product-family audit 재검토 | exact template overlap 0; product fact sheet는 v13 TP를 반복 손실 | template transfer와 CSV prompt reinjection 금지 |

첫 결과의 상세는 [S0D 계획](dev_precedent_s0d_plan.md) 및 ignored
`outputs/dev-precedent-s0d/report.md`, 두 번째는
[D0 결과](decoding_diversity_d0_result.md)에 보존한다. D0의 headline F1은 malformed
attempt와 소수 v2/v4/v24 cell 변화에 의존하므로 promotion evidence가 아니다.

이후 새 후보는 다음 모두를 만족해야 한다: (1) 기존 표의 어느 행과도 다른 정보 또는
semantic operation을 도입하고, (2) 그 정보가 현재 공고의 원문/metadata에서 label-blind하게
관측됨을 먼저 보이며, (3) 20~30 notice gate에서 parse/evidence/runtime을 통과한다.
"더 긴 법령", "다른 card 문구", "더 많은 사례", "다른 temperature"는 후보가 아니다.

## 현 환경의 정확 runtime 한계

2026-09-07 mac 환경에서 `PPS_MODEL_DIR`/`PPS_EMBED_DIR`는 설정되지 않았고,
Hugging Face cache에는 `google/gemma-4-26B-A4B-it`의 실제 tokenizer 파일이 아니라
`.no_exist` marker만 있었다. 따라서 현 OpenRouter token usage나 character 수를
제출 vLLM의 `apply_chat_template` admission으로 해석하면 안 된다.

exact-runtime branch를 재개하려면 대회와 동일한 `PPS_MODEL_DIR`가 연결된 환경에서
shared `submission/script.py`의 staged zip을 대상으로 다음을 함께 측정해야 한다.

1. 각 candidate의 final chat-template token count와 overflow/pass count
2. batch 64/128의 실제 VRAM·throughput 및 1,853건 runtime projection
3. structured JSON malformed recovery와 evidence CSV validation

그 환경이 없는 동안에는 이 branch를 유료 OpenRouter prompt experiment로 대체하지 않는다.

## 아직 분리되지 않은 큰 변수

### A. source-grounded precedent retrieval의 성립 여부

외부 팀의 전략ㆍ제출물은 재현 목표나 다음 실험의 전제가 아니다. 공개 점수 차이는
우리의 국소적인 dev 보정이 충분하지 않다는 신호로만 사용한다.

대신 대회 제공 자료만으로 성립하는 큰 가설을 검증한다. dev의 양성 사례 중 실제
evidence가 원문 substring으로 검증되는 사례만 후보로 삼고, 같은 v의 새 공고
문서 조각이 그 사례를 source-grounded retrieval로 찾아낼 수 있는지를 leave-one-out
방식으로 측정한다. 이 검색의 localization과 판별력이 없으면, 20,000건 self-label,
teacher 호출, case RAG 어느 것도 진행하지 않는다.

### B. 판단(label)과 근거(evidence)의 결합 비용

리더보드는 v만 채점하지만, 현재 baseline V/E 출력은 매 positive에 정확한 원문
substring을 동시에 생성하게 한다. 이 계약이 Gemma의 label recall을 바꾸는지는
우리의 제어된 비교로만 판단한다. 과거 V-only 실험은 output schema 외에도
카드ㆍ문맥ㆍgrouping이 함께 바뀐 경우가 많았다. EXP074/075에는 baseline V-only
arm이 있으나, 이는 현재의 exact organizer metadata rendering 정합성 수정 전
historical contract다.

다음 실험은 **정확 baseline control에서 schema만 바꾸는** V-only probe다. 카드,
문서 4,000자, metadata, item list, model, seed, temperature, context strategy,
parsingㆍmerge는 전부 고정한다. V-only의 local label 성능이 충분히 높아질 때에만,
제출 품질을 위해 별도 source locator/evidence pass를 설계한다. V-only 자체를 evidence
없는 제출 후보로 승격하지 않는다.

### C. organizer-allowed self-labeling은 남아 있지만, 범용 RAG는 아니다

규정상 대회 제공 dev-200ㆍ무라벨 20,000건 및 외부 LLM을 이용한 자가 라벨링은
허용된다. 다만 이미 수행한 사례 RAG는 source fact의 query-문서 alignment가 약했고,
template overlap도 판별력이 없었다. 따라서 20,000건을 무작정 Luna로 label하고
whole-notice BGE top-k를 붙이는 것은 금지한다.

새 사례집 branch가 열리려면 먼저 비용 없는 retrieval feasibility audit을 통과해야
한다. item별로 leave-one-out dev에서 source-grounded demonstration이 같은 위반
유형을 실제로 enrich하는지, evidence source-type과 legal-condition signature가
동시에 맞는지를 검사한다. 기존 generic BGE AUC 약 0.52/낮은 localization을 넘는
명확한 신호가 없으면 teacher labeling 비용을 쓰지 않는다.

## 다음 실험 순서와 승격 gate

### 0. 실행 계약 감사와 retrieval feasibility (비용 없음)

- 현 organizer baseline과 기존 V-only config의 effective prompt/schema diff를
  유지해, 비교가 실제로 schema-only인지 계속 검증한다.
- source-grounded precedent의 leave-one-out localization, source-type 정합성,
  positive-vs-negative 판별력을 측정한다.
- runtime은 call count, prompt token, output token, batch와 별도로 표기한다.

**산출물:** profile manifest, byte/message diff, staged mock, 비용 없는 context report,
retrieval feasibility report.

### 1. label/evidence 분리의 깨끗한 fast probe (Gemma, 20 + 독립 20)

Control은 exact organizer baseline V/E이다. Treatment는 그 control의 모든 message
의미를 유지하되 output schema만 `v1..v24: 0|1`로 바꾼다. 각각 고정 fast-20과
label-blind independent holdout-20에서 실행한다.

**통과 조건:** 두 cohort 모두 control보다 Macro-F1이 +0.02 이상이고, positive recall이
감소하지 않으며 parse error가 없다. 하나라도 실패하면 V-only branch를 다시
문구 수정해 반복하지 않는다.

### 2. dev-200 확인 및 evidence 분리 설계 (Gemma, 조건부)

1단계 통과 후보만 dev-200으로 올린다. 여기서도 baseline보다 +0.015 이상이고
runtime projection이 45분 이하일 때만 evidence recovery를 구현한다. recovery는
label을 바꾸지 않으며, 예측 positive에 대해서만 immutable source span 후보를
선택하게 한다. Python은 후보 위치ㆍ길이ㆍ원문 substring만 검증한다.

### 3. casebook feasibility만 검사 (BGE, 조건부)

1단계와 병렬로 하지 않는다. 0단계/1단계가 끝난 뒤, label-free structural signature
(계약법ㆍ업무구분ㆍ문서유형ㆍ명시 restriction fact)로 candidate를 좁힌 retrieval이
기존 generic retrieval보다 확실히 나은지 offline audit한다. 통과할 때에만 작은
teacher self-label cohort를 만든다. full 20,000 self-label은 이 gate 뒤의 별도
투자 결정이다.

## 현재 결론

현재 최적이라고 주장할 수 있는 제출 정책은 EXP-123 계열이며 public 0.260446이다.
그러나 이 수치는 0.7대 leaderboard와 큰 차이가 있으므로 canonical 우승 전략으로
고정할 근거가 없다. 다음 도약의 우선순위는 **개별 v 보정이나 타 팀 재현이 아니라,
대회 제공 자료에서 실제로 재사용 가능한 source-grounded signal 또는 source-complete
predicate가 존재하는지를 반증 가능하게 확인하는 것**이다. 이 과정에서 local panel만으로
후보를 승격하지 않는다.
