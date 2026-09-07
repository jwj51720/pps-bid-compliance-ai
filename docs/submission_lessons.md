# 제출 관측과 운영 교훈

이 문서는 실제 제출에서 확인된 runtime·leaderboard 관측을 실험 결과와 구분해
기록한다. `outputs/`의 재현 가능한 local metric과 달리, 동료가 구두로 전달한
제출 성적은 원본 zip·config가 확보되기 전까지 **외부 관측**으로 표기한다.

## 2026-09-02: EXP044 runtime timeout

EXP044 제출은 `full_split_merge`와 `grouping: four_way`를 함께 사용했고, 2시간
제한에서 timeout 되었다. `batch_size: 128`도 사용했다. timeout의 직접 원인을
batch 크기 하나로 단정할 수는 없지만, 이 구조의 호출량은 이미 제출 후보로 보기
어려울 만큼 크다.

동일 prompt/admission 조건을 Gemma tokenizer로 다시 세면 dev-200은 다음과 같다.

| 대상 문서 유형 | 실제 document-context 조각 수 | 4개 v그룹 적용 후 Gemma 호출 수 |
| --- | ---: | ---: |
| 공고문 | 201 | 804 |
| 규격서 | 63 | 252 |
| 과업지시서 | 53 | 212 |
| 제안요청서 | 60 | 240 |
| 합계 | 377 | 1,508 |

제안요청서 3개만 tokenizer budget 때문에 추가 조각으로 분할되었고, 나머지는
원문 문서 하나당 1 context였다. 따라서 병목의 주원인은 overflow가 아니라
`문서별 pass × v그룹`의 곱셈이다. 실제 평가 입력의 공개 sample은 10건뿐이므로
1900여 실제 평가 공고의 정확한 호출 수는 로컬에서 알 수 없다. 다만 dev 평균은
공고당 1.885 context이므로, 같은 문서 분포라면 1,900건에서 약 14,326회의
grouped call이 발생한다. 실제 분포가 다를 수 있으므로 이는 추정치일 뿐이다.

### 앞으로의 제출 gate

1. 제출 후보마다 tokenizer admission 뒤의 document-context 수, 문서 유형별
   분포, `context 수 × item group 수` 호출 상한을 반드시 기록한다.
2. full split과 v-grouping을 함께 쓰는 후보는 단순 baseline보다 정확도와
   runtime 양쪽에서 이득이 확인되기 전에는 제출하지 않는다.
3. `batch_size`는 호출 총량을 줄이지 않는다. 128개 긴 prompt와 호출당
   `max_tokens=2500`은 scheduler/KV-cache 압력을 높일 수 있으므로, GPU 실측이
   없는 상태에서 timeout의 해결책으로 batch만 키우거나 고정하지 않는다.
4. 기본 전략은 실제 공고를 넣는 **단일 호출 또는 adaptive overflow split**이어야
   한다. 항목 그룹화·문서별 독립 호출은 그보다 강한 근거가 생긴 경우에만 ablation으로
   다룬다.

## 외부 기준선: vanilla prompt 제출

동료가 전달한 제출 관측은 다음과 같다.

| 방식 | runtime | leaderboard score | 재현 상태 |
| --- | ---: | ---: | --- |
| RAG·추가 후처리 없이, 전체 24항목을 한 번에 예측하는 기본 prompt-engineering | 약 32분 | 0.32734 | 원본 config/zip 미확보 |

이는 EXP014 제출의 0.183495 및 EXP044 timeout보다 훨씬 강한 신호다. 다만 이
수치는 아직 동일 데이터·동일 decoding·동일 evidence 처리의 local 재현물이 없으므로,
어떤 문구가 원인인지 또는 dev-200과 왜 다른지 결론 내릴 수 없다.

그럼에도 다음 가설은 우선순위가 높다.

- 공개 dev-200과 실제 평가의 분포 차이가 크다. dev-200의 Macro-F1만으로 복잡한
  후처리를 선택하면 실제 평가에서 악화될 수 있다.
- OpenRouter Gemma와 offline vLLM Gemma의 provider/template/structured-decoding
  차이가 local 순위를 뒤집을 수 있다.
- 문서별 strict evidence gate, 카드·제품문맥, 다중 호출 OR/AND merge가 Gemma의
  원래 판단을 과도하게 0으로 강등하거나 문맥을 분절했을 수 있다.
- 한 번에 전 항목을 보여주는 단순한 문제 정의가 Gemma가 항목 간 공통 맥락을
  이용하게 하며, 이득은 RAG보다 prompt 구조에 있을 수 있다.

다음 연구의 출발점은 복잡한 RAG의 추가가 아니라, 동료 제출의 **정확한 prompt,
vLLM chat template, structured-output 설정, decoding parameter, evidence 정책**을
확보해 동일 shared pipeline에서 dev-200과 제출 runtime으로 재현하는 일이다.

## 2026-09-06: EXP-123의 local-to-public 일반화 한계

`pps_20260906_233304.zip` (EXP-123: EXP-120에 v2/v3/v21 source-grounded
fixed rule을 합성)의 관측치는 다음과 같다.

| 기준 | Macro positive-F1 |
| --- | ---: |
| EXP-120 public | 0.2443173108 |
| EXP-123 dev-200 | 0.317797 |
| EXP-123 public | 0.2604457110 |

EXP-123은 public에서 +0.0161284002로 상승했으므로 세 rule이 완전히 무효인 것은
아니다. 그러나 dev 상승폭 +0.068865의 대부분은 public으로 전이되지 않았다. 이
관측 이후에는 dev 오류를 보고 항목별 predicateㆍ숫자ㆍ키워드 rule을 추가 누적하지
않는다. 다음 후보는 개별 보정이 아니라 실행 계약 또는 input/output task 구조의
독립적인 한 가지 변화여야 한다. 상세 전략과 gate는
[`strategic_reset_post_exp123.md`](strategic_reset_post_exp123.md)에 기록한다.

## 2026-09-07: 34-minute submission and bounded multi-call budget

The organizer-format single-call submission observation is approximately
34 minutes. A bounded notice-level second or third Gemma call may therefore
fit the two-hour limit, but this does not rescue document-split × group
multiplication.

Remote token observations on the same frozen fast-20 make the distinction
concrete:

| Policy | Calls | Prompt tokens | Completion tokens | Total tokens | Ratio to single call |
| --- | ---: | ---: | ---: | ---: | ---: |
| EXP125A exact organizer single call | 20 | 75,381 | 15,173 | 90,554 | 1.00× |
| EXP139 full 24-item call + focused five-item call | 40 | 140,902 | 18,811 | 159,713 | 1.76× |

The focused five-item response repeats the notice prompt but has only about
one fifth of baseline completion tokens. A first-order projection from 34
minutes is roughly 55–72 minutes for two calls and 82–108 minutes for three.
Provider/vLLM scheduling can move these figures, so they are planning bounds,
not an inference guarantee. Four whole-notice calls have no safe margin.

Admissible future structures are: a full 24-item call plus one semantically
complete fixed-group verifier; or a full call plus a verifier invoked only for
a declared first-pass output condition. The latter is precision-oriented and
cannot recover first-pass false negatives. Both need a versioned merge policy.
At most three whole-notice calls may be considered after semantic-input review,
exact rendered-input review, mock, and runtime projection.

Excluded structures remain `full_split_merge × v grouping`, per-v calls, and
any verifier prompt that lacks the full legal condition it is meant to verify.
EXP141 was invalidated for the last reason; the next multi-call candidate must
first pass `docs/semantic_input_contract_v1.md`.

## 2026-09-07: two-way partition submission candidate

Today's package uses the only grouped execution policy with a completed
fast-panel, independent-holdout, and dev-200 quality signal:
`document_restrictions_two_way_v1` (EXP133/134/135).  It has exactly two
disjoint whole-notice calls per notice under the organizer 4,000-character
context:

| Call | Output items | Context / merge |
| --- | --- | --- |
| G01 | `v1`–`v5`, `v10`–`v18`, `v20`–`v24` | Same ordered 4,000-character organizer context; its 19 columns are final. |
| G02 | `v6`–`v9`, `v19` | The identical context; its five columns are final. |

The calls do not overlap, vote, OR/AND-merge, or split documents. Thus the
final row has exactly one LLM source per v item. EXP135 dev-200 macro
positive-F1 was 0.24694 against its single-call organizer control's 0.22350.
Its call count is exactly `1 context × 2 groups = 2` per notice; no overflow
document contexts are admitted by this policy.

The packaged candidate is `dist/pps_20260907_174343.zip`. It was built only
after root `config.yaml` and `submission/runtime_config.json` were made equal
on prompt policy and grouping. A fresh unzip/staged `script.py --mock` run
with organizer-shaped temporary input completed two notices through both
groups, with 49 ordered CSV columns, zero malformed retries, and zero
unrecovered passes. The zip contains 23 files and is about 60 KB.

The mac environment still has no competition vLLM/GPU model directory, so no
offline batch-64 throughput or malformed-output smoke test was claimed.
The 34-minute real single-call observation projects two whole-notice calls to
roughly 55–72 minutes, below the two-hour limit but not a substitute for an
actual evaluator runtime measurement. This candidate deliberately does not
include EXP146's global two-pass adjudication: it declined on dev-200 and had
a severe malformed-output runaway on `PPS-DEV-160`.
