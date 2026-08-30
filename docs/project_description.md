다시 전체 페이지를 확인했습니다. 이번에는 **개요·평가·규칙·일정·상금·동의사항·데이터·코드공유·토크·리더보드·제출 페이지까지** 실제로 훑었습니다.

결론부터 말하면, 이 대회는 일반적인 DACON 분류 대회와 성격이 꽤 다릅니다.

> **Gemma를 잘 학습시키는 대회가 아니라, 주어진 Gemma를 얼마나 잘 “조련”해서 법령 위반을 판정하게 만드느냐를 겨루는 대회**입니다.

즉 핵심 경쟁력은 **Prompt Engineering + RAG + Rule Engine + Self-labeling + Evidence Extraction**입니다.

---

# 1. 대회의 목적

주제는:

**나라장터 자체입찰 공고의 법령 위반사항 판정 및 판단 근거 제시 AI 파이프라인 개발**

입니다.

입찰공고 한 건마다 다음이 들어옵니다.

* 공고문
* 규격서
* 과업지시서
* 제안요청서
* 예외공표서 등 첨부문서
* 나라장터 메타데이터 21개 필드

그리고 모델이 **24개 검사항목 각각에 대해**

```text
위반인가? 0 / 1
+
위반이라면 어디가 근거인가?
```

를 반환해야 합니다. ([Dacon][1])

예를 들면 24개 항목 중 일부는:

* v1: 참가자격 특정기관 제한
* v2: 고시금액 미만 실적제한
* v3: 실적제한 1배수 이상
* v5: 고시금액 이상 지역제한
* v9: 과업지시서 특정 모델명 명시
* v13: 중기간 경쟁제품 소기업·소상공인 제한
* v19: 물품공급 확약서 입찰 시 제출
* v22: 현장설명회 참석업체 자격 제한
* v24: 공고서와 나라장터 입력값 상이

등입니다. ([Dacon][2])

즉 본질적으로는 **24개의 binary legal-compliance detector를 하나의 LLM 파이프라인 안에 구현하는 문제**라고 보면 됩니다.

---

# 2. 가장 중요한 특징: 모델을 학습시키는 대회가 아니다

평가 서버에는 이미 모델이 있습니다.

고정 LLM:

```text
google/gemma-4-26B-A4B-it
```

고정 임베딩 모델:

```text
BAAI/bge-m3
```

모든 참가자가 똑같은 모델을 사용합니다. ([Dacon][3])

그리고 다음은 금지입니다.

```text
Gemma Fine-tuning
LoRA
QLoRA
Adapter
별도 classifier
별도 regression model
다른 embedding model
학습된 model weight 제출
```

즉 이런 전략은 불가능합니다.

```text
20,000건 self-label
        ↓
BERT 학습
        ↓
classifier 제출
```

대신 이렇게 해야 합니다.

```text
Document
   ↓
전처리
   ↓
Rule / Candidate Detection
   ↓
RAG
   ↓
Prompt
   ↓
Gemma
   ↓
Structured Output
   ↓
Rule-based Correction
   ↓
Evidence Validation
```

규칙 기반 후처리는 명시적으로 허용되어 있습니다. ([Dacon][3])

더 중요한 규칙이 하나 있습니다.

> **평가 데이터의 모든 공고는 최소 한 번 이상 Gemma에 실제 공고 내용을 넣어 정상 호출해야 합니다.**

따라서 극단적으로 정규식만으로 전부 풀고 Gemma를 호출하지 않는 방법도 안 됩니다. ([Dacon][3])

---

# 3. 데이터는 어떻게 생겼나

배포 파일 구조가 꽤 잘 되어 있습니다.

```text
open.zip
├── README.md
├── train_unlabeled.jsonl.gz
├── dev.jsonl.gz
├── dev_labels.csv
├── sample_submission.csv
│
├── data/
│   ├── test.jsonl.gz
│   ├── 항목표.json
│   ├── 정답스키마_디코딩.json
│   └── 법령패키지/
│       ├── 법령/
│       └── 중기부고시/
│
└── baseline/
    ├── script.py
    └── requirements.txt
```

공식 데이터 명세 그대로입니다. ([Dacon][2])

### train_unlabeled

```text
20,000건
라벨 없음
```

그리고 중요한 사실:

> 정상 공고 20,000개가 아니라 **위반 공고도 섞여 있습니다.**

자가 라벨링, RAG 사례 구축, 규칙 개발용입니다. ([Dacon][4])

### dev

```text
dev.jsonl.gz          200건
dev_labels.csv        정답
```

24개 항목 모두에 대해 위반 사례가 들어 있고, 각 항목당 대략 5~8개의 positive 예제가 있습니다.

하지만 DACON이 아주 중요한 경고를 해놨습니다.

> **dev의 class distribution은 test와 다르다.**

따라서 dev에서 F1이 높다고 test에서도 그대로 높은 건 아닙니다. ([Dacon][2])

이게 실험 설계에서 굉장히 중요합니다.

---

# 4. 입력 JSON 한 건 구조

대략 이런 개념입니다.

```python
{
    "id": "...",

    "docs": [
        {
            "doc_id": "...",
            "type": "공고문",
            "text": "..."
        },
        {
            "doc_id": "...",
            "type": "과업지시서",
            "text": "..."
        }
    ],

    "meta": {...},

    "dropped_doc_counts": {...},

    "input_completeness": {...}
}
```

문서 유형은:

```text
공고문
규격서
과업지시서
제안요청서
예외공표서
```

5가지입니다. ([Dacon][2])

특히 **첨부문서를 반드시 봐야 합니다.**

공식 설명에서도 위반 내용이 첨부문서에만 존재할 수 있기 때문에 공고문만 보고 판단하면 안 된다고 명시되어 있습니다. ([Dacon][2])

---

# 5. meta도 굉장히 중요하다

메타데이터는 21필드입니다.

예를 들면:

```text
적용계약법
업무구분
계약방법
낙찰방법
낙찰하한율
배정예산금액
입찰추정가격
공동도급구성방식
정보화사업여부
세부품명번호목록
제한지역코드목록
지역제한여부
면허업종제한목록
업종제한여부
공고게시일자
개찰예정일자
긴급공고여부
입찰방법
조달방식
...
```

입니다. ([Dacon][2])

특히 **v24가 아주 특이합니다.**

```text
본문:
서울 지역 업체만 가능

meta:
지역제한여부 = false
```

처럼 본문과 나라장터 입력값이 다르면 위반입니다.

따라서 LLM에 document만 주는 것도 안 되고,

```text
docs + meta
```

를 같이 보게 만들어야 합니다.

---

# 6. 제출하는 것은 CSV가 아니다

이게 가장 헷갈릴 수 있는 부분입니다.

일반 DACON처럼

```text
submission.csv 업로드
```

가 아닙니다.

이번 대회에서 사용자가 직접 제출하는 것은:

```text
submit.zip
```

입니다. ([Dacon][5])

가장 기본적인 형태는:

```text
submit.zip
├── script.py
├── requirements.txt     # optional
└── model/               # optional
```

입니다.

여기서 `model/`은 이름 때문에 헷갈리지만 모델 weight를 넣는 곳이 아닙니다.

예를 들면:

```text
RAG index
BM25 index
keyword dictionary
rule config
self-labeled example database
```

등 **정적 자산**을 넣을 수 있습니다.

학습된 모델 weight는 금지입니다. ([Dacon][5])

---

# 7. 그러면 submission.csv는 누가 만드나?

당신의 `script.py`가 만듭니다.

평가 서버에서는 자동으로 이렇게 구성됩니다.

```text
submit.zip
│
├── script.py
├── requirements.txt
├── model/
│
├── data/
│   ├── test.jsonl.gz
│   ├── 항목표.json
│   ├── 정답스키마_디코딩.json
│   └── 법령패키지/
│
└── output/
```

그리고 당신의 코드가 반드시

```text
output/submission.csv
```

를 생성해야 합니다. ([Dacon][5])

실제 test는:

```text
1,853건
```

입니다.

---

# 8. 경로를 하드코딩하면 안 된다

평가 서버가 환경변수를 줍니다.

```python
PPS_DATA_DIR
PPS_OUTPUT_DIR
PPS_MODEL_DIR
PPS_EMBED_DIR
```

따라서 대략:

```python
import os

DATA_DIR = os.environ["PPS_DATA_DIR"]
OUTPUT_DIR = os.environ["PPS_OUTPUT_DIR"]
MODEL_DIR = os.environ["PPS_MODEL_DIR"]
EMBED_DIR = os.environ["PPS_EMBED_DIR"]
```

형태로 해야 합니다.

예를 들어

```python
"/home/user/data/test.jsonl.gz"
```

같은 식으로 쓰면 안 됩니다. ([Dacon][5])

---

# 9. 최종 submission.csv 형식

총 **49열**입니다.

```text
id

v1
v2
...
v24

e1
e2
...
e24
```

즉:

```text
1 + 24 + 24 = 49 columns
```

입니다. ([Dacon][4])

예를 들어 개념적으로:

```csv
id,v1,v2,...,v24,e1,e2,...,e24
PPS-001,0,1,...,0,,"실적이 2억원 이상인 업체로 제한한다",..., 
```

입니다.

---

# 10. v1~v24와 e1~e24의 의미

### v

```text
v1 ~ v24
```

는 반드시:

```text
0
1
```

이어야 합니다.

이런 건 안 됩니다.

```text
True
False
0.73
"1"
Y
N
```

판단 못했다고 빈칸도 안 됩니다. ([Dacon][4])

---

### e

```text
e1 ~ e24
```

는 evidence입니다.

여기가 꽤 까다롭습니다.

예를 들어 원문이:

```text
입찰 참가업체는 서울특별시에 본사를 둔 업체로 제한한다.
```

라면 evidence는 원문의 substring이어야 합니다.

가능:

```text
서울특별시에 본사를 둔 업체로 제한한다
```

불가능:

```text
서울 소재 업체만 입찰할 수 있도록 제한함
```

후자는 LLM이 만든 요약이라서 **무효**입니다.

공식 규칙상 evidence는:

* 원문 substring
* 수정 금지
* 요약 금지
* 최대 500자

입니다. ([Dacon][5])

그래서 저는 evidence를 **LLM에게 그대로 생성하게 하면 안 된다고 봅니다.**

LLM이

```json
{
  "evidence": "서울 소재 업체로 제한"
}
```

라고 만들게 한 다음,

Python이 실제 원문에서 substring을 다시 찾아서 뽑는 구조가 훨씬 안전합니다.

---

# 11. 5개 항목은 evidence가 없다

다음은 **부재탐지형**입니다.

```text
v10
v11
v16
v18
v20
```

예를 들어:

> 있어야 할 내용이 없음

자체가 위반이기 때문에 인용할 원문 자체가 없습니다.

그래서:

```text
e10
e11
e16
e18
e20
```

은 항상 blank입니다. ([Dacon][2])

---

# 12. 평가 방식

리더보드 점수는:

$$
Score =
\frac{1}{24}
\sum_{i=1}^{24}
F1_i
$$

입니다.

여기서 각 \(F1_i\)는 해당 항목의 **위반 클래스(1)에 대한 F1**입니다. ([Dacon][5])

즉 그냥 전체 44,472개 `(1853×24)` prediction에 대해 F1을 계산하는 게 아닙니다.

각 v가 똑같은 weight를 가집니다.

예를 들어:

```text
v1 F1 = 0.9
v2 F1 = 0.2
...
v24 F1 = 0.8
```

를 계산해서 평균냅니다.

### 이게 전략적으로 굉장히 중요합니다.

희귀한 항목이라고 무시하면 안 됩니다.

예를 들어 test에 v23 위반이 아주 적어도:

```text
v23 = 전체 점수의 1/24
```

입니다.

따라서 **24개 문제를 각각 별도의 classifier처럼 관리해야 합니다.**

---

# 13. evidence는 1차 리더보드에 안 들어간다

1차 리더보드는 오직:

```text
v1 ~ v24
```

만 봅니다.

`e1~e24`는 1차 점수와 무관합니다. ([Dacon][5])

하지만 상위 15팀에 들어가면 2차 평가가 있습니다.

최종 평가는:

```text
1차 정량평가     80%
근거문구 정성평가 20%
```

입니다.

따라서 상을 노린다면 처음부터 evidence를 제대로 만들어야 합니다.

---

# 14. Public / Private가 일반 DACON과 다르다

특이하게도 test 1,853건 **전부가 매번 리더보드 평가 대상**입니다.

```text
Public = test 100%
Private = 대회 종료 시점의 Public
```

입니다. ([Dacon][5])

즉 일반적인

```text
Public 30%
Private 70%
```

같은 hidden split이 없습니다.

이것 때문에 리더보드 피드백 자체는 강하지만, 반대편 위험도 큽니다.

**리더보드에 직접 과적합하기 아주 좋은 구조**입니다.

게다가 하루 제출은 단 1회라서 이를 막으려는 의도가 어느 정도 있다고 봅니다.

---

# 15. 제출 제한

현재 규칙은:

```text
1일 제출: 1회

submit.zip:
압축 2GB 이하
압축 해제 8GB 이하

requirements 설치:
10분

전체 inference:
2시간
```

입니다. ([Dacon][5])

서버:

```text
NVIDIA L40S × 1
VRAM 약 44.7 GiB

7 vCPU
RAM 60 GiB

Python 3.12.13
CUDA 13.0

vLLM 0.26.0
```

입니다.

인터넷은 inference 중 차단됩니다. ([Dacon][5])

---

# 16. 여기서 매우 중요한 계산비용 문제가 생긴다

test가:

```text
1,853 notices
```

인데,

각 notice마다 24개 항목을 따로 LLM 호출하면:

$$
1853\times24=44,472
$$

번입니다.

2시간 안에 사실상 굉장히 부담스럽습니다.

따라서 저는 **v1마다 LLM 호출하는 구조를 권하지 않습니다.**

초기 구조는:

```text
공고 1건
   ↓
관련 문서 + meta + 관련 법령
   ↓
Gemma 1회
   ↓
v1 ~ v24 한번에 생성
```

이 더 적절합니다.

필요하면 애매한 case만 second-pass를 거는 식으로 발전시키면 됩니다.

---

# 17. 내가 이 대회에 참가한다면 파이프라인은 이렇게 만든다

제가 보기에는 가장 유력한 architecture가 이겁니다.

```text
                     ┌───────────────┐
                     │   Notice      │
                     │ docs + meta   │
                     └───────┬───────┘
                             ↓
                    ┌────────────────┐
                    │ Normalization  │
                    └───────┬────────┘
                            ↓
                 ┌──────────────────────┐
                 │ Candidate Detection  │
                 │ Regex / Meta / Rule  │
                 └──────────┬───────────┘
                            ↓
                 ┌──────────────────────┐
                 │       RAG            │
                 │ law + examples       │
                 └──────────┬───────────┘
                            ↓
                 ┌──────────────────────┐
                 │ Gemma 4 26B          │
                 │ Structured Output    │
                 └──────────┬───────────┘
                            ↓
                 ┌──────────────────────┐
                 │ Rule Correction      │
                 └──────────┬───────────┘
                            ↓
                 ┌──────────────────────┐
                 │ Evidence Extraction  │
                 └──────────┬───────────┘
                            ↓
                      submission.csv
```

이 대회는 딱 이런 구조를 요구합니다.

---

# 18. RAG도 두 종류를 분리하는 게 좋다

저라면 RAG를 두 개로 나눕니다.

## Law RAG

공식 제공 법령 23건에서:

```text
관련 조항
판정 조건
예외조건
금액 조건
```

검색.

```text
query
→ bge-m3 / BM25
→ 관련 법령 chunk
```

공식에서도 Gemma + 법령 RAG baseline을 제공하고 있습니다. ([Dacon][6])

---

## Case RAG

훨씬 중요한 건 이것일 가능성이 높습니다.

```text
dev 200
+
self-labeled train examples
```

를 example DB로 구축합니다.

예:

```text
현재 공고
        ↓
similar notices retrieval
        ↓
v1 positive 사례
v1 negative 사례
v3 positive 사례
...
        ↓
few-shot prompt
```

즉:

> 법령만 알려주는 것보다 **실제 판정 사례를 Gemma에게 같이 보여주는 것**이 훨씬 강력할 가능성이 높습니다.

---

# 19. Self-labeling이 사실 이 대회의 핵심 장치다

train 20,000개에 label이 없습니다.

그런데 규칙이 굉장히 파격적입니다.

**자가 라벨 생성 단계에서는 외부 LLM도 허용됩니다.**

예:

```text
GPT
Claude
Gemini
```

같은 상용 API도 가능합니다.

단 반드시:

```text
대회가 제공한 자료만 입력
```

해야 합니다.

웹 검색이나 외부 법령 등을 결합하면 안 됩니다. ([Dacon][3])

이건 굉장히 큰 힌트라고 봅니다.

즉 운영 측도 사실상:

```text
20k unlabeled
        ↓
강한 external LLM
        ↓
pseudo labels
        ↓
RAG / rule / validation
```

같은 전략을 예상하고 있는 겁니다.

---

# 20. 그렇다고 20,000개를 전부 GPT로 라벨링할 필요는 없다

제가 한다면 처음부터 20k 전체를 안 합니다.

먼저 규칙으로 후보를 뽑습니다.

예를 들어 v9:

> 과업지시서 특정 모델명

이라면 다음 키워드 후보를 탐색합니다.

```text
모델
제품
제조사
규격
동등 이상
Samsung
LG
...
```

이런 candidate mining으로:

```text
20,000
   ↓
v9 의심 800
```

만 뽑습니다.

그리고 그 800개를 고품질 LLM으로 라벨링합니다.

각 항목별로:

```text
positive candidate
negative candidate
hard negative
```

를 확보하는 겁니다.

---

# 21. 실험 데이터는 이렇게 만들어야 한다

제가 추천하는 구조입니다.

### Gold

```text
dev 200
```

DACON 정답.

---

### Silver

외부 LLM + rule + human check:

```text
train_unlabeled
       ↓
candidate mining
       ↓
external LLM labeling
       ↓
high-confidence examples
```

예:

```text
silver_v1_positive.jsonl
silver_v1_negative.jsonl

silver_v2_positive.jsonl
silver_v2_negative.jsonl

...
```

---

### Hard set

특히 중요한 게 이겁니다.

모델이 틀리는 것만 모읍니다.

```text
hard_v1.jsonl
hard_v2.jsonl
...
```

그리고 모든 실험마다:

```text
dev macro-F1
+
per-label F1
+
hard-set accuracy
```

를 확인합니다.

---

# 22. 실험은 전체 Macro F1 하나만 보면 안 된다

예를 들어:

| label |   F1 |
| ----- | ---: |
| v1    | 0.92 |
| v2    | 0.87 |
| v3    | 0.43 |
| v4    | 0.71 |
| ...   |  ... |
| v24   | 0.51 |

처럼 관리해야 합니다.

그리고 각 실험마다:

```text
exp_001
macro 0.58

exp_002
macro 0.61
v3 +0.12
v7 -0.01
v24 +0.08
```

식으로 추적합니다.

왜냐하면 Macro-F1이므로 **낮은 label 하나를 크게 끌어올리는 것이 매우 효율적**이기 때문입니다.

---

# 23. 제가 추천하는 실험 루프

처음에는 이렇게 갑니다.

### EXP 000 — Official Baseline

```text
Gemma
+
전체 문서
+
24개 정의
```

아무것도 바꾸지 않습니다.

목적:

```text
submission pipeline 정상작동
runtime 측정
dev F1 측정
```

공식 baseline에는 모델 없이 I/O 흐름만 확인하는 `--mock`도 있습니다. ([Dacon][2])

---

### EXP 001 — Prompt 개선

각 항목에 대해:

```text
조건
예외
위반
정상
```

을 명시.

---

### EXP 002 — Law RAG

```text
항목표
+
관련 법령 top-k
```

추가.

---

### EXP 003 — dev Few-shot

각 v에 대해:

```text
positive example
negative example
```

추가.

---

### EXP 004 — Rule Engine

명확히 규칙화 가능한 것부터 구현.

특히:

```text
금액
날짜
지역
계약유형
meta 비교
```

는 LLM보다 deterministic rule이 더 강할 가능성이 큽니다.

---

### EXP 005 — Self-label RAG

20k에서 candidate를 뽑고 self-label:

```text
현재 notice
       ↓
유사 violation 사례 retrieval
       ↓
Gemma
```

---

### EXP 006 — Error-specific rules

dev false positive / false negative 분석.

예:

```text
v5 FP 18건

원인:
광역지역 표현을 지역제한으로 오판
```

이면:

```python
if ...:
    v5 = 0
```

같은 deterministic correction.

---

### EXP 007 — Evidence Engine

classification과 evidence를 분리합니다.

```text
Gemma:
위반 여부 판단
+
근거가 있는 문장 후보

Python:
실제 원문 substring 검색
+
exact extraction
```

---

# 24. 특히 저는 “24개 항목을 똑같이 LLM으로 풀지 않을 것” 같다

이게 꽤 중요한 전략입니다.

24개를 세 그룹으로 나눌 것 같습니다.

### A. Rule-dominant

예:

```text
금액 조건
날짜
계약법
지역
meta 불일치
```

```text
Rule 80%
LLM 20%
```

---

### B. Semantic

예:

```text
특정 모델명 명시
특정 기관 제한
특정 실적 제한
현장설명회 자격 제한
```

```text
LLM 70%
Rule 30%
```

---

### C. Absence detection

```text
v10
v11
v16
v18
v20
```

이건 완전히 별도 logic으로 관리합니다.

왜냐하면:

> 문서에 “없다”는 것을 찾는 문제

이기 때문입니다.

그리고 `dropped_doc_counts != {}`라면 일부 문서가 아예 데이터에 없을 수 있으므로 특히 조심해야 합니다. 공식 데이터 설명도 이를 경고합니다. ([Dacon][2])

---

# 25. 제가 프로젝트 구조도 이렇게 가져갈 것 같다

```text
competition/
│
├── data/
│
├── src/
│   ├── loader.py
│   ├── normalize.py
│   ├── document_router.py
│   ├── legal_rag.py
│   ├── example_rag.py
│   ├── rules/
│   │   ├── v01.py
│   │   ├── v02.py
│   │   ├── ...
│   │   └── v24.py
│   │
│   ├── prompt.py
│   ├── gemma.py
│   ├── evidence.py
│   └── postprocess.py
│
├── evaluation/
│   ├── metric.py
│   ├── error_analysis.py
│   └── reports.py
│
├── experiments/
│   ├── exp001.yaml
│   ├── exp002.yaml
│   └── ...
│
├── assets/
│   ├── rag_index/
│   ├── examples/
│   └── rules.json
│
└── submission/
    ├── script.py
    ├── requirements.txt
    └── model/
```

그리고 제출할 때 필요한 것만 복사해서:

```text
submit.zip
```

으로 만듭니다.

---

# 26. 실험 기록은 이렇게 남기는 걸 추천한다

이 대회는 하루 한 번만 리더보드 제출할 수 있어서 실험 관리가 특히 중요합니다.

예:

```text
exp_id: 014

base:
exp_012

change:
v3 실적배수 rule 추가
v5 region parser 개선

dev_macro_f1:
0.6812 → 0.6947

per_label:
v3 0.41 → 0.69
v5 0.72 → 0.76

runtime:
74 min

leaderboard:
0.6621

notes:
v3 FP 크게 감소
```

이렇게 해야 합니다.

Git commit도:

```text
exp014-v3-multiple-rule
```

처럼 맞춰놓는 게 좋습니다.

---

# 27. Leaderboard는 지금 어느 정도인가

제가 **2026년 8월 30일 현재** 리더보드도 확인했습니다.

현재:

```text
1위   0.73391
2위   0.70875
3위   0.70172

15위  0.64278
```

수준입니다. ([Dacon][7])

2차 진출이 **상위 15팀**이기 때문에 현재 기준으로 보면 대략:

```text
0.64+
```

가 2차 진출권이고,

```text
0.70+
```

부터 강한 상위권이라고 볼 수 있습니다.

물론 아직 대회 초반이라 이 cutoff는 앞으로 상당히 올라갈 가능성이 큽니다.

---

# 28. 리더보드 제출 전략도 일반 대회와 달라야 한다

하루 1회밖에 없습니다. ([Dacon][5])

따라서:

```text
코드 수정
↓
바로 submission
```

하면 안 됩니다.

최소한:

```text
DEV
↓
Regression Test
↓
Runtime Test
↓
Submission Validation
↓
submit.zip
```

순서를 강제하는 게 좋습니다.

특히 제출 실패도 종류가 나뉩니다.

**설치 오류**

```text
zip 구조
requirements 설치 실패
```

→ 제출 횟수 미차감

반면 **script 실행 후 오류**는:

```text
runtime error
timeout
submission.csv 문제
```

→ 제출 횟수 차감

입니다. ([Dacon][5])

그래서 로컬 validation script를 반드시 만드는 게 좋습니다.

---

# 29. submission validator는 초기에 바로 만들어야 한다

예를 들어 자동으로:

```python
assert len(df) == len(test)

assert df.columns.tolist() == EXPECTED_COLUMNS

assert df["id"].is_unique

for c in [f"v{i}" for i in range(1, 25)]:
    assert set(df[c].unique()) <= {0, 1}

assert df["id"].notna().all()
```

그리고:

```text
UTF-8 no BOM
NFC normalization
evidence <= 500 chars
evidence ∈ original document
```

까지 검증합니다.

이런 실수 때문에 하루짜리 submission을 날리는 건 너무 아깝습니다.

---

# 30. 또 하나 중요한 점: 모델 output은 JSON constrained decoding을 써라

공식에서도:

```text
정답스키마_디코딩.json
```

을 제공합니다.

그리고 vLLM structured output 사용을 권합니다. ([Dacon][5])

따라서:

```text
LLM에게 JSON 출력하라고 부탁
```

하는 수준이 아니라,

실제로:

```text
JSON schema constrained decoding
```

을 걸어야 합니다.

그러면:

```text
JSON parse failure
열 누락
v17 빠짐
```

같은 문제가 거의 사라집니다.

---

# 31. 이 대회에서 제가 가장 중요하다고 보는 연구 포인트

순위를 매기면 저는 이렇게 봅니다.

**1순위 — 항목별 Rule + LLM hybrid**

24개를 하나의 “법률 판단” 문제로 다루면 안 됩니다.

---

**2순위 — Self-labeling**

20,000 unlabeled를 그냥 방치하면 엄청난 데이터 낭비입니다.

---

**3순위 — Case RAG**

법령 RAG보다도 **실제 positive/negative 판정 사례 RAG**가 굉장히 강할 가능성이 있다고 봅니다.

---

**4순위 — Prompt routing**

24개의 법률 조건을 매번 전부 길게 넣는 대신:

```text
notice feature
↓
relevant law/rule
↓
compact prompt
```

로 만드는 게 성능뿐 아니라 2시간 제한 대응에도 중요합니다.

---

**5순위 — deterministic evidence**

Evidence 생성 자체를 LLM에게 맡기지 않고 원문에서 exact substring으로 확정.

---

# 32. 일정

현재 기준 중요한 날짜는:

```text
2026-09-23 23:59
팀 병합 마감

2026-09-29 10:00
리더보드 제출 마감

2026-09-30 10:00
대회 종료

2026-10-05 10:00
2차 평가 자료 제출 마감

2026-10-16 10:00
최종 결과
```

입니다. ([Dacon][8])

특히 **리더보드 제출 마감은 대회 종료 하루 전인 9월 29일 10시**입니다.

이 날짜를 9월 30일로 착각하면 안 됩니다.

---

# 33. 수상까지 생각한다면 반드시 재현성을 관리해야 한다

상위 15팀은 2차에서 코드 재현 검증을 받습니다.

자가 라벨링도 대상입니다.

외부 LLM을 썼다면 최소한:

```text
model
prompt
input
output label
generation code
```

를 남겨야 합니다. ([Dacon][2])

따라서:

```text
ChatGPT 웹 UI에 넣어서 300개 라벨 만들고
어떻게 만들었는지 기록 안 함
```

은 수상권에서는 상당히 위험합니다.

---

# 34. 추가로 알아둘 규정 하나

수상작의 경우 동의사항에 꽤 강한 조항이 있습니다.

대회 수상 산출물에 대한 저작권 및 2차적 저작물 작성권이 **주최 측에 독점적으로 귀속**된다는 내용이 명시돼 있습니다. ([Dacon][9])

실제 수상권까지 간다면 해당 조항은 한 번 자세히 읽어두는 게 좋겠습니다.

---

# 35. 그래서 지금 당장 시작한다면

제가 참가자라면 첫 작업 순서는 딱 이렇습니다.

1. `open.zip` 다운로드
2. official `baseline/script.py` 실행
3. `--mock`으로 I/O 및 submission 생성 확인
4. `dev.jsonl.gz` + `dev_labels.csv` 로컬 평가기 구현
5. 24개 항목별 precision / recall / F1 출력
6. official Gemma baseline의 dev 결과 확보
7. 오답 200건 전부 분석
8. 항목별 `rule / semantic / absence` 분류
9. Law RAG 추가
10. dev few-shot 추가
11. train 20k candidate mining
12. 외부 LLM self-labeling
13. Case RAG 구축
14. rule-based correction 추가
15. evidence exact substring validator 구현
16. runtime 2시간 이하 확인
17. `submit.zip` 생성
18. 하루 1회 리더보드 제출

입니다.

그리고 **첫 번째 목표는 0.70을 노리는 게 아니라 `baseline → dev evaluation → error analysis` 인프라를 만드는 것**으로 잡는 게 맞습니다.

이 인프라가 만들어지고 나면 이 대회는 꽤 전형적인:

> **24개 법률 규칙을 하나씩 부수면서 Macro-F1을 올리는 error-driven engineering 문제**

가 됩니다.

현재 리더보드가 계속 움직이고 있으니 원하면 순위와 상위 15팀 컷을 정기적으로 확인할 수도 있습니다.

[1]: https://dacon.io/competitions/official/236754/overview/description "나라장터 자체입찰 공고 법령 위반사항 모니터링 AI 경진대회 - DACON"
[2]: https://dacon.io/competitions/official/236754/talkboard/417195?dtype=recent&page=1 "데이터 명세 - DACON"
[3]: https://dacon.io/competitions/official/236754/overview/rules "나라장터 자체입찰 공고 법령 위반사항 모니터링 AI 경진대회 - DACON"
[4]: https://dacon.io/competitions/official/236754/data "나라장터 자체입찰 공고 법령 위반사항 모니터링 AI 경진대회 - DACON"
[5]: https://dacon.io/competitions/official/236754/overview/evaluation "나라장터 자체입찰 공고 법령 위반사항 모니터링 AI 경진대회 - DACON"
[6]: https://dacon.io/competitions/official/236754/codeshare "나라장터 자체입찰 공고 법령 위반사항 모니터링 AI 경진대회 - DACON"
[7]: https://dacon.io/competitions/official/236754/leaderboard "나라장터 자체입찰 공고 법령 위반사항 모니터링 AI 경진대회 - DACON"
[8]: https://dacon.io/competitions/official/236754/overview/schedule?utm_source=chatgpt.com "나라장터 자체입찰 공고 법령 위반사항 모니터링 AI 경진대회 - DACON"
[9]: https://dacon.io/competitions/official/236754/overview/agreement "나라장터 자체입찰 공고 법령 위반사항 모니터링 AI 경진대회 - DACON"
