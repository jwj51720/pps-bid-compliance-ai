# Source-first 이후 아키텍처 탐색 매트릭스 v1

작성일: 2026-09-10 (dev / mac)

## 목적

이 문서는 credit 복구 뒤의 다음 유료 실험을 결정하기 위한 **사전 설계 문서**다. 작은
문구 수정·카드 수정·dev 오답별 규칙 추가를 반복하지 않는다. 각 후보는 현재 공고의
원문 사실을 빠뜨리지 않으면서 Gemma가 24개 법률 판단을 수행하기 쉽게 만드는가만
검증한다.

공통 고정 조건은 다음과 같다.

- 원문 법령 RAG, 20,000건 사례 RAG, dev label 기반 Python 보정은 넣지 않는다.
- decision card v6, human-readable metadata, exact organizer product fact, EXP123의
  동결 v2/v3/v21 후처리는 변경하지 않는다.
- final V/E 판단과 evidence 확정은 Gemma가 실제 공고 원문을 읽고 한다. navigation의
  null/후보없음은 Python 또는 final label의 0이 아니다.
- final 단계는 exact-token 32k admission으로 **모든 supplied notice source**를 받는다.
  4,000자 final anchor는 이 branch에서 사용하지 않는다.

## 이미 얻은 구조적 증거

| 후보 | final 원문 범위 | stage-1 역할 | 결과 | 판정 |
| --- | --- | --- | --- | --- |
| EXP152/154 one-stage | complete source | 없음 | 32k fast20 0.241667 | 기준선 |
| EXP155/156 item group final | complete source를 group마다 반복 | 그룹별 최종 V/E | 0.237500 / 0.213889 | 종료 |
| EXP150 triage | 4k | route가 final item을 좁힘 | 0.277020 vs control 0.291071 | 종료: positive coverage 부족 |
| EXP151 strict locator | 4k | 항목별 exact snippet | 0.248016 | 종료: 32/380 중 14개만 non-empty |
| EXP153 inventory → final | complete source → 4k | 24개 항목별 한 구절/null | 0.280556 vs 4k control 0.291071 | 종료: final source 축소 + coverage 6/38 |
| EXP167/168/171 source-first v1 | complete source | 7개 사실 범주 × 최대 3구절 | fast +.023611, holdout +.018056, dev200 0.307962 | complete-source incumbent |
| EXP172 matched one-stage | complete source | 없음 | dev200 0.259281 | source-first v1보다 -0.048681 |
| EXP174 source-first v2 | complete source | 범주당 4구절 | fast 0.269444 | 종료 |
| EXP175 source-first v3 | complete source | 같은 navigation을 source 앞에 배치 | fast 0.263889 | 종료 |
| EXP176/177 source-first v4 | complete source | 예외 범주 1개 추가 | fast 0.287500, holdout 0.166667 | 종료: holdout 반대 방향 |

핵심 결론은 두 가지다.

1. 전문을 final에서 빼면 안 된다. EXP153의 항목별 inventory가 나쁜 결과를 낸 원인을
   항목별 탐색 자체로 단정할 수 없다.
2. source-first v1의 이득은 navigation 자체에서 왔을 가능성이 높지만, 더 많이 뽑기,
   앞에 놓기, 범주를 하나 더 늘리기로는 재현되지 않았다.

## 다음 후보: item-aware navigation + complete-source final

### 가설

현재 v1 범주는 원문을 넓게 보여 주지만, 한 범주 안의 서로 다른 v의 사실을 같은 세
구절 슬롯이 경쟁한다. 예를 들어 자격·지역·실적·금액 사실이 동시에 있는 문서 pack에서
필요한 사실 하나가 navigation에서 빠질 수 있다. 이를 **항목별 source fact navigation**으로
바꾸면 final Gemma가 자기 카드와 관련된 후보를 더 쉽게 찾을 수 있다.

이는 EXP153의 재실행이 아니다. 달라지는 점은 최종 판정이 4,000자 anchor가 아니라 모든
tokenizer-admitted source pack을 다시 읽는다는 것이다. candidate가 null이어도 final은 원문과
metadata/card를 독립적으로 전부 판단한다.

### 아직 유료로 실행하지 않는 이유

EXP153은 24개 항목별로 문서 묶음당 한 구절만 요구했을 때 gold evidence 38개 중 6개만
navigation과 겹쳤다. 이 결과만으로 item-aware full-final이 실패한다고 결론낼 수는 없지만,
출력 부담이 너무 큰지 먼저 label-blind하게 확인해야 한다.

### 오프라인 admission/coverage 진단

다음 검사를 먼저 수행한다. 이 검사는 dev labels/predictions을 읽지 않는다.

1. 24개 item의 card에서 요구하는 사실 유형과 required document type을 추출한다.
2. v1의 7개 범주가 각 item에 필요한 사실 유형을 실제로 표현할 수 있는지 matrix로 표시한다.
3. item-aware schema의 최악 JSON 크기, exact tokenizer admission, stage/final pack 수,
   1,853건 runtime 상한을 계산한다.
4. short complete / attachment / overflow record 각각에서 exact Stage-1 및 final messages를
   export한다. Stage-1은 raw source만, final은 cards/meta/product facts/full source/navigation을
   모두 포함하는지 사람이 읽어 확인한다.
5. mock에서 candidate null, malformed stage-1, duplicated candidate, absence item, final parse
   recovery, unchanged evidence validation을 검증한다.

### 오프라인 profile 결과 (2026-09-10)

`scripts/profile_source_first_full_final.py`를 exact Gemma chat-template tokenizer로 실행했다.
이 결과는 API/label을 사용하지 않으며, 현재 **범주형** navigation이 final admission에 만드는
여유만 측정한다. 산출물은 다음 ignored 경로에 남겼다.

- `outputs/exp178-item-aware-full-final-offline/source_first_v1_fast_profile.json`
- `outputs/exp178-item-aware-full-final-offline/source_first_v1_dev200_profile.json`

| dev-200 scenario | stage-1 calls | final calls | 합계 | final source omission |
| --- | ---: | ---: | ---: | ---: |
| 빈 navigation | 216 | 216 | 432 | 0 |
| 실제 EXP167 fast20 navigation (20건만) | 23 | 24 | 47 | 0 |
| 범주당 160자 1개 synthetic | 216 | 218 | 434 | 0 |
| 현재 schema 상한: 범주당 360자 3개 | 216 | 232 | 448 | 0 |

즉 현재 v1 범주형 schema는 navigation이 최대로 차도 dev-200에서 16회의 final pack만
추가한다. 반대로 이 수치는 **24-item schema의 안전성 증거가 아니다**. item-aware 후보는
실제 schema가 만들어진 뒤 동일 profile을 새로 통과해야 한다. 그 schema가 32k admission을
무너뜨리거나 final call 수를 의미 있게 늘리면, paid run 없이 종료한다.

이 검사가 통과하더라도 item별 v 하나씩 24회를 호출하지 않는다. 기본은 **한 stage-1
호출에서 24 item을 함께 반환**하는 최소 topology다. 이 방식의 schema 부담이 admission 또는
mock 안정성을 해치면 유료 실행 대신 이 후보를 종료한다. item group을 여러 호출로 나누는
확장은 source-first v1보다 call 수가 크게 늘어나므로, fast20에서 quality 이득이 확인되기
전에는 설계하지 않는다.

### 유료 fast20 gate

오프라인 검증을 통과할 때만 20건의 versioned fast panel에서 one-variable probe를 실행한다.

- base config: EXP167.
- allowed change: `staged_run.mode` 하나.
- stage-1은 item별 raw source candidate 또는 null만 낸다. label/판정/evidence 확정은 금지한다.
- final은 EXP167과 같은 full source + V/E output을 유지한다.
- success: parser/CSV 20/20, source omission 0, final recovery 0, evidence warning 악화 없음,
  fast F1이 EXP167보다 높을 때만 independent holdout으로 진행한다.
- fast F1이 낮거나 stage-1 coverage/형식이 나쁘면 항목별 prompt tuning 없이 branch를 종료한다.

## 이번 단계에서 명시적으로 하지 않는 것

- navigation candidate 수를 5개 이상으로 다시 늘리기
- navigation section의 앞/뒤 위치 재변경
- taxonomy 이름을 더 늘리기
- v별 hard-code, dev 오류 예외, Python label override
- full split × item grouping, raw-law RAG, final 4k 축소

위 항목은 이미 같은 원인에 대한 반복이거나 source coverage/runtime contract를 악화시킨다.

## 실행 순서

1. 이 문서의 label-blind architecture audit을 구현/실행하고 결과를 여기에 추가한다.
2. 코드/config가 필요한 경우 mock·preflight·semantic contract·exact rendered input review를
   마친다.
3. 그때만 fast20 paid run을 실행하고, 완료까지 process를 감시한다.
4. fast20이 통과하면 policy-identical independent holdout, 그 뒤에만 dev200으로 확대한다.
