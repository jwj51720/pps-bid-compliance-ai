좋습니다. 이 대회에서는 **“서비스처럼 예쁘게 설계된 구조”보다 “내가 3주 뒤에도 어디서 뭐가 돌아가는지 바로 알 수 있는 구조”**가 훨씬 중요합니다.

특히 핵심 원칙은 하나로 잡는 게 좋겠습니다.

> **실험과 실제 제출은 같은 파이프라인을 실행하고, 입력 데이터·LLM 연결 방식·출력 위치만 다르게 한다.**

즉 `experiment용 코드`와 `submission용 코드`를 따로 구현하면 안 됩니다. 제출용 `script.py`는 최대한 얇은 entrypoint로 만들어야 합니다.

아래 구조를 추천합니다.

# PPS Bid Compliance AI — Project Structure

## 1. 설계 원칙

본 프로젝트는 서비스 출시나 장기적인 확장성을 목적으로 하지 않는다.

목표는 하나다.

**나라장터 자체입찰 공고 법령 위반사항 모니터링 AI 경진대회에서 높은 성능을 달성하는 것.**

따라서 다음 세 가지를 최우선 설계 원칙으로 한다.

### 1. 가시성

대회의 모든 실험과 제출 코드에 대해 개발자가 직접 책임질 수 있어야 한다.

따라서:

* 코드 위치만 보고도 역할을 파악할 수 있어야 한다.
* 과도한 Factory / Registry / Dependency Injection 등의 추상화를 사용하지 않는다.
* 하나의 동작을 확인하기 위해 여러 디렉토리를 따라가지 않도록 한다.
* 대회 핵심 로직인 `rule`, `prompt`, `RAG`, `LLM`, `evidence`, `evaluation`을 명확히 노출한다.
* 실험 결과와 사용한 config를 항상 함께 저장한다.

---

### 2. 간결함

같은 로직을 실험용과 제출용으로 중복 구현하지 않는다.

특히 다음 구조를 피한다.

```text
experiment_pipeline.py
submission_pipeline.py
```

두 파일에서 비슷한 코드를 따로 관리하면 시간이 지나면서 반드시 동작이 달라진다.

대신:

```text
공통 pipeline
    ↑
    ├── experiment entrypoint
    └── submission entrypoint
```

구조를 사용한다.

실험과 제출의 차이는 가능한 한 **config와 실행 환경만으로 표현한다.**

---

### 3. 실험 반복 가능성

모든 실험은 실제 대회 제출과 최대한 동일한 흐름으로 실행한다.

```text
입력 데이터
    ↓
전처리
    ↓
Rule / RAG
    ↓
LLM
    ↓
후처리
    ↓
Evidence
    ↓
submission.csv 생성
    ↓
정답이 존재하면 평가
```

따라서 로컬 실험에서도 최종적으로 실제 제출 형식과 동일한 `submission.csv`를 생성한다.

그 뒤 공개된 dev 정답셋이 존재하는 경우 동일한 파일을 그대로 평가한다.

---

# 2. 권장 디렉토리 구조

```text
pps-bid-compliance-ai/
│
├── README.md
├── requirements.txt
├── .gitignore
├── .env.example
│
├── configs/
│   ├── default.yaml
│   ├── exp001_baseline.yaml
│   ├── exp002_prompt.yaml
│   └── exp003_rag.yaml
│
├── data/
│   ├── raw/
│   │   ├── dev.jsonl.gz
│   │   ├── dev_labels.csv
│   │   ├── train_unlabeled.jsonl.gz
│   │   ├── 항목표.json
│   │   └── 법령패키지/
│   │
│   └── processed/
│       └── ...
│
├── src/
│   ├── pipeline.py
│   ├── loader.py
│   ├── preprocess.py
│   │
│   ├── prompts/
│   │   ├── base.py
│   │   └── violation.py
│   │
│   ├── rules/
│   │   ├── common.py
│   │   ├── violation.py
│   │   └── absence.py
│   │
│   ├── rag/
│   │   ├── law.py
│   │   └── examples.py
│   │
│   ├── llm/
│   │   ├── openrouter.py
│   │   ├── openai.py
│   │   └── local_gemma.py
│   │
│   ├── evidence.py
│   ├── postprocess.py
│   ├── submission.py
│   └── evaluate.py
│
├── scripts/
│   ├── run_experiment.py
│   ├── evaluate.py
│   ├── label_train.py
│   ├── build_rag.py
│   └── make_submission_zip.py
│
├── submission/
│   ├── script.py
│   └── requirements.txt
│
├── outputs/
│   ├── exp001/
│   ├── exp002/
│   └── ...
│
├── artifacts/
│   ├── rag/
│   ├── labels/
│   └── cache/
│
└── docs/
    ├── competition.md
    ├── architecture.md
    ├── experiments.md
    ├── error-analysis.md
    └── ideas.md
```

---

# 3. 각 디렉토리의 책임

## `configs/`

실험 조건을 저장한다.

코드 안에 다음과 같은 값을 직접 박아 넣지 않는다.

```python
DEV_PATH = "./data/dev.jsonl.gz"
TEMPERATURE = 0.1
TOP_K = 5
MODEL = "..."
```

대신 config에서 관리한다.

예:

```yaml
experiment:
  name: exp003_rag

data:
  input_path: data/raw/dev.jsonl.gz
  label_path: data/raw/dev_labels.csv
  output_dir: outputs/exp003_rag

llm:
  provider: openrouter
  model: google/gemma-4-27b-it
  temperature: 0.0
  max_tokens: 4096

rag:
  enabled: true
  law_top_k: 3
  example_top_k: 3

rules:
  enabled: true

evaluation:
  enabled: true
```

실험을 재현할 때는:

```bash
python scripts/run_experiment.py \
    --config configs/exp003_rag.yaml
```

만 실행하면 되도록 한다.

---

# 4. `src/pipeline.py`

프로젝트의 핵심이다.

**한 공고를 받아 최종 24개 판정과 evidence를 생성하는 전체 흐름만 담당한다.**

예를 들면 개념적으로:

```python
def predict_notice(notice, config):
    notice = preprocess(notice)

    rule_context = apply_rules(notice)
    rag_context = retrieve_context(notice)

    prompt = build_prompt(
        notice=notice,
        rule_context=rule_context,
        rag_context=rag_context,
    )

    result = call_llm(prompt)

    result = postprocess(result, notice)
    result = extract_evidence(result, notice)

    return result
```

중요한 점은 `pipeline.py` 안에 세부 구현을 전부 넣지 않는 것이다.

Pipeline은:

```text
무엇을 어떤 순서로 호출하는가
```

만 보여줘야 한다.

이 파일 하나를 읽으면 전체 시스템의 동작을 이해할 수 있어야 한다.

---

# 5. `src/llm/`

외부 시스템과 통신하는 코드는 전부 이곳에 둔다.

```text
src/llm/
├── openrouter.py
├── openai.py
└── local_gemma.py
```

## `openrouter.py`

로컬 실험에서 Gemma API 호출.

```python
response = generate(
    messages=messages,
    model=model,
)
```

정도의 단순한 interface를 제공한다.

---

## `openai.py`

train_unlabeled 자가 라벨링 등에 사용할 OpenAI API.

Gemma inference와 역할이 완전히 다르므로 별도 파일로 분리한다.

---

## `local_gemma.py`

실제 DACON 평가 환경에서 제공되는 Gemma를 호출한다.

중요한 점은 Pipeline 입장에서는:

```python
llm.generate(...)
```

의 반환 형식이 최대한 동일해야 한다는 것이다.

다만 이를 위해 복잡한 추상화 계층까지 만들 필요는 없다.

예를 들어 단순히:

```python
if provider == "openrouter":
    from src.llm.openrouter import generate

elif provider == "local_gemma":
    from src.llm.local_gemma import generate
```

정도로도 충분하다.

대회를 위해 `BaseLLM`, `AbstractLLMProvider`, `LLMFactory` 같은 구조까지 만드는 것은 피한다.

---

# 6. `src/prompts/`

Prompt는 코드와 분리한다.

Prompt가 이 대회에서 사실상 모델의 일부이기 때문이다.

```text
src/prompts/
├── base.py
└── violation.py
```

예를 들어:

```python
SYSTEM_PROMPT = """
너는 나라장터 자체입찰 공고의 ...
"""
```

형태로 관리한다.

실험 과정에서 prompt 변경이 매우 많을 가능성이 높기 때문에 다른 코드에 긴 prompt 문자열을 넣지 않는다.

---

# 7. `src/rules/`

24개 항목을 반드시 `v01.py ~ v24.py`로 쪼갤 필요는 없다.

초기부터 이렇게 만들면 오히려 탐색성이 떨어질 가능성이 있다.

대신 성격에 따라 먼저 나눈다.

```text
rules/
├── common.py
├── violation.py
└── absence.py
```

예:

### `common.py`

공통 parser.

```text
금액 추출
지역 추출
날짜 추출
문서 유형
meta 비교
```

### `violation.py`

문서에 존재하는 표현을 기반으로 하는 위반 규칙.

### `absence.py`

v10, v11 등과 같이 특정 내용의 부재를 탐지하는 규칙.

규칙 수가 많아져 한 파일이 지나치게 커질 때만 이후에:

```text
rules/
├── v01.py
├── v02.py
...
```

로 분리한다.

**미리 복잡하게 만들지 않는다.**

---

# 8. `src/rag/`

RAG도 역할을 두 개로만 나눈다.

```text
rag/
├── law.py
└── examples.py
```

## `law.py`

공식 법령에서 관련 조항 검색.

## `examples.py`

dev 또는 self-labeled train 데이터에서 유사 사례 검색.

두 retrieval은 목적 자체가 다르기 때문에 명확히 분리한다.

---

# 9. `src/evidence.py`

Evidence는 별도의 책임으로 분리한다.

LLM이 판단한 문장을 그대로 submission에 넣지 않는다.

```text
LLM
 ↓
candidate evidence
 ↓
원문 검색
 ↓
exact substring
```

을 담당한다.

예:

```python
def resolve_evidence(candidate, documents):
    ...
```

그리고 다음을 보장한다.

```text
evidence가 실제 입력 문서 substring인지
500자 이하인지
v=0인 경우 불필요한 evidence가 들어가지 않는지
부재 탐지 항목에서는 blank인지
```

---

# 10. `src/submission.py`

예측 결과를 **대회 submission 형식으로 변환하는 역할만** 한다.

즉:

```python
results
    ↓
DataFrame
    ↓
id
v1 ... v24
e1 ... e24
```

를 생성한다.

실험과 실제 제출 모두 반드시 이 함수를 사용한다.

```python
submission = build_submission(results)
submission.to_csv(...)
```

이렇게 하면 로컬에서는 정상인데 DACON에서는 column 구조가 다르게 나오는 문제를 방지할 수 있다.

---

# 11. `src/evaluate.py`

`submission.csv`와 정답 파일을 비교한다.

Pipeline 내부에서 직접 평가하지 않는다.

```text
prediction
    ↓
submission.csv
    ↓
evaluation
```

순서를 유지한다.

이렇게 해야 실제 제출 상황을 그대로 재현할 수 있다.

예:

```python
metrics = evaluate_submission(
    submission_path,
    label_path,
)
```

출력은 최소:

```text
Macro F1

v1 precision / recall / F1
v2 precision / recall / F1
...
v24 precision / recall / F1
```

을 포함한다.

가능하면 추가로:

```text
FP id 목록
FN id 목록
```

도 저장한다.

---

# 12. `scripts/run_experiment.py`

실험의 메인 entrypoint다.

사용자는 대부분 이 파일만 실행하게 된다.

```bash
python scripts/run_experiment.py \
    --config configs/exp003_rag.yaml
```

실행 흐름:

```text
config load
     ↓
input load
     ↓
pipeline 실행
     ↓
submission.csv 생성
     ↓
정답 존재 여부 확인
     ↓
evaluation
     ↓
metrics 저장
```

예를 들어:

```text
outputs/
└── exp003_rag/
    ├── config.yaml
    ├── submission.csv
    ├── metrics.json
    ├── per_label.csv
    ├── predictions.jsonl
    └── errors.csv
```

를 만든다.

여기서 특히 중요한 것은:

### 실행 당시 config를 output에 복사한다.

나중에:

```text
exp017이 왜 잘 나왔지?
```

라고 했을 때 Git history까지 뒤지지 않아도 된다.

---

# 13. 실제 제출과 실험의 관계

가장 중요한 구조다.

## Local Experiment

```text
scripts/run_experiment.py
        ↓
config
        ↓
src.pipeline
        ↓
OpenRouter Gemma
        ↓
src.submission
        ↓
outputs/expXXX/submission.csv
        ↓
src.evaluate
```

---

## DACON Submission

```text
submission/script.py
        ↓
DACON 환경변수 / 경로
        ↓
src.pipeline
        ↓
Local Gemma
        ↓
src.submission
        ↓
$PPS_OUTPUT_DIR/submission.csv
```

즉 실제 핵심 코드는 같다.

차이는 다음뿐이다.

| 항목         | 실험             | 실제 제출          |
| ---------- | -------------- | -------------- |
| Input      | dev            | test           |
| Gemma      | OpenRouter     | DACON Local    |
| Label      | 존재             | 없음             |
| Evaluation | 실행             | 실행 안 함         |
| Output     | outputs/expXXX | PPS_OUTPUT_DIR |

---

# 14. `submission/script.py`는 최대한 얇게 만든다

예를 들어 개념적으로 다음 정도만 담당해야 한다.

```python
def main():
    config = load_submission_config()

    notices = load_test_data(config)

    results = run_pipeline(
        notices,
        config,
    )

    submission = build_submission(results)

    save_submission(
        submission,
        config.output_path,
    )


if __name__ == "__main__":
    main()
```

여기에:

```text
prompt
rule
RAG
evidence 처리
```

등이 직접 들어가면 안 된다.

`script.py`는 DACON이 요구하는 실행 interface일 뿐이다.

---

# 15. 단, 제출 패키지는 self-contained하게 만들어야 한다

개발 repository는:

```text
src/
submission/
...
```

구조를 사용하지만 실제 `submit.zip`을 만들 때는 필요한 코드를 함께 묶어야 한다.

이를:

```text
scripts/make_submission_zip.py
```

가 담당한다.

예:

```text
dist/
└── submit.zip
```

안에는:

```text
script.py
src/
artifacts/
requirements.txt
```

등 필요한 파일만 포함한다.

이 과정도 수동으로 하지 않는 것이 좋다.

```bash
python scripts/make_submission_zip.py
```

한 번으로 만들어져야 한다.

---

# 16. `artifacts/`

코드가 아닌 **실험 결과로 생성된 재사용 자산**을 저장한다.

예:

```text
artifacts/
├── rag/
│   ├── law_index/
│   └── example_index/
│
├── labels/
│   ├── train_self_labels.jsonl
│   └── high_confidence.jsonl
│
└── cache/
    └── ...
```

특히:

```text
OpenAI를 이용한 self labeling 결과
```

는 `data/raw`에 넣지 않는다.

원본 데이터와 우리가 생성한 데이터를 반드시 구분한다.

---

# 17. `outputs/`

**실험 결과 전용 디렉토리다.**

```text
outputs/
├── exp001_baseline/
├── exp002_prompt_v2/
├── exp003_law_rag/
└── ...
```

각 experiment에는 가능하면 다음을 남긴다.

```text
config.yaml
submission.csv
metrics.json
per_label.csv
predictions.jsonl
errors.csv
run.log
```

이렇게 하면:

> 실험 결과가 코드 상태와 분리되어 사라지는 문제

를 방지할 수 있다.

---

# 18. `docs/`

대회 중 생각나는 내용은 코드 안의 TODO가 아니라 문서에 정리한다.

추천:

```text
docs/
├── competition.md
├── architecture.md
├── experiments.md
├── error-analysis.md
└── ideas.md
```

## `competition.md`

공식 규칙 요약.

특히:

```text
제출 조건
허용 모델
금지 모델
시간 제한
파일 제한
평가 방식
```

등을 적는다.

---

## `architecture.md`

현재 파이프라인 구조.

---

## `experiments.md`

실험 로그.

예:

```markdown
## EXP-007

### 변경

- law RAG top-k 3 → 5
- prompt에 정상 사례 추가

### 결과

Macro F1
0.612 → 0.631

### 관찰

v3 recall 증가
v7 FP 증가

### 다음 실험

v7 관련 법령 retrieval 제한
```

---

## `error-analysis.md`

항목별 주요 실패 패턴.

```markdown
## v3

### FP

- 계약금액 표현을 실적금액으로 오인

### FN

- 별첨 문서 안의 실적 조건 탐지 실패
```

이 문서는 대회 후반으로 갈수록 매우 중요해진다.

---

## `ideas.md`

아직 실험하지 않은 아이디어.

코드에 TODO를 수십 개 남기는 것보다:

```text
아이디어 backlog
```

를 따로 두는 것이 좋다.

---

# 19. Config 관리 원칙

Config에는 **실험하면서 변경할 값**만 넣는다.

잘못된 예:

```yaml
submission:
  columns:
    - id
    - v1
    - v2
    ...
```

대회에서 절대 바뀌지 않는 구조까지 config로 빼지 않는다.

좋은 대상:

```text
data path
output path

LLM provider
LLM model
temperature

prompt version

RAG enable
RAG top-k

rule enable

batch size
max tokens

cache 여부
```

즉:

> 코드를 config-driven framework로 만들지 말고, 실험 parameter만 config에 둔다.

---

# 20. 실험 ID 규칙

실험 이름은 자동 timestamp보다는 사람이 읽을 수 있게 하는 것이 좋다.

예:

```text
exp001_baseline
exp002_prompt_v2
exp003_law_rag
exp004_example_rag
exp005_v3_rule
```

그래야:

```text
exp034가 뭐였지?
```

가 아니라 디렉토리 이름만 보고 기억할 수 있다.

Git branch까지 실험별로 만드는 것은 과하다.

대신 의미 있는 실험마다 commit:

```text
exp005: add v3 threshold rule
```

정도면 충분하다.

---

# 21. API Cache는 초기에 고려한다

OpenRouter나 OpenAI를 반복 호출하면:

```text
비용
속도
API variance
```

문제가 생긴다.

따라서 동일한:

```text
model
prompt
notice
generation config
```

조합에 대해서는 결과를 cache할 수 있게 해두는 것이 좋다.

예:

```text
artifacts/cache/
```

key:

```text
SHA256(
    model
    + prompt
    + input
    + generation_config
)
```

단, cache 시스템 자체가 복잡해져서는 안 된다.

단순 JSONL / JSON 파일 수준이면 충분하다.

---

# 22. Logging은 최소한으로 명확하게

복잡한 logging framework는 필요 없다.

최소:

```text
[001/200] notice_id=...
[LLM] 1.83 sec
[RAG] law=3 example=3
[PRED] v1=0 v2=1 ...
```

정도로 현재 어디까지 실행됐는지 알 수 있어야 한다.

전체 로그는:

```text
outputs/expXXX/run.log
```

로 남긴다.

---

# 23. 중요한 금지사항

## 1. 실험 코드와 제출 코드를 따로 만들지 않는다.

가장 위험하다.

---

## 2. `utils.py`에 모든 것을 넣지 않는다.

예:

```text
utils.py
```

안에:

```text
load data
call llm
parse amount
calculate f1
save csv
```

가 다 들어가는 순간 구조가 무너진다.

역할이 명확하면 파일 이름 자체가 역할을 표현하도록 한다.

---

## 3. 초기부터 클래스 중심으로 설계하지 않는다.

예:

```python
class PipelineManager:
class RAGManager:
class RuleManager:
class PromptManager:
```

대부분 필요 없다.

이 대회에서는 pure function 위주의 코드가 오히려 읽기 쉽다.

---

## 4. v1~v24를 처음부터 각각 완전히 독립된 시스템으로 만들지 않는다.

공통 로직이 많다.

먼저:

```text
공통 parser
공통 rule
공통 prompt
```

를 만들고 실제 차이가 커진 항목만 분리한다.

---

## 5. Experiment가 DataFrame을 직접 만들어 평가하게 하지 않는다.

항상:

```text
pipeline
→ submission.csv
→ evaluator
```

를 거친다.

그래야 실제 제출과 동일한 형식 자체도 테스트된다.

---

## 6. 외부 API 코드를 pipeline 안에 직접 작성하지 않는다.

잘못된 예:

```python
def predict_notice(...):
    response = requests.post(
        "https://openrouter.ai/..."
    )
```

이렇게 하면 DACON local Gemma로 변경하기 어려워진다.

반드시 `src/llm/`을 통과한다.

---

# 24. 최종적으로 원하는 개발 경험

실험은:

```bash
python scripts/run_experiment.py \
  --config configs/exp005_v3_rule.yaml
```

하나로 실행된다.

결과:

```text
outputs/exp005_v3_rule/

├── config.yaml
├── submission.csv
├── metrics.json
├── per_label.csv
├── predictions.jsonl
├── errors.csv
└── run.log
```

터미널:

```text
Experiment: exp005_v3_rule
Data: dev

Processing 200 notices...
200 / 200 complete

Macro F1: 0.6813

Worst labels
v03   0.4211
v17   0.4878
v24   0.5032

Output:
outputs/exp005_v3_rule/submission.csv
```

그리고 실제 제출은:

```bash
python submission/script.py
```

이며 내부적으로 **동일한 `src.pipeline`을 호출한다.**

---

# 25. 핵심 구조 요약

전체 프로젝트에서 실질적으로 기억해야 하는 흐름은 이것 하나면 된다.

```text
                 configs/
                    │
                    ↓
data ───────→ pipeline.py
                    │
       ┌────────────┼────────────┐
       ↓            ↓            ↓
     rules         rag          llm
                                  │
                                  ↓
                              prompts
                    │
                    ↓
               postprocess
                    │
                    ↓
                evidence
                    │
                    ↓
               submission
                    │
           ┌────────┴─────────┐
           ↓                  ↓
       experiment          DACON
           │
           ↓
       evaluation
```

이 프로젝트에서 가장 중요한 설계 원칙은:

**“대회 제출 코드를 따로 개발하지 않는다.”**

실험 자체가 항상 작은 규모의 실제 제출이어야 한다.

따라서

```text
로컬 dev 실행
```

과

```text
DACON test 실행
```

사이의 차이는 최대한 다음 세 가지에만 존재하게 만든다.

```text
입력 데이터
LLM provider
평가 여부
```

나머지 코드 경로는 동일하게 유지한다.

한 가지는 제가 위 구조에서 특히 강하게 추천합니다. **`submission/script.py`와 `scripts/run_experiment.py`를 서로 다른 프로그램으로 생각하지 않는 것**입니다. 둘 다 같은 `pipeline`을 실행하는 entrypoint이고, `run_experiment.py`에만 마지막 `evaluate()` 단계가 하나 더 붙어 있다고 생각하면 됩니다.

그리고 지금 단계에서는 `rules/v01.py ~ v24.py`, `models/`, `services/`, `core/`, `interfaces/`, `repositories/` 같은 구조는 일부러 만들지 않는 게 좋습니다. 대회 코드에서 그런 디렉토리가 생기기 시작하면 보통 “구조는 근사한데 내가 코드 찾는 시간이 길어지는” 방향으로 갑니다.
