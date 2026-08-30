첫 번째 실험은 말씀하신 대로 **성능 실험이라기보다 “대회 시스템 전체를 한 번 성공적으로 관통하는 기준 실험”**으로 정의하는 게 좋습니다. RAG나 self-labeling은 후보 전략으로만 기록하고, 이번에는 일부러 건드리지 않는 방향으로 정리했습니다.

# EXP-001 — First Submission Baseline

## 1. 실험 개요

### Experiment ID

```text
exp-001-first-submission
```

### 목적

본 실험의 최우선 목표는 모델 성능을 극대화하는 것이 아니다.

**대회에서 요구하는 전체 실행 과정을 로컬에서 재현하고, 실제 DACON 제출까지 최초로 성공시키는 것**이 목표다.

전체 과정은 다음과 같다.

```text
공식 데이터 확인
    ↓
데이터 로딩
    ↓
Baseline Prompt 생성
    ↓
Gemma 추론
    ↓
v1~v24 / e1~e24 생성
    ↓
submission.csv 생성
    ↓
dev 정답으로 로컬 평가
    ↓
실제 제출 환경 재현
    ↓
submit.zip 생성
    ↓
DACON 제출
    ↓
Leaderboard Score 기록
```

이 실험을 통해 이후 모든 실험의 기준이 되는:

* 데이터 구조
* 실행 방식
* 출력 형식
* 평가 방식
* 실험 결과 기록 방식
* 제출 방식

을 확정한다.

---

# 2. 이번 실험에서 하지 않는 것

EXP-001은 가능한 한 단순한 baseline으로 유지한다.

따라서 다음 전략은 이번 실험에서 사용하지 않는다.

```text
RAG
Self-labeling
LLM Wiki
Embedding Retrieval
FAQ Retrieval
Rule-based Correction
복잡한 Post-processing
항목별 개별 Prompt 최적화
```

이번 실험의 목적은:

> 좋은 모델을 만드는 것

이 아니라:

> 앞으로 좋은 모델을 반복해서 실험할 수 있는 기반을 만드는 것

이다.

---

# 3. 공식 데이터 확인 및 문서화

## 3.1 `open.zip` 보존

원본 파일은 수정하지 않는다.

```text
data/raw/
└── open.zip
```

원본은 그대로 유지하고 별도의 디렉토리에 압축을 해제한다.

예:

```text
data/raw/
├── open.zip
└── open/
    ├── README.md
    ├── train_unlabeled.jsonl.gz
    ├── dev.jsonl.gz
    ├── dev_labels.csv
    ├── sample_submission.csv
    ├── data/
    └── baseline/
```

공식 제공 데이터는 다음과 같다.

```text
train_unlabeled.jsonl.gz    20,000건 무라벨 공고
dev.jsonl.gz                   200건 검증 공고
dev_labels.csv                 200건 정답
sample_submission.csv           10행 제출 예시
data/test.jsonl.gz               10건 실행 형식 확인용
```

`dev_labels.csv`는 실제 제출 구조와 동일한 49열이다.

```text
id
v1 ~ v24
e1 ~ e24
```

따라서 EXP-001의 로컬 성능 평가는 **dev 200건 전체**를 이용한다.

---

# 4. 데이터 분석 문서 작성

EXP-001에서 반드시 다음 문서를 만든다.

```text
docs/data.md
```

이 문서는 단순 데이터 설명이 아니라 앞으로 프로젝트 전체에서 데이터의 기준 문서 역할을 한다.

최소한 다음 내용을 포함한다.

---

## 4.1 공식 제공 데이터

각 파일에 대해:

```text
파일명
목적
행/공고 수
주요 필드
사용 시점
수정 가능 여부
```

를 기록한다.

---

## 4.2 공고 입력 Schema

`dev.jsonl.gz`, `train_unlabeled.jsonl.gz`, `test.jsonl.gz`의 실제 내용을 확인하여 한 공고가 어떤 구조로 되어 있는지 기록한다.

예:

```text
id
docs
meta
dropped_doc_counts
input_completeness
...
```

`docs` 내부에 대해서도 실제 데이터 기준으로 기록한다.

```text
doc_id
type
text
...
```

문서 종류별 분포도 확인한다.

예:

```text
공고문
규격서
과업지시서
제안요청서
예외공표서
```

---

## 4.3 Metadata

`meta`의 실제 필드를 전부 확인한다.

각 필드에 대해:

```text
필드명
자료형
예시
Null 여부
의미
```

정도를 기록한다.

향후 v24를 비롯한 여러 판정에서 중요할 가능성이 있으므로 원문과 별도로 파악한다.

---

## 4.4 문서 크기

Prompt 설계에 직접 영향을 주므로 최소한 다음을 확인한다.

```text
공고별 문서 수
공고별 총 문자 수
문서 종류별 문자 수
평균
중앙값
P90
P95
최댓값
```

이를 통해 향후:

```text
원문 전체 입력
Truncation
Chunking
RAG
LLM Wiki
```

중 무엇이 필요한지 판단할 근거를 만든다.

---

## 4.5 Label 분포

`dev_labels.csv`에서:

```text
v1 positive 개수
v2 positive 개수
...
v24 positive 개수
```

를 기록한다.

Macro F1 대회이므로 항목별 데이터 수를 반드시 확인한다.

---

# 5. Derived Data 관리 기준

향후 다음과 같은 데이터가 생성될 수 있다.

```text
Embedding Index
법령 Chunk
LLM Wiki
OpenAI Self-label
FAQ Dataset
Hard Negative Set
Prompt용 Example Set
```

이들은 모두:

```text
data/derived/
```

아래에 저장한다.

다만 EXP-001에서는 구체적인 derived 구조를 미리 정하지 않는다.

대신 **추적 방법만 먼저 정의한다.**

---

# 6. Derived Data Registry

다음 파일을 만든다.

```text
data/derived/registry.yaml
```

생성된 derived data마다 고유 ID를 부여한다.

예:

```yaml
drv-063-faq-labels:
  description: >
    train_unlabeled에서 OpenAI API를 이용해 생성한
    FAQ RAG용 self-label 데이터

  created_by:
    experiment: exp-063

  source:
    - data/raw/open/train_unlabeled.jsonl.gz

  generator:
    script: scripts/label_train.py

  output:
    - data/derived/faq_labels_v1.jsonl

  purpose:
    - FAQ RAG
    - Few-shot retrieval

  created_at: 2026-09-XX
```

핵심은 **실험 번호와 derived data 번호를 구분하는 것**이다.

예를 들어:

```text
exp-081
```

이 실행될 때:

```text
drv-063-faq-labels
```

을 사용할 수 있다.

즉:

```text
Experiment
≠
Derived Data
```

이다.

---

# 7. 실험에서 Derived Data 사용 추적

실험 설정에는 사용한 derived data ID를 기록한다.

예:

```yaml
experiment:
  id: exp-081

derived_data:
  - drv-063-faq-labels
  - drv-071-law-wiki-v2
```

그러면 나중에:

> exp-081의 성능이 왜 좋았는가?

를 확인할 때 어떤 코드뿐 아니라 **어떤 파생 데이터를 사용했는지까지 추적할 수 있다.**

EXP-001에서는:

```yaml
derived_data: []
```

이다.

---

# 8. EXP-001 Baseline 전략

## 8.1 RAG

비활성화한다.

```yaml
rag:
  enabled: false
```

이번 실험에서는 외부 Knowledge Retrieval 없이 기본 입력만 사용한다.

---

# 9. 향후 RAG 후보

이번 실험에서는 구현하지 않지만 `docs/ideas.md`에 다음 전략을 기록한다.

## Candidate 1 — Naive RAG

공식 제공 embedding model을 이용한다.

```text
법령
 ↓
Chunking
 ↓
Embedding
 ↓
Vector Search
 ↓
관련 법령 Context
```

Embedding 모델의 사용 방식은 추후 결정한다.

가능한 방법:

```text
HuggingFace에서 로딩
사전 다운로드 후 로컬 사용
평가 패키지에 정적 자산으로 포함
```

실제 DACON 평가 환경과 규칙을 고려하여 결정한다.

---

## Candidate 2 — LLM Wiki

법령과 판정 기준을 LLM을 이용해 미리 구조화한다.

예:

```text
v1
 ├─ 판단 조건
 ├─ 관련 법령
 ├─ 예외
 ├─ Positive Pattern
 └─ Negative Pattern
```

이를 하나의 정형화된 Knowledge Base로 만든 뒤 Prompt Context로 사용한다.

---

## Candidate 3 — Self-label + FAQ RAG

공식 제공:

```text
train_unlabeled 20,000건
```

을 OpenAI API 등을 이용해 self-labeling한다.

이후:

```text
공고
+
v1~v24 판단
+
evidence
+
reasoning
```

형태의 사례 DB를 만든다.

추론 시 현재 공고와 비슷한 사례를 찾아:

```text
Current Notice
      ↓
Similar Cases
      ↓
Few-shot / FAQ Context
      ↓
Gemma
```

방식으로 사용한다.

---

# 10. Baseline LLM

로컬 실험에서는 OpenRouter를 통해 Gemma 계열 모델을 호출한다.

```text
src/external/openrouter.py
```

실제 DACON 제출에서는 평가 서버에서 제공하는 Gemma를 호출한다.

```text
src/external/local_gemma.py
```

두 환경의 입력과 출력 interface는 최대한 동일하게 유지한다.

단:

> OpenRouter의 실행 환경과 DACON 평가 서버의 실행 환경은 완전히 동일하지 않을 수 있다.

따라서 로컬 점수와 실제 Leaderboard 점수가 정확하게 일치할 것이라고 가정하지 않는다.

---

# 11. Baseline Prompt

EXP-001의 Prompt는 최대한 단순하게 구성한다.

기본적으로 모델이 받을 정보는 다음이다.

```text
24개 검토 항목 정의
+
현재 공고 docs
+
현재 공고 meta
```

모델은 최종적으로:

```text
v1 ~ v24
e1 ~ e24
```

를 생성한다.

Prompt engineering 자체는 EXP-001의 연구 대상이 아니다.

목표는:

```text
파싱 가능
형식 안정적
24개 항목 누락 없음
```

정도이다.

---

# 12. Structured Output

가능하면 JSON Schema 기반 structured output을 사용한다.

개념적으로:

```json
{
  "v1": 0,
  "e1": "",
  "v2": 1,
  "e2": "...",
  ...
}
```

형식으로 받는다.

이 단계의 목표는 모델 성능보다:

```text
Parsing Failure = 0
누락 Field = 0
Invalid v 값 = 0
```

에 가깝다.

---

# 13. 로컬 실행

실험 진입점은:

```bash
python scripts/run_experiment.py
```

이다.

실행 과정:

```text
config load
    ↓
dev 200건 load
    ↓
pipeline
    ↓
OpenRouter Gemma
    ↓
prediction 생성
    ↓
submission.csv 생성
    ↓
submission validation
    ↓
dev_labels.csv 평가
    ↓
실험 결과 저장
```

---

# 14. 실제 제출 형식 그대로 생성

로컬 결과도 반드시 다음 형식으로 끝난다.

```text
id
v1 ~ v24
e1 ~ e24
```

총 49열이다.

즉:

```text
outputs/exp-001-first-submission/submission.csv
```

은 필요하다면 그 자체로 대회 제출 결과물 형식으로 사용할 수 있어야 한다.

평가만을 위한 별도 prediction format은 만들지 않는다.

---

# 15. Submission Validation

평가 전에 형식 검사를 수행한다.

최소한 다음을 확인한다.

```text
행 수 = 입력 공고 수
49열 존재
Column 순서 일치
id 누락 없음
id 중복 없음
v1~v24 ∈ {0, 1}
evidence 길이 ≤ 500
UTF-8
```

또한 evidence consistency를 검사한다.

일반 항목에서:

```text
v = 0 → e는 빈값
```

이어야 한다.

부재탐지형:

```text
e10
e11
e16
e18
e20
```

은 항상 빈값이어야 한다.

---

# 16. 로컬 평가

평가는 `docs/evaluation.md`에서 정의한 방법을 따른다.

가장 중요한 평가 지표는 세 가지다.

---

## 16.1 Primary — Leaderboard Metric

공식 1차 평가와 동일한 방식으로 계산한다.

각 항목의 positive-class F1을 계산한다.

$$
F1_i =
F1(y_{v_i}, \hat y_{v_i})
$$

그리고:

$$
VScore =
\frac{1}{24}
\sum_{i=1}^{24}F1_i
$$

를 계산한다.

이 값이 EXP-001의 **Primary Metric**이다.

---

## 16.2 Secondary — Evidence Validity

예측한 evidence가 실제 입력 원문의 exact substring인지 확인한다.

$$
EvidenceValidity =
\frac
{\text{원문에 실제 존재하는 Evidence}}
{\text{검증 대상 Evidence}}
$$

목표:

```text
100%
```

Evidence가 LLM에 의해 요약되거나 수정되는 것은 허용하지 않는다.

---

## 16.3 Secondary — Evidence Span F1

정답 `dev_labels.csv`의 evidence span과 예측 evidence가 어느 정도 겹치는지를 측정한다.

개념적으로:

$$
Precision_e =
\frac{|PredictedSpan \cap GoldSpan|}
{|PredictedSpan|}
$$

$$
Recall_e =
\frac{|PredictedSpan \cap GoldSpan|}
{|GoldSpan|}
$$

$$
F1_e =
\frac{2P_eR_e}{P_e+R_e}
$$

로 계산한다.

이를 통해:

```text
근거를 너무 길게 가져오는 경우
근거 일부만 가져오는 경우
잘못된 근거를 가져오는 경우
```

를 구분한다.

이 지표는 공식 2차 평가 점수를 정확하게 재현하는 것이 아니라 **2차 정성평가를 대비하기 위한 Local Proxy Metric**이다.

---

# 17. Per-item 평가

Macro F1 하나만 기록하지 않는다.

반드시:

```text
v1 Precision / Recall / F1
v2 Precision / Recall / F1
...
v24 Precision / Recall / F1
```

을 저장한다.

Evidence 역시 가능하면 항목별로 확인할 수 있게 한다.

이를 통해 다음 실험에서:

```text
어떤 항목을 개선해야 하는가?
```

를 바로 판단할 수 있어야 한다.

---

# 18. EXP-001 결과 디렉토리

실험 결과는 다음처럼 저장한다.

```text
outputs/
└── exp-001-first-submission/
    ├── config.yaml
    ├── run_meta.json
    ├── predictions.jsonl
    ├── submission.csv
    ├── metrics.json
    ├── per_item_metrics.csv
    └── errors.csv
```

---

# 19. `run_meta.json`

실험 자체를 추적하기 위한 metadata다.

예:

```json
{
  "experiment_id": "exp-001-first-submission",
  "git_commit": "abc1234",
  "input": "dev",
  "input_count": 200,
  "derived_data": [],
  "llm_provider": "openrouter",
  "model": "...",
  "rag_enabled": false,
  "created_at": "..."
}
```

향후 derived data를 사용하는 경우:

```json
"derived_data": [
  "drv-063-faq-labels"
]
```

처럼 기록한다.

---

# 20. `metrics.json`

전체 결과를 기계적으로 비교할 수 있도록 저장한다.

예:

```json
{
  "experiment_id": "exp-001-first-submission",

  "leaderboard_metric": {
    "macro_f1": 0.6123
  },

  "evidence": {
    "validity": 0.987,
    "span_f1": 0.841
  }
}
```

구체적인 항목별 점수는:

```text
per_item_metrics.csv
```

에 저장한다.

---

# 21. `errors.csv`

향후 Error Analysis를 위해 최소한 다음 정보를 남긴다.

```text
id
item
gold_v
pred_v
gold_e
pred_e
evidence_valid
evidence_span_f1
```

그러면 예를 들어:

```text
v3 FN만 보기
v9 FP만 보기
Evidence validity 실패만 보기
Span F1 < 0.5만 보기
```

등을 바로 할 수 있다.

---

# 22. 공식 Baseline 실행 구조 확인

우리 코드를 제출하기 전에 공식 제공:

```text
baseline/script.py
```

도 확인한다.

가능하면 공식 안내의 `--mock` 실행을 먼저 수행한다.

목적은 모델 성능 확인이 아니라:

```text
평가 서버 입력 경로
환경변수
출력 경로
submission.csv 생성 방식
requirements 구조
script.py entrypoint
```

를 파악하는 것이다.

공식 예제를 우리가 만드는 제출 pipeline의 reference implementation으로 사용한다.

---

# 23. 평가 서버 형식 사전 테스트

실제 제출 전에 로컬 제공:

```text
data/test.jsonl.gz
```

10건을 대상으로 실행한다.

이 데이터에는 정답이 필요 없다.

목적은:

```text
dev-specific 코드가 없는지
label이 없어도 실행되는지
test input을 정상 처리하는지
submission.csv를 정상 생성하는지
```

확인하는 것이다.

즉:

```text
dev 200 → 성능 검증
test sample 10 → 실제 제출 실행 검증
```

으로 역할을 나눈다.

---

# 24. 제출 패키지 생성

이후:

```bash
python scripts/make_submission.py
```

를 실행하여 실제 제출용 패키지를 만든다.

예:

```text
dist/
└── submit.zip
```

실제 패키지 내부에서는 DACON 평가 서버의:

```text
data
model
embedding model
output
```

경로를 올바르게 참조해야 한다.

---

# 25. 실제 DACON 제출

EXP-001의 마지막 단계는 실제 제출이다.

성능이 좋지 않더라도 제출한다.

이번 제출의 목적은 점수 자체보다:

```text
코드 업로드 성공
requirements 설치 성공
script 실행 성공
Inference 성공
submission.csv 생성 성공
Leaderboard Score 생성 성공
```

을 확인하는 것이다.

---

# 26. Leaderboard 결과 기록

실제 제출이 완료되면 EXP-001 기록에 다음을 추가한다.

```text
DACON 제출 시각
제출 상태
Public Leaderboard Score
전체 실행 성공 여부
실행 관련 오류
```

가능하면 `run_meta.json` 또는 실험 기록 문서에 추가한다.

예:

```json
"dacon_submission": {
  "submitted": true,
  "score": 0.XXXX,
  "submitted_at": "...",
  "status": "success"
}
```

---

# 27. Local Score와 Leaderboard Score

EXP-001에서는 다음 두 값을 확보한다.

```text
Local Dev Macro F1
DACON Leaderboard Macro F1
```

그러나 이 둘의 단순 차이를 모델의 일반화 성능이라고 해석하지 않는다.

이유는:

```text
dev와 test의 데이터 분포가 다름
OpenRouter와 DACON inference 환경이 다를 수 있음
```

때문이다.

따라서 EXP-001에서 얻는 것은 **첫 번째 기준점**이다.

예:

```text
EXP-001

Local     0.58
Leaderboard 0.54
```

이 한 점만으로:

```text
Local 점수가 Leaderboard와 잘 align된다
```

라고 판단할 수 없다.

---

# 28. Alignment는 이후 여러 실험으로 판단

향후:

```text
EXP-001   Local 0.58 → LB 0.54
EXP-004   Local 0.61 → LB 0.57
EXP-008   Local 0.64 → LB 0.60
EXP-012   Local 0.66 → LB 0.59
```

처럼 데이터가 쌓이면 비로소:

```text
Local score 증가가
실제 Leaderboard 증가로 이어지는가?
```

를 판단할 수 있다.

중요한 것은 절대 점수 차이보다:

$$
\Delta Local
$$

과

$$
\Delta Leaderboard
$$

의 방향과 크기다.

이 정보는 이후 dev overfitting 여부를 판단하는 데 사용한다.

---

# 29. EXP-001 성공 조건

다음 조건을 모두 만족하면 EXP-001을 성공으로 본다.

### Data

* `open.zip` 정상 압축 해제
* 공식 데이터 구조 파악
* `docs/data.md` 작성
* `data/derived/registry.yaml` 생성

### Pipeline

* dev 200건 전체 실행 성공
* Parsing Failure 없음
* 24개 v/e 출력 누락 없음

### Submission

* 49열 `submission.csv` 정상 생성
* Submission Validator 통과

### Evaluation

* Macro F1 계산
* v1~v24 개별 F1 계산
* Evidence Validity 계산
* Evidence Span F1 계산
* Error 분석용 결과 저장

### Test Simulation

* sample test 10건 정상 실행
* label이 없는 상태에서도 pipeline 정상 동작

### DACON

* `submit.zip` 생성
* DACON 실제 제출 성공
* Leaderboard Score 획득

---

# 30. EXP-001 종료 시 확보되어야 할 것

EXP-001이 끝나면 최소한 다음 질문에 모두 답할 수 있어야 한다.

```text
공식 데이터는 정확히 어떻게 생겼는가?

한 공고가 모델에 어떻게 들어가는가?

Gemma에게 무엇을 넣고 무엇을 받아야 하는가?

prediction은 어떻게 submission.csv가 되는가?

로컬 Macro F1은 얼마인가?

각 v별로 어디가 취약한가?

Evidence가 실제 원문을 제대로 가리키는가?

실제 DACON 서버에서 코드가 실행되는가?

첫 Leaderboard Score는 얼마인가?

다음 실험에서 가장 먼저 개선할 대상은 무엇인가?
```

이 질문들에 답할 수 있게 되는 순간 **EXP-001의 목적은 달성된 것**으로 본다.

---

# 31. EXP-001 이후

EXP-001 다음 실험부터 비로소 성능 개선을 시작한다.

우선순위는 EXP-001의 실제 Error Analysis 결과를 보고 결정한다.

후보는:

```text
Prompt 개선
법령 Context 추가
Naive RAG
LLM Wiki
Self-labeling
FAQ RAG
Evidence Extraction 개선
항목별 특화 처리
Rule-based Correction
```

등이다.

다만 어떤 방법을 먼저 사용할지는 지금 결정하지 않는다.

**EXP-001의 결과가 다음 실험을 결정한다.**

한 가지 추가로 특히 잘 잡힌 부분은 **`experiment`와 `derived data`를 별도 ID 체계로 둔 것**입니다. 나중에 `exp-081`이 `drv-063`, `drv-071`을 같이 사용했다는 식으로 남길 수 있어야, RAG/자가라벨링 실험이 수십 번 넘어가도 성능의 원인을 추적할 수 있습니다.

그리고 공식적으로 dev는 **200건**, 제출과 같은 49열 정답이 제공되며, 리더보드는 `v1~v24`의 positive-class F1 평균만 사용합니다. `e`는 리더보드에는 들어가지 않지만 2차 평가용으로 보존됩니다. ([DACON][1])

원하면 다음 단계로는 이 EXP-001을 실제 구현하기 위한 **TODO를 개발 순서대로 10~15개 정도의 체크리스트**로 쪼개는 게 가장 자연스럽습니다.

[1]: https://dacon.io/competitions/official/236754/talkboard/417195?utm_source=chatgpt.com "데이터 명세 - DACON"
