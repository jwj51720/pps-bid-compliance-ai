네. **정답이 포함된 로컬 검증용 데이터가 제공됩니다.** 다만 “학습용 정답 데이터셋”을 제공하는 건 아니고, **검증용 `dev` 200건**을 따로 제공합니다. ([Dacon][1])

구성은 이렇습니다.

```text
dev.jsonl.gz        # 공고 200건
dev_labels.csv      # 위 200건의 정답
```

`dev_labels.csv`는 실제 제출 형식과 똑같은 **49열**입니다.

```text
id
v1 ~ v24       # 위반 여부 0/1
e1 ~ e24       # 근거 문구
```

그리고 24개 모든 검사항목에 대해 **각 항목당 5~8건 정도의 위반 예시**가 포함되어 있습니다. 정상 예시도 112건 들어 있습니다. ([Dacon][1])

그래서 우리가 아까 설계한 로컬 실험 루프를 그대로 적용하면 됩니다.

```text
dev.jsonl.gz
      ↓
우리 pipeline
      ↓
submission.csv
      ↓
dev_labels.csv와 비교
      ↓
v1 F1
v2 F1
...
v24 F1
      ↓
Macro F1
```

즉 실제 대회 채점 방식처럼

$$
Score = \frac{1}{24}\sum_{i=1}^{24}F1_i
$$

를 로컬에서 계산하면 됩니다.

다만 **주의할 점이 하나 매우 중요합니다.**

DACON이 명시적으로:

> dev는 판정 유형을 보여주기 위한 예시 세트이고, **실제 test의 항목별 구성비와는 다르다**

고 해두었습니다. ([Dacon][1])

따라서 이 200개에 계속 prompt/rule을 맞추면 **dev overfitting**이 생길 가능성이 큽니다.

그래서 저는 처음에는 이렇게 가는 게 좋다고 봅니다.

```text
Phase 1

dev 200건
   ↓
baseline 성능 측정
   ↓
오답 분석
   ↓
pipeline 개발
```

그리고 어느 정도 올라가면 `train_unlabeled 20,000건`에서 우리가 직접 validation set을 만들어야 합니다.

```text
train_unlabeled 20,000
        ↓
OpenAI 등으로 self-labeling
        ↓
신뢰도 높은 일부 추출
        ↓
silver validation set
```

그러면 나중에는:

```text
공식 dev 200        → Gold validation
자가라벨 validation → Silver validation
Public leaderboard  → 실제 test feedback
```

3개를 같이 볼 수 있습니다.

그리고 아까 말씀하신 **“40개 정도 공개된 정답”은 실제로는 40개가 아니라 200개**입니다. 현재 공식 데이터 페이지 기준으로 `dev.jsonl.gz + dev_labels.csv`가 **200건** 제공됩니다. ([Dacon][1])

따라서 첫 구현 목표는 정말 명확하게 잡을 수 있습니다.

```bash
python scripts/run_experiment.py
```

한 번 실행하면:

```text
dev 200건 추론
→ outputs/baseline/submission.csv 생성
→ dev_labels.csv 비교
→ Macro F1 + v1~v24 F1 출력
```

여기까지를 **첫 번째 milestone**으로 잡는 게 가장 좋습니다.

[1]: https://dacon.io/competitions/official/236754/data "나라장터 자체입찰 공고 법령 위반사항 모니터링 AI 경진대회 - DACON"


맞습니다. 이 대회에서 `e`는 **1차 점수에는 안 들어가지만, 오히려 로컬에서는 `v`의 품질을 검증하는 보조 신호로 적극 활용할 가치가 큽니다.**

공식 기준을 다시 보면 2차 평가는 정답이 `v=1`인 항목의 `e`만 평가하며, **① 반드시 해당 공고의 공고문/첨부문서 원문 substring이어야 하고, ② 정답 근거와 얼마나 일치하는지를 보며, ③ 위반에 해당하는 부분만 짧게 인용하는 게 유리**합니다. 요약·수정·LLM이 새로 만든 문구는 자동 무효이고, 메타데이터 값은 substring 대조 대상도 아닙니다. 부재탐지형 `v10, v11, v16, v18, v20`은 evidence 평가에서 제외됩니다. ([Dacon][1])

그래서 저는 **`v-score`와 `e-score`를 분리해서 관리하되, `e`를 v의 신뢰도 검증에도 쓰는 구조**를 추천합니다.

## 1. 우선 `e`의 가장 기본적인 평가: Validity

이건 2차 평가 전에 무조건 통과해야 하는 hard constraint입니다.

예측 evidence가:

```text
pred_e
```

라면 해당 공고의 모든 제공 문서를 합쳐서,

```python
pred_e in document_text
```

가 반드시 참이어야 합니다.

로컬에서는 다음 지표를 계산할 수 있습니다.

$$
EvidenceValidity
=
\frac{
\#\{\text{predicted evidence that is exact substring}\}
}{
\#\{\text{predicted positive evidence}\}
}
$$

목표는 사실상:

```text
100%
```

이어야 합니다.

이건 성능 지표라기보다 **submission validation**에 가깝습니다.

---

# 2. 그다음 핵심: Gold Evidence와 얼마나 겹치는가

예를 들어 정답이:

```text
서울특별시에 주된 영업소를 둔 업체로 제한합니다
```

인데 모델이:

```text
입찰참가자격은 서울특별시에 주된 영업소를 둔 업체로 제한합니다.
본 사업의 자세한 내용은 별첨 과업지시서를 참조하시기 바랍니다.
```

를 evidence로 가져왔다고 합시다.

둘 다 원문 substring이기 때문에 **유효하기는 합니다.**

하지만 공식 평가 기준상:

> 위반에 해당하는 부분만 인용하는 것이 유리

하므로 후자가 더 나쁩니다. ([Dacon][1])

그래서 저는 `e`의 로컬 점수를 **문자 단위 Precision / Recall / F1**로 잡는 게 상당히 합리적이라고 봅니다.

정답 evidence 문자 집합/구간을 \(G\), 예측을 \(P\)라고 하면 개념적으로:

$$
Precision_e
=
\frac{|P \cap G|}{|P|}
$$

$$
Recall_e
=
\frac{|P \cap G|}{|G|}
$$

$$
F1_e
=
\frac{2P_eR_e}{P_e+R_e}
$$

라고 보는 겁니다.

예를 들어:

### 너무 긴 evidence

```text
Gold:
서울특별시에 주된 영업소를 둔 업체

Pred:
입찰참가자격은 서울특별시에 주된 영업소를 둔 업체로 제한하며 ...
```

Gold는 거의 다 포함하므로:

```text
Recall ↑
Precision ↓
```

### 너무 짧은 evidence

```text
Gold:
서울특별시에 주된 영업소를 둔 업체

Pred:
서울특별시
```

이면:

```text
Precision ↑
Recall ↓
```

둘 다 F1에서 패널티를 받습니다.

이게 공식 설명의 **“정답 근거와 일치하면서 필요한 부분만 인용”**이라는 기준과 상당히 잘 맞습니다. ([Dacon][1])

---

# 3. 그런데 단순 문자 집합으로 하면 안 되고 "구간 overlap"으로 보는 게 좋다

문자 집합이라고 표현했지만 실제 구현은 문서상의 **span 위치**로 평가하는 게 더 정확합니다.

예를 들어 원문에서:

```text
[120:152] = gold evidence
[115:160] = predicted evidence
```

라면:

```python
intersection = max(
    0,
    min(gold_end, pred_end)
    - max(gold_start, pred_start)
)
```

로 overlap을 구합니다.

그리고:

$$
P_e = \frac{intersection}{pred\_length}
$$

$$
R_e = \frac{intersection}{gold\_length}
$$

이렇게 계산합니다.

이걸 저는 `Evidence Span F1`이라고 부르겠습니다.

---

# 4. Exact Match도 같이 기록하자

단순하지만 유용합니다.

```python
pred_e == gold_e
```

이면 1.

따라서 실험 결과에는:

```text
Evidence Validity
Evidence Exact Match
Evidence Span Precision
Evidence Span Recall
Evidence Span F1
```

를 같이 기록합니다.

여기서 **주 지표는 Span F1**, 나머지는 진단 지표로 보면 좋겠습니다.

---

# 5. 더 중요한 활용: `e`를 이용해 `v`의 false positive를 줄일 수 있다

이게 오히려 대회 성능 측면에서는 가장 중요할 수 있습니다.

LLM이:

```json
{
  "v7": 1,
  "e7": "..."
}
```

이라고 했다고 합시다.

그런데 `e7`을 실제 원문에서 찾아보니:

```text
원문에 존재하지 않음
```

그러면 두 가지 가능성이 큽니다.

1. hallucination
2. 위반 판단 자체가 잘못됨

따라서 evidence를 **판정 검증용 self-consistency signal**로 사용할 수 있습니다.

개념적으로:

```text
LLM:
v = 1

        ↓

evidence 있음?
        ↓

원문 exact substring인가?
        ↓

그 substring이 정말 해당 violation을 뒷받침하는가?
```

를 확인합니다.

---

# 6. 그래서 저는 `Evidence-gated Prediction`도 실험해볼 만하다고 봅니다

예를 들어 semantic violation 항목에서는:

```python
if pred_v == 1:
    if not valid_evidence:
        # 바로 0으로 바꾸기보다는
        # second-pass를 한번 더 요청
```

처럼 합니다.

즉:

```text
1차 Gemma
 ↓
v=1
 ↓
evidence validation 실패
 ↓
Gemma verification prompt
 ↓
최종 v
```

이런 식입니다.

단순히 evidence가 없으면 무조건 `v=0`으로 바꾸는 것은 위험합니다.

LLM이 **판정은 맞았는데 evidence extraction만 실패**했을 수도 있으니까요.

따라서 dev에서 실제로:

```text
evidence invalid인 positive 중
진짜 FP가 얼마나 되는가?
```

를 측정해보고 결정하면 됩니다.

이게 상당히 좋은 실험 포인트입니다.

---

# 7. 반대로 정답 `v=1`인데 e가 틀렸다면 오답 유형을 둘로 나눌 수 있다

지금까지 `v`만 평가하면:

```text
v = 정답
```

이면 성공입니다.

하지만 evidence까지 보면 사실 두 종류로 나뉩니다.

### 완전 성공

```text
v correct
e correct
```

### 판정은 맞았지만 reasoning이 불안정

```text
v correct
e wrong
```

두 번째 케이스는 매우 중요합니다.

왜냐하면 모델이 실제로 법령을 이해해서 맞춘 게 아니라:

```text
키워드 우연히 발견
추측
잘못된 문장을 근거로 결론
```

했을 가능성이 있기 때문입니다.

이런 경우는 dev에서는 맞았어도 test에서 일반화가 깨질 가능성이 있습니다.

---

# 8. 그래서 로컬 평가를 3단계로 만드는 게 좋겠습니다

## Level 1 — Leaderboard Metric

공식 1차와 완전히 동일합니다.

$$
VScore =
MacroF1(v_1,\ldots,v_{24})
$$

이게 **대회 최우선 지표**입니다.

---

## Level 2 — Evidence Quality

부재탐지형 5개를 제외한 positive 정답에 대해서:

$$
EScore =
Mean(EvidenceSpanF1)
$$

단, predicted evidence가 원문 substring이 아니면:

$$
EScore_i = 0
$$

로 줍니다.

이렇게 하면 공식 2차 방식과 어느 정도 방향이 맞습니다.

---

## Level 3 — Joint Quality

우리만의 diagnostic metric으로:

```text
v도 맞고
e도 제대로 찾은 경우
```

를 평가합니다.

예를 들어:

$$
Joint_i
=
\mathbb{1}(v_i=\hat v_i=1)
\times
EvidenceF1_i
$$

이걸 평균냅니다.

이건 공식 점수가 아닙니다.

하지만 **실제로 reasoning까지 제대로 된 positive detection**을 측정할 수 있습니다.

---

# 9. 저는 전체 점수를 억지로 하나로 합치지는 않는 게 좋다고 봅니다

공식 최종 평가는:

```text
1차 정량 80%
근거문구 정성 20%
```

입니다. ([Dacon][1])

그래서 우리도:

$$
LocalScore
=
0.8VScore+0.2EScore
$$

라고 만들고 싶어질 수 있습니다.

그런데 저는 **이걸 메인 지표로 쓰지는 않을 것 같습니다.**

왜냐하면 공식 `20%`의 evidence 평가는 사람이 하는 **정성평가**이고, 우리가 만든 `Span F1`과 정확히 같은 평가가 아니기 때문입니다.

대신 결과판을 이렇게 가져가는 게 낫습니다.

```text
EXP-012

V Macro F1          0.6841   ← 가장 중요

Evidence
  Validity          100.0%
  Exact Match        61.3%
  Span Precision     88.2%
  Span Recall        91.5%
  Span F1            89.3%

Joint Positive F1    0.612
```

이렇게 **별도로 봅니다.**

---

# 10. 특히 `Evidence Precision`을 중요하게 보는 게 좋다

공식 설명에 굉장히 중요한 문장이 있습니다.

> “위반에 해당하는 부분만 인용하는 것이 유리합니다.” ([Dacon][1])

즉 정답 문장을 포함한다고 무조건 좋은 게 아닙니다.

예를 들어 모델이 매번 공고문 전체 500자를 evidence로 넣어버리면:

```text
Recall = 높음
Precision = 낮음
```

이 됩니다.

그래서 개인적으로는 `Evidence Span F1`과 함께:

```text
Span Precision
```

을 눈여겨보겠습니다.

---

# 11. `v=0`의 e도 validation에 활용할 수 있다

공식상 위반이 아니거나 근거가 없는 경우 `e`는 빈칸으로 둘 수 있습니다. ([Dacon][1])

그래서 우리는 다음 consistency check도 할 수 있습니다.

```text
v = 0
e = non-empty
```

라면 이상합니다.

반대로:

```text
v = 1
e = empty
```

도 부재탐지형 5개가 아니라면 의심스럽습니다.

따라서 submission validator에:

```python
ABSENCE_TYPES = {10, 11, 16, 18, 20}

if v == 0:
    assert e == ""

if v == 1 and i not in ABSENCE_TYPES:
    warn_if(e == "")
```

같은 검증을 두면 좋습니다.

두 번째는 `assert`까지 걸지는 않고 warning 정도가 적당합니다.

---

# 12. v24는 별도로 조심해야 한다

공식 설명상 evidence 자동 검증 대상은 **공고문·첨부문서의 본문 텍스트**이고, `meta` 값 자체는 evidence substring의 대조 대상이 아닙니다. ([Dacon][1])

그런데 v24처럼:

```text
공고 본문
vs
나라장터 metadata
```

불일치를 판정하는 항목은 결국 두 정보를 비교해야 합니다.

예:

```text
본문:
서울특별시 업체로 제한

meta:
지역제한여부 = false
```

이라면 reasoning에는 둘 다 필요하지만, `e24`로 제출하는 것은:

```text
서울특별시 업체로 제한
```

같은 **본문 부분만** 넣는 게 맞습니다.

따라서 내부적으로는:

```text
reasoning evidence
```

와

```text
submission evidence
```

를 개념적으로 구분하는 것도 좋습니다.

---

# 13. 그래서 prediction 내부 representation을 조금 다르게 하는 것도 좋다

바로:

```json
{
  "v1": 1,
  "e1": "..."
}
```

만 들고 다니기보다는 내부적으로:

```json
{
  "v1": {
    "violation": 1,
    "evidence": "...",
    "reason": "...",
    "confidence": 0.91
  }
}
```

정도를 가지고 있을 수 있습니다.

그리고 최종 `submission.py`에서만:

```text
v1 = violation
e1 = evidence
```

로 떨어뜨리는 겁니다.

`reason`은 제출에는 안 쓰지만:

* dev error analysis
* evidence mismatch 분석
* prompt 개선

에 굉장히 유용합니다.

다만 이것도 처음부터 너무 복잡하게 구조화할 필요는 없습니다.

---

# 14. 최종적으로 제가 추천하는 로컬 evidence 평가 기준

정리하면 이렇게 가겠습니다.

| 지표                    | 의미                    |   중요도 |
| --------------------- | --------------------- | ----: |
| **V Macro F1**        | 공식 1차 점수              | ★★★★★ |
| **Evidence Validity** | 실제 원문 substring인가     | ★★★★★ |
| **Evidence Span F1**  | Gold 근거 구간과 얼마나 일치하는가 | ★★★★☆ |
| Evidence Precision    | 불필요하게 길지 않은가          | ★★★★☆ |
| Evidence Recall       | 핵심 근거를 빠뜨리지 않았는가      | ★★★☆☆ |
| Exact Match           | Gold와 정확히 같은가         | ★★☆☆☆ |
| Joint Quality         | v와 e를 동시에 맞혔는가        | ★★★★☆ |

그리고 결과를 예를 들어:

```text
=====================================
EXP: baseline-001
=====================================

[Leaderboard]
V Macro F1              0.6214

[Evidence]
Validity                 98.7%
Span Precision           86.1%
Span Recall              91.7%
Span F1                  88.8%
Exact Match              54.3%

[Joint]
Correct V + Good E       0.5571
=====================================
```

정도로 출력하게 만들겠습니다.

**핵심은 `e`를 2차 평가 준비용으로만 보지 않는 것입니다.**

`v=1`이라고 판단하면서 **실제 원문에서 그 판단을 뒷받침하는 정확한 구간을 못 찾는 모델은 상당히 의심스럽다**는 점을 이용하면 됩니다. 그래서 `e`는 dev에서 일종의 **reasoning correctness / hallucination detector** 역할을 할 수 있습니다.

그리고 이 관점이라면 `evaluate.py`를 처음 만들 때부터 `v metric`과 `e metric`을 같이 넣는 게 좋겠습니다. 나중에 붙이는 것보다 지금 평가 인터페이스만 그렇게 잡아두는 게 깔끔합니다.

[1]: https://dacon.io/competitions/official/236754/overview/evaluation "나라장터 자체입찰 공고 법령 위반사항 모니터링 AI 경진대회 - DACON"
