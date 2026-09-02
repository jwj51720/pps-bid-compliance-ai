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
