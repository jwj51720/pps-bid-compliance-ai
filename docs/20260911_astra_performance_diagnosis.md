# Astra 분석: 0.2x 정체의 원인과 0.3·0.5·0.7을 향한 실험 순서

작성: 2026-09-11, dev / mac. 이 문서는 연구 진단과 제안이며 canonical 정책 변경이나 제출 승인이 아니다.

## 판단

**Gemma의 한계만으로 설명하기 전에, 우리가 만든 판정 문제 자체를 고쳐야 한다.**
입력 파일과 환경변수를 읽는 기본 경로는 정상이라는 근거가 있지만, 판정에 필요한 정보가
모델까지 모두 전달된다는 주장은 성립하지 않는다. 제품 CSV의 적용 조건이 renderer 이전에
빠지고, 일부 카드는 항목표의 적용 범위를 과도하게 좁혔을 가능성이 높다. 같은 카드·조회·검사를
고정한 채 호출 순서를 수십 번 바꾸면 이 오류도 함께 고정된다.

이번 분석에서 특히 중요한 결과는 다음과 같다.

1. 제품 index의 `특이사항`은 파일에 있지만 prompt용 fact에는 없다. 조건부 제품 185/615개,
   그 코드와 매칭되는 dev 공고 35/200개가 있다. **패키징 성공과 의미 입력 완결은 다르다.**
2. 카드 v6의 v6·v7은 지방 소액수의 중심의 적용 전제를 요구한다. 그러나 항목표는 국가계약
   근거도 제시하며, v7 gold 양성 7건 중 4건은 국가계약이다. 이는 카드/항목표/정답 간의
   실질적인 충돌로, 단순한 모델 독해 실패라고 부를 수 없다.
3. EXP171의 dev200 0.307962는 정탐 48, 오탐 37, 미탐 105다. 12개 항목은 정탐이 0이고,
   부재탐지 5개도 전부 정탐 0이다. 현재 예측에서 오탐만 완벽하게 제거해도 **0.362581**이다.
4. 최근 specialist 실험에는 비교 해석 문제가 있다. EXP190/191의 낮은 전체 점수에는
   다시 실행한 앞 단계의 변동이 섞였다. 같은 실행의 일반 final과 비교하면 specialist의
   순증은 각각 +0.011905 / +0.016667이다. 이것도 승격 근거는 아니지만, 감소 원인을
   specialist 자체로 전부 귀속하면 잘못된 연구 결론을 낸다.
5. dev 라벨은 운영진이 노이즈 가능성을 인정한 참조 자료다. 공식 기준에 맞는 예측을 dev의
   오탐으로 벌점 주는 사례도 확인된다. dev 점수만으로 기준 해석까지 선택하면 public에서
   악화될 수 있다. 이 문제를 모델 호출 추가로 해결할 수는 없다.

0.3은 실행 가능한 올바른 기준선과 입력 결함 교정의 목표로 삼을 수 있다. 0.5 이상은 현재
정탐이 없는 항목들을 회복해야 하며, 0.7은 판정 기준 정합성·양성 회복·오탐 제어·실행 시간의
동시 개선이 필요하다. 이번 분석으로 어느 점수도 달성했다고 주장하지 않는다.

## 1. 근거와 분석 범위

`docs/`, `incubator/docs/`의 기존 문서 311개를 목록·해시로 등록했다. 초기 EXP001 계열부터
EXP191까지의 결과 문서, source-first 매트릭스, complete-fact 요약, 제출 기록, WSL 내부
leaderboard 및 INC125/128/130 등 원인 분석을 교차 검토했다. 311개 모두를 같은 깊이로
독립 재검증했다는 뜻은 아니다. 요약의 중요한 수치는 가능한 경우 실제 예측으로 내려가 확인했다.

`outputs/*/metrics.json` 중 mock을 제외하고 dev 예측 CSV를 가진 **185개 기록**을 정확한 ID로
정답에 연결하여 직접 TP/FP/FN과 `mean_v[2TP/(2TP+FP+FN)]`을 재계산했다. 저장된 macro와의
불일치는 0개다. 이 목록에는 작은 진단, 다른 모델, 역사적 정책도 들어 있으므로 185개를 모두
유효한 후보나 독립 검증으로 취급하지 않는다. 특히 WSL teacher 결과는 접근 가능한 결과
문서를 근거로 인용하며, 이번 CSV 185개 재계산에 포함됐다고 주장하지 않는다.

재현 코드는 [analyze_astra_research_history.py](../scripts/analyze_astra_research_history.py),
전체 수치·cohort hash·파일 hash는 ignored
[audit.json](../outputs/astra_research_audit_20260911/audit.json)에 있다.

```bash
.venv/bin/python scripts/analyze_astra_research_history.py
```

새 모델 호출·self-label·학습·라벨 수정은 하지 않았다. 기존 미커밋 실험 코드는 보존했다.
공식 해석은 2026-09-11에 운영진 답변 원문도 재확인했다. 외부 웹 내용은 분석의 출처이며
추론 prompt나 새 제출 asset에 주입하지 않았다.

## 2. 먼저 바로잡아야 할 입력 계약

### 2.1 제품 CSV의 조건 열이 실제 판단 입력에서 사라진다

경로는 다음과 같다.

```text
organizer CSV
  → competition_products_v1.json: 제품명 + 특이사항 보존
  → src/data.py competition_product_fact(): matched_products는 코드와 제품명만 반환
  → src/prompt.py format_competition_product_context(): 등재 제품명만 설명
  → final Gemma: 등재 사실은 보지만 그 행의 적용 조건은 조회 정보로 받지 못함
```

현재 index는 615개 코드이며 185개에 `특이사항`이 있다. dev200의 35개 공고가 그중 하나
이상과 매칭된다. 예를 들면 행사 서비스에는 금액 조건, 서버에는 CPU/주파수 조건, 드론에는
제외 종류와 중량/고도 조건이 있다. **정확한 코드 일치만으로 해당 구매에 적용되는 경쟁제품임이
확정되는 것은 아니다.** 문자열 매칭 정확도와 법적 적용 정확도를 분리해야 한다.

구체적으로 `PPS-DEV-054`는 코드 `9015189001`에 매칭되고 metadata 추정가격은
327,272,727원이다. index의 해당 행에는 `추정가격 3억원 미만에 한함`이 있으나 현재 fact
경로가 이를 전달하지 않는다. 저장된 EXP171 DEV-054의 실제 final message에서도 해당 조건
문장이 없고 제품명 등재 안내만 있는 것을 확인했다. 이 한 예로 v14 등의 최종 정답을 Python에서 결정하자는 뜻이
아니다. 모델이 검토해야 할 필수 조건이 사라지는 것을 보여 주는 반례다.

또한 `competition_product_fact()`는 모든 문서에 등장하는 매칭 코드를 합친다. 따라서
실제 구매대상, 참가자격 등록코드, 기존 장비, 복수 구매품목을 구분하지 않은 notice 수준의
`matched`는 혼합 구매 전체를 단일 경쟁제품으로 해석하게 할 위험이 있다. 이 위험의 개별
오답 기여량은 아직 측정하지 않았다.

우선 필요한 변경은 Python 법률판정이 아니다. **매칭된 각 제품의 원본 조건과 그 코드가
어디서 나왔는지를 사람이 읽을 수 있게 전달하고, 실제 구매대상과의 적용 관계를 Gemma가
판단하게 하는 것**이다. 이 조건 정보 복원은 기존 raw-law RAG 재실행과 다르다.

### 2.2 v6·v7은 입력 누락보다 문제 정의의 범위가 의심스럽다

배포 항목표의 v6·v7은 국가계약법 시행규칙 근거와 지방계약법 근거를 모두 가진다.
비고는 `지방 + 소액수의 가능`이다. 반면 카드 v6는 v6에 지방계약의 2인 이상 견적 수의계약
등을, v7에 v6의 지방 소액수의 적용 유형을 선행조건으로 적었다.

| 대조 | 관찰 |
| --- | --- |
| v6 gold 양성 | 6건 모두 metadata 계약방법이 제한경쟁, 1건은 국가계약 |
| v7 gold 양성 | 7건 모두 제한경쟁, 4건은 국가계약 |
| EXP171 v6 / v7 | 각각 TP 0, FP 0, FN 6 / 7 |
| 원문 예시 | DEV-08은 협상 방식과 실제 소재지 자격 제한을 명시; DEV-09는 국가계약의 지역 참가범위 제한 |

이것만으로 법적 정답이나 모든 dev 라벨의 타당성을 확정할 수는 없다. 그러나 **예외·허용
조건을 전체 항목의 적용 전제로 뒤집었는지** 독립 검토할 충분한 증거다. 카드가 시킨 대로
0을 내는 모델을 더 오래 생각하게 하거나, 같은 카드로 verifier를 추가해도 이 문제가 남는다.

운영진은 v2의 같은 비고 표현에 대해 지방 소액수의를 별도 특례로 설명했다. 이를 v6·v7에
자동 적용하지는 않되, 비고의 논리적 역할을 재확인해야 한다는 보조 근거다.
[운영진 v2 답변](https://dacon.io/competitions/official/236754/talkboard/417262)

다음 감사는 v6 한 항목부터 원래 항목명 → 국가/지방 기준 → 허용 예외 → 카드 문장으로
역추적한다. dev 정답에 맞춰 범위를 넓히는 방식 대신, 배포 기준에서 독립적으로 결정한 후
현재 gold와의 충돌을 기록한다. 충돌이 해소되기 전 카드 전체를 새 버전으로 일반화하지 않는다.

### 2.3 unknown 정보가 있다는 것과 필요한 사실이 있다는 것은 다르다

v10–v18 gold 양성 58개 중 현재 exact-code 조회가 `unknown`인 것은 30개다.

| 항목 | 양성 수 | matched | not_matched | unknown |
| --- | ---: | ---: | ---: | ---: |
| v10 | 7 | 1 | 0 | 6 |
| v11 | 6 | 3 | 0 | 3 |
| v12 | 6 | 3 | 2 | 1 |
| v13 | 6 | 4 | 0 | 2 |
| v14 | 8 | 1 | 3 | 4 |
| v15 | 6 | 0 | 4 | 2 |
| v16 | 6 | 0 | 1 | 5 |
| v17 | 6 | 1 | 3 | 2 |
| v18 | 7 | 0 | 2 | 5 |

unknown을 1로 바꾸라는 뜻이 아니다. 원문에 다른 적용 사실이 있는지, 여러 품목을 잘못
묶었는지, 조건부 등재인지, 실제로 정보가 없는지, gold가 노이즈인지 분해해야 한다.
`unknown을 자동판정하지 말라`는 안내와 `필수 전제가 불명이면 0`이라는 카드가 함께 있으면,
모델이 합리적으로 보수적인 0을 반복할 수도 있다. 현재 실험은 이 병목을 독립적으로 측정하지 않았다.

### 2.4 semantic-input PASS의 범위를 넓게 해석했다

현재 `audit_candidate_semantic_contract.py`는 카드 문자열의 span, metadata 필드 제목,
제품 문맥 section 존재, 문서 type header, ledger 출처 등을 확인한다. 이 검사는 중요하지만
다음은 증명하지 않는다.

- 카드가 원래 기준을 논리적으로 정확하게 옮겼는가.
- metadata 값이 실제 적용 판단에 충분한가.
- 제품 행의 조건 열이 빠지지 않았는가.
- 동일 문서 유형의 모든 문서·조각이 빠짐없이 보존됐는가. 이는 별도의 exact coverage 검사 대상이다.

카드와 contract가 같은 잘못된 해석에서 만들어졌다면 서로 일치해도 PASS한다. 그러므로 기존
EXP152–191은 **현재 card/renderer 정의 아래의 complete-fact 실험**으로는 재현 가능하지만,
법률·제품 적용 사실까지 완결됐다는 더 강한 표현은 철회해야 한다.

## 3. 점수의 병목은 어디인가

### 3.1 local과 public, 모델과 규칙을 분리해야 한다

| 정책 | dev200 | public 기록 | 비고 |
| --- | ---: | ---: | --- |
| EXP120 | 0.248932 | 0.244317 | 단일 4k + 카드 v6 |
| EXP123 | 0.317797 | 0.260446 | EXP120 + 동결 v2/v3/v21 규칙 |
| EXP135 | 0.246942 | 0.220069 | 2-way item 분할 |
| EXP171 | 0.307962 | 점수 없음 | full-source 2단계, 제출 timeout |
| EXP172 | 0.259281 | 이 비교에 대응하는 기록 없음 | EXP171의 one-stage control |
| 동료 near-vanilla | local 미확보 | 약 0.32734 | 구두 관측, 정확한 zip/config 미확보 |

public 수치는 [submission_lessons.md](submission_lessons.md)의 기록이며 이번에 제출 서버의
개인 이력을 읽어 재확인한 것은 아니다. 다른 참가자의 0.7은 사용자가 전달한 관측으로 취급한다.
상위권의 코드·정책을 보지 않았으므로 성공 원인을 추정해 사실처럼 말하지 않는다.

EXP120은 local/public 차이가 약 -0.0046으로 작다. 따라서 **모든 낮은 점수가 원격 provider와
vLLM 차이 때문이라는 설명도 근거가 약하다.** EXP123의 더 큰 낙차는 dev에서 설계한 세 규칙의
효과가 public에서 작아졌다는 설명과 맞지만, public per-item가 없어 완전한 원인 분해는 불가능하다.

EXP171/172는 `postprocess.frozen_rule_set: exp123_v1`을 실제 사용한다. 이는 Python은 label을
판정하지 않는다는 최근 설명과 다르다. 역사적 재현을 위해 남아 있는 예외를 명시해야 한다.
이번 분석에서 pass judgment를 OR/부재 AND로 다시 합쳐 규칙 적용 전을 계산했다.

| 정책 | 동결 규칙 전 | 규칙 후 | 변경 cell |
| --- | ---: | ---: | ---: |
| EXP171 | 0.250070 | 0.307962 | 26 |
| EXP172 | 0.177321 | 0.259281 | 32 |

EXP171의 세 규칙 항목은 모두 F1=1이며 전체 macro에 0.125를 기여한다. 나머지 21개 항목의
평균 F1은 약 0.2091이다. “Gemma가 24개를 고르게 풀어 0.308”이라는 해석은 틀리다.
다만 source-first 개선은 규칙 전에도 보이므로 구조적 신호 자체를 부정하지 않는다.

### 3.2 source-first의 주효과는 폭넓은 양성 회복보다 오탐 감소다

| 정책 | TP | FP | FN | micro precision | micro recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| EXP172 direct | 45 | 78 | 108 | 36.6% | 29.4% |
| EXP171 source-first | 48 | 37 | 105 | 56.5% | 31.4% |

총 86개 cell이 달라졌고 65개가 맞아지고 21개가 틀려졌다. +0.048681의 macro 개선은 유용하지만
31.4%라는 낮은 recall을 해결하지 못했다. notice 단위 paired bootstrap 5,000회(seed 20260911)의
차이 95% percentile interval은 **[-0.0030, +0.0956]**이다. 희소 항목의 support=0 resample은
기존 metric처럼 F1=0으로 처리했다. 이는 고정된 두 예측의 표본 민감도만 나타내며 provider
변동·반복 선택 편향·public 분포까지 포함한 신뢰구간은 아니다.

fast/holdout/dev200의 같은 방향은 현재 가진 가장 좋은 구조 증거다. 그러나 그것을 통계적으로
확정된 큰 효과, 모든 새로운 모델의 한계, 또는 0.7로 가는 검증된 방법으로 확대할 수 없다.

### 3.3 정탐 0인 항목이 절반이다

| v | EXP171 TP/FP/FN | F1 |
| --- | --- | ---: |
| 1 | 5 / 1 / 2 | .7692 |
| 2 | 7 / 0 / 0 | 1.0000 |
| 3 | 8 / 0 / 0 | 1.0000 |
| 4 | 0 / 1 / 6 | .0000 |
| 5 | 3 / 2 / 4 | .5000 |
| 6 | 0 / 0 / 6 | .0000 |
| 7 | 0 / 0 / 7 | .0000 |
| 8 | 3 / 4 / 3 | .4615 |
| 9 | 5 / 7 / 1 | .5556 |
| 10 | 0 / 0 / 7 | .0000 |
| 11 | 0 / 0 / 6 | .0000 |
| 12 | 1 / 0 / 5 | .2857 |
| 13 | 0 / 4 / 6 | .0000 |
| 14 | 0 / 0 / 8 | .0000 |
| 15 | 1 / 0 / 5 | .2857 |
| 16 | 0 / 0 / 6 | .0000 |
| 17 | 0 / 0 / 6 | .0000 |
| 18 | 0 / 0 / 7 | .0000 |
| 19 | 4 / 2 / 2 | .6667 |
| 20 | 0 / 0 / 5 | .0000 |
| 21 | 6 / 0 / 0 | 1.0000 |
| 22 | 3 / 1 / 2 | .6667 |
| 23 | 2 / 13 / 3 | .2000 |
| 24 | 0 / 2 / 8 | .0000 |

부재탐지 5개는 총 31개 양성을 모두 놓친다. 이 5개가 모두 F1 0이면 다른 19개가 완벽해도
최대 19/24=.7917이다. 현재처럼 12개가 F1 0이면 나머지가 완벽해도 최대 .5다.
0.7을 넘으려면 적어도 17개 항목에서 F1이 양수여야 한다는 것은 필요조건일 뿐, 17개에서
양성 하나씩 잡으면 충분하다는 뜻은 아니다.

현재 EXP171의 FP를 정답을 이용해 전부 지우는 **진단용 oracle**을 계산하면 .362581이다.
이는 배포 가능한 정책이나 모델 전체의 상한이 아니라 “현재 recall을 그대로 둔 검증-only
방식”의 상한이다. v23 하나를 완벽하게 고쳐도 macro 이득은 최대 (1-.2)/24=.0333이다.
따라서 v23 날짜 schema를 계속 확장하는 일은 0.5·0.7 목표의 중심 전략이 될 수 없다.

## 4. 우리가 실험 결과를 잘못 배울 위험

### 4.1 dev는 작은 데다 임의 순서 표본이 아니다

dev는 4,800개 label cell 중 양성 153개(3.1875%)이며 항목당 양성은 5–8개다.
파일 앞 75개 공고에 135개 양성(88.2%)이 모여 있고 뒤 125개에는 18개뿐이다.
101–125, 151–200 위치의 75개 공고에는 양성이 하나도 없다. 이 순서를 날짜나 자연스러운
모집단 구간으로 해석하지 않는다. ID/순서로 라벨을 만드는 것은 금지해야 한다.

fast20은 양성 38/480=7.92%로 dev200보다 약 2.48배 풍부하다. 15개 항목의 양성이 각각
한 개뿐이다. 그런 항목에서 FP 없이 유일한 TP 하나를 얻거나 잃으면 전체 macro가 최대
1/24=.0417 바뀐다. 몇 개의 판단 변동만으로 +.03, -.05를 만들 수 있다.

고정 fast20은 재현용으로 계속 사용하되, 작은 음수 한 번을 모든 유사 방법의 반증으로
격상하지 않는다. holdout20은 fast20과 분리됐지만 같은 dev200에서 반복 사용됐고 card와
동결 규칙의 과거 설계에도 dev가 쓰였다. **프로젝트 전체에서 완전히 미사용된 독립 test는 아니다.**
새로 나눈 dev fold도 과거 노출을 없애 주지 않는다.

### 4.2 official 기준과 dev gold가 다를 수 있다

운영진은 dev가 실제 검토 이력 기반이며 일부 노이즈가 있을 수 있고, 평가셋은 별도 다층
검증으로 관리된다고 설명한다. v9는 규격서 등의 모델·제조사 명시를 기준으로 보며,
v13은 경쟁제품 입찰에서 중기업 배제 여부를 보라고 안내했다.
[운영진 원문 답변](https://dacon.io/competitions/official/236754/talkboard/417272)

실제 `PPS-DEV-180/v9`는 gold 0이다. EXP172는 1, EXP171은 0으로 예측했다. 따라서
dev metric에서는 source-first가 FP 하나를 없앤 것으로 보인다. 하지만 운영진이 바로 이
사례의 모델명 명시 판단을 설명했으므로, 이 변화가 실제 기준에서도 개선인지 단정하면 안 된다.
이 한 cell로 전체 +.0487을 부정하는 것도 잘못이다.

현재 nonempty gold evidence는 54개이고 blank는 99개다. blank 중 부재항목 양성은 31개,
나머지 **68개는 비부재항목 양성인데도 evidence가 없다.** blank는 근거가 원문에 없다는
증명도, 정보가 부족하다는 증명도 아니다. EXP171은 nonempty 54개 중 27개, blank 99개 중
21개를 맞혔다. 근거가 있는 subset의 recall만으로 전체 판정 문제를 진단할 수 없다.

공식 답변으로 확인된 사례와 해결되지 않은 충돌을 별도 dossier로 관리하되, 공식 dev CSV나
정식 metric은 수정하지 않는다. official-concordance 보조 검토는 dev score를 유리하게
수정한 새 리더보드가 아니다. 법적으로 정확한 card와 dev상의 최고 card를 구분하기 위한 것이다.

### 4.3 EXP190/191 비교에서 앞 단계 재실행 효과가 섞였다

| 실행 | 같은 실행의 일반 final | specialist 적용 후 | specialist 순증 |
| --- | ---: | ---: | ---: |
| EXP190 | .220833 | .232738 | +.011905 |
| EXP191 | .200000 | .216667 | +.016667 |

EXP179의 .287500과 비교한 전체 감소 대부분은 specialist 이전부터 발생했다. EXP190/191의
일반 final은 EXP179 대비 각각 10/8 cell이 달랐으며, v23을 제외해도 7/6 cell이 달랐다.
이는 원격 backend만의 원인이라고 단정할 수 없다. stage-1 navigation을 다시 생성한 효과,
모델 비결정성, transport 차이가 모두 포함된다.

같은 실행의 v23은 EXP190에서 0TP/1FP/1FN → 1TP/5FP/0FN,
EXP191에서 0TP/2FP/1FN → 1TP/3FP/0FN이다. 둘 다 오탐 부담이 크고 표본도 작아
승격하지 않는 판단은 타당하다. 그러나 “specialist가 macro를 떨어뜨렸다”는 설명은 정정해야 한다.
EXP179 호출 수도 문서 일부의 40이 아니라 저장 inventory 23 + final 24 = **47**이다.

향후 마지막 한 단계만 바꾸는 가설은 같은 upstream 결과를 control/treatment에서 공유하여
그 단계의 효과를 측정한다. 이 cached-upstream 검사는 전체 전략 재실행 성능이 아니라
국소 단계 효과라는 이름으로 보고하고, 이득이 있을 때 별도로 end-to-end 반복을 한다.
이렇게 해야 작은 아이디어를 버릴지 결정하는 데 불필요한 upstream 변동이 덜 섞인다.

### 4.4 cap 초과와 timeout에 대한 과거 단정도 수정해야 한다

EXP171 prediction의 `usage.completion_tokens`는 stage-1들과 final usage의 합이다.
합계가 2,500을 넘는 12개 record를 세어 **12번의 개별 호출이 cap을 넘었다고 말할 수 없다.**
당시 runner도 이를 합산해 저장했다. 같은 저장물에서 개별 응답의 cap 위반을 확정할 수 없으며,
별도 provider raw 로그가 필요하다. INC050/051의 실제 whitespace runaway 기록과 이 합산
오해는 서로 다른 문제다.

또 2시간 timeout만으로 모델 loading이 정상 종료됐는지, GPU에서 어디가 병목이었는지 알 수 없다.
batch64가 batch128보다 KV-cache 부담을 더 키웠다고 단정한 앞선 답변도 근거가 없다.
batch는 요청 총량을 바꾸지 않지만 throughput에는 영향을 줄 수 있다. 긴 입력·두 단계는
유력한 부담 요인이며, 직접 원인을 확인하려면 phase별 실측이 필요하다.

## 5. 호출·RAG·예측 구조에 대한 재평가

### 현재 EXP171

모든 제공 원문 pack을 읽고 7개 범주의 navigation을 생성한 뒤, final에서 card·metadata·제품
fact·navigation·원문 packs로 판단한다. dev200의 216+219=435회, 원격 총 6.08M tokens는
재현된다. 모든 원문이 final **단계 전체에 걸쳐** 들어간다는 뜻이지, overflow 공고의 각 final
call 하나에 모든 문서가 동시에 들어간다는 뜻은 아니다. 분할된 관계는 여전히 문맥을 넘을 수 있다.

다만 dev200 EXP172의 186건은 single-pack이고, 그 안에서 FP70/FN105가 발생한다.
EXP171도 single-pack 184건에서 TP48/FP34/FN102다. 두 run의 multi-pack 양성 support는
각각 3개뿐이다. merge만 고치는 것이 주된 병목을 해결한다는 가설은 현재 자료가 지지하지 않는다.

### 이미 시도한 큰 계열

| 계열 | 근거 | 이번 판단 |
| --- | --- | --- |
| 입력 확대 / 첨부 제외 | EXP004/111/113, EXP152/154/172, EXP189 | 양을 늘리기만 해서는 부족; 첨부를 일괄 제거할 근거 없음 |
| 법령 원문·요약 RAG | EXP005 .1679, INC021/030/122 | 현재 방식의 성능·비용 이득 없음; 재실행 제안 안 함 |
| item grouping | EXP044/096/097, EXP135 public .2201, EXP155/156 | 분할의 recall/비용 문제; source-first와 곱하지 않음 |
| inventory 뒤 압축 final | EXP153/157/158, INC073 | 추출 누락이 final에서 복구되지 않음; excerpts-only는 채택 근거 없음 |
| source-first full final | EXP167/168/171/179 | 로컬의 가장 일관된 신호, 입력 결함·양성 회복·runtime은 미해결 |
| navigation 범주/개수/관계 변경 | EXP174–188 | 유효 후보 없음; 용어·slot 재포장은 새로운 실험이 아님 |
| V-only / voting / review | EXP125/186/187, INC054/063/068/129 | 출력 절약은 가능, recall 개선 증거 부족 |
| 사례 retrieval / self-label bank | S0A/B/C, INC111/112 | 키워드·문서형식 유사성이 법적 관계 유사성을 대체하지 못함 |
| 더 강한 teacher | INC088 .360726, INC125 .427366 | 표현과 기준이 중요하다는 진단 증거; 최종 모델 대체나 Gemma 성능 보장 아님 |

S0C의 BGE AUC .5211, evidence localization 12/42는 해당 24개 teacher-positive fact bank를
그대로 확대할 근거가 없다는 뜻이다. 모든 가능한 RAG를 수학적으로 반증한 것은 아니지만,
현재 새 검색 key의 이득 증거도 없다. 이번 우선순위에 raw 법령/일반 사례 RAG를 넣지 않는다.

E0의 “4k 밖 gold evidence는 7개뿐”도 54개 nonempty evidence subset에 관한 관찰이다.
문맥·예외·대응 값은 인용문 밖에 있을 수 있고, blank 99개는 이 검사의 직접 대상이 아니다.
그 수치를 전체 source 관측의 개선 상한으로 사용하면 안 된다. 그렇다고 global selector를
재시도하자는 제안도 아니다. 현재는 확정된 조건 정보 누락부터 해결하는 편이 낫다.

## 6. 실행 파일 감사에서 확인한 것과 남은 것

timeout zip의 entrypoint/config/cards/products hash와 현재 대응 파일은 직전 감사에서 일치했다.
그 zip으로 `PPS_*`를 넣은 mock 10건의 49열 CSV·ID·복구 경로가 통과했다. 현재 소스도
`PPS_DATA_DIR/test.jsonl.gz`, 같은 디렉터리의 항목표, `PPS_MODEL_DIR` 모델/tokenizer,
`PPS_OUTPUT_DIR/submission.csv`를 쓴다. embedding 미사용이므로 `PPS_EMBED_DIR` 미사용은
그 자체로 결함이 아니다. test 원문은 evaluator가 제공하고, zip에는 필요한 static assets만 넣는다.

그러나 mock의 0-only 응답은 **실제 모델 품질, 1인 label의 evidence, 배치별 ID 대응의 모든
오류, GPU throughput**을 증명하지 않는다. loader가 baseline보다 더 많은 record 필드를 필수로
요구한다는 차이도 있다. 현재 sample에는 맞지만 hidden schema 변동을 허용하는지는 별도 문제다.

현재 설정은 baseline과 temperature 0, seed 20260826, TP1, GPU memory .92, 기본 INT8,
structured JSON, `LLM.chat`에서 같지만 context 16k→32k, output1536→2500, batch128→64,
single→2-stage에서 다르다. `PPS_QUANT=none` 정규화도 baseline과 다르다. 이 차이가 timeout
원인이라고 확인된 것은 아니다.

또 source-first 제출 orchestration은 `submission/script.py`에 별도 구현되어 shared pipeline의
동작을 모방한다. 동일 소스 디렉터리를 패키징했다는 사실만으로 로컬의 stage builder/recovery와
완전한 동등성이 자동 성립하지 않는다. 비교하려면 같은 고정 inventory에 대해 실제 local/final
messages·schema·pack·merge 결과를 zip 버전과 대조해야 한다.

필요한 GPU 측정은 loading, token admission, stage1 prefill/decode, final admission,
final prefill/decode, recovery, CSV를 각각 구분한다. 요청별 prompt/generated tokens,
finish_reason, output count, batch size를 남긴다. 정확한 template·quantization/backend가
다른 OpenRouter wall time으로 2시간 내 완료를 보장할 수 없다. 현 mac에서는 GPU/vLLM을
실행하지 않았다.

## 7. 다음 실험의 우선순위

### 0순위: 공식 기준과 실제 입력의 정합성을 먼저 복구한다

두 작업을 각각 독립적으로 한다.

**A. 제품 적용 조건 전달.** base는 EXP172의 versioned config로 두고 matched row의
`특이사항`과 코드 출처의 human-readable 표현만 추가하는 ablation을 설계한다. 제품 자체를
Python에서 적용/비적용으로 계산하지 않는다. 카드·model params·source scope·merge는 고정한다.
조건부 35건의 actual rendered span을 확인하고, fast20에서 이 조건을 실제로 사용하는 사례가
포함되는지 사전에 기록한다. 다음 단계는 independent holdout20, 그 뒤 dev200이다.

**B. v6의 적용범위 출처 감사.** 국가/지방 원문 기준과 item table 비고를 독립적으로 읽고,
현재 카드의 제한이 출처에 있는지 먼저 판단한다. 원문으로 수정이 정당화될 경우에만 v6 하나의
card 변경을 선언한다. 숫자·ID·정답 패턴을 새 판단 규칙으로 만들지 않는다. v7/다른 항목에
동시에 일반화하지 않는다. 기준의 정확성과 모델 개선이라는 두 질문을 따로 평가한다.

이것은 기각된 card 문구 polishing을 반복하는 것이 아니다. 실제 누락 열과 적용범위 충돌이라는
새 증거를 해결하는 작업이다. source/법적 검토에서 결함이 해소되지 않으면 유료 실행을 하지 않는다.

### 1순위: public에 연결되는 대조군과 관측 체계를 확정한다

exact organizer control은 재현성 대조군으로 가치가 있다. 다만 이전 baseline 변형의 public
관측도 있고 친구의 원본도 없으므로, 새 exact baseline이 반드시 .327을 낸다는 기대는 버린다.
공식 원본을 별도로 복사해 제출하지 않고 tracked entrypoint/shared pipeline에서 재현한다.

정확한 친구 artifact를 얻으면 prompt뿐 아니라 출력 schema, template, 모델 옵션, context,
후처리까지 비교한다. 없더라도 A/B 입력 감사를 계속할 수 있으므로 친구 파일을 모든 연구의
필수 blocker로 만들지 않는다. 수정 후보는 별도 config에서 준비하고 runtime 검증 후 제출한다.

### 2순위: 남는 FN을 판단 단계별로 분해한다

새 7범주 schema를 설계하기 전에, 0순위에서 정리된 한 항목을 골라 다음을 평가한다.

```text
필요한 사실이 제공됐는가
  → 대상 품목/참가자/문서 역할을 맞게 연결했는가
  → 일반 규정과 예외를 정확한 방향으로 적용했는가
  → 모은 사실과 최종 0/1이 일관되는가
```

Gemma가 찾아야 할 관측 사실의 정답을 사람이 organizer 원문에서 검토한 작은 진단 세트를
만든다. 독립적으로 원문 판단을 먼저 기록하고 마지막에 dev label과 대조한다. 배포용 few-shot
bank나 Python rule로 재사용하지 않는다. 올바른 사실이 주어졌을 때도 판단을 못하는지, 사실
추출에서 이미 막히는지를 분리해야 다음 구조의 필수 구성요소가 나온다.

관계 추출을 다시 실험할 필요가 입증되면, 최소 한 항목에서 source-only 사실의 정확도·누락률·
최종 판단 일관성을 관찰한다. final은 카드·필요 metadata/제품 조건·전체 admitted source를
유지한다. facts-only final, 모든 v의 새 schema, Python 숫자/법률 label override로 확대하지 않는다.
기존 EXP180/182/188/191과 무엇이 달라졌는지 명시할 수 없으면 실행하지 않는다.

### 3순위: V-only와 verifier는 측정된 역할이 있을 때만 사용한다

V-only의 작은 output은 비용 이점이지 정확도 이점이 아니다. INC/EXP 양쪽의 반복 결과에서
recall 하락이 있었다. 여러 번 호출해도 같은 잘못된 카드·제품 사실·보수적 0이 반복되면
독립적인 오류 교정 정보가 생기지 않는다.

양성만 검증하는 pass는 현재 TP를 늘릴 수 없으므로 위 .3626 상한을 벗어날 수 없다.
새 verifier를 하려면 어떤 미탐을 새로 찾는지까지 가설에 넣어야 한다. e를 알고리즘으로
찾는 방식은 source span의 추적이 필요하며, e가 없어도 label을 조용히 바꾸지 않는다.
단순한 v binary만으로는 e 위치가 식별되지 않으므로 zero-cost evidence를 가정하지 않는다.

## 8. 0.3·0.5·0.7 목표를 어떻게 관리할 것인가

| 목표 | 필요한 증거 | 현재에서의 의미 |
| --- | --- | --- |
| public .3 초과 | corrected input + 재현 가능한 실행 + 실제 public 결과 | dev .308 자체는 이미 있으나 rule 의존/timeout; 현재 가장 가까운 검증 목표 |
| .5 초과 | 현재 zero-TP 항목군의 실제 회복, 기존 TP 보존, FP 통제 | 현재 살아 있는 12개만 개선하면 수학적으로 부족; 적용범위/제품/부재가 핵심 |
| .7 초과 | 더 많은 항목에서 높은 precision과 recall, official 기준 정합성, runtime 동시 충족 | 좁은 v23 보정이나 voting의 누적으로 보장할 수 없는 전체 문제 |

가령 현재 12개 zero-F1 항목을 각각 .4까지 회복하고 나머지가 유지되면 .30796+.2=.50796이다.
이는 효과 예측이 아니라 필요한 개선 폭을 보여 주는 산술 시나리오다. 반대로 zero 항목을
방치한 채 이미 맞히는 항목의 FP만 줄이는 전략은 .5를 만들 수 없다.

INC125 teacher의 .4274, 동결 규칙 합성 .4622도 “이 데이터에서 .7은 불가능”이라는 증거가
아니다. 그 teacher도 특정 카드·해석·출력 계약을 사용했다. 더 강한 모델까지 공통으로 실패한
항목은 모델 크기만 탓하기보다 입력/적용 정의/라벨 충돌을 우선 의심할 근거다.

성공 기준에는 headline macro 외에 zero-TP 항목 수, 항목별 TP/FP/FN, applicability unknown,
조건부 제품 사실 보존, parse/finish_reason, source coverage, 실제 GPU 시간을 함께 둔다.
fast20 + holdout20 → dev200 순서를 유지하되, 기준 오류를 고친 후보가 noisy dev에서 내려갔다는
이유만으로 공식 기준을 다시 틀리게 바꾸지는 않는다. 승격 여부는 별도 근거와 public에서 판단한다.

## 9. 재현·완료 확인과 남은 한계

이번에 완료한 것은 원인 분석과 다음 실험 설계다. 새 성능 실험·card 교정·제품 renderer 변경·
새 zip·public 제출은 이 문서에서 완료했다고 주장하지 않는다.

- 185개 저장 metric을 CSV에서 재계산했고 모두 일치했다. 기본 점수 계산의 광범위한 버그는
  발견하지 못했다. 이것이 gold 의미·hidden 입력·모든 JSON 후처리의 무결성 증명은 아니다.
- EXP171/172와 최근 specialist의 exact-ID 대조, 규칙 전/후, per-item 및 paired bootstrap을
  `audit.json`에 보존했다. bootstrap은 실제 값과 별개인 불확실성 분석이다.
- 제품 조건 누락은 index→fact→renderer 코드로, 카드 범위 충돌은 item table→card→원문/
  metadata로 추적했다. 이 결함들의 성능 개선 폭은 아직 측정하지 않았다.
- AGENTS.md와 memo의 정책을 검토했다. 이 문서는 정책 승격이 아닌 branch 분석이므로
  canonical/AGENTS/memo를 바꾸지 않았다. 향후 실제 정책 교정 시 함께 정합화해야 한다.
- 기존 자료 중 “가능한 구조를 모두 기각했다”, “입력 완결이 증명됐다”, “timeout 원인이
  batch로 확정됐다”는 표현은 해당 실험 범위를 넘는다. 이 문서는 그 과도한 일반화를 정정한다.

주요 근거:
[complete-fact 결과](complete_fact_experiment_summary_v1.md),
[source-first 대조](exp167_source_first_full_final_retry_plan.md),
[아키텍처 매트릭스](source_first_architecture_matrix_v1.md),
[제출 관측](submission_lessons.md),
[실행 계약 감사](execution_contract_audit_result_v1.md),
[merge 진단](exp172_merge_deep_diagnostic.md),
[EXP190](exp190_v23_specialist_final_owner_plan.md),
[EXP191](exp191_v23_proof_carrying_final_plan.md),
[E0](evidence_first_e0_result.md),
[S0C](fact_precedent_s0c_result.md),
[WSL 연구 이력](../incubator/docs/leaderboard.md),
[teacher full-dev](../incubator/docs/inc125_luna_full_dev_official_ledger_result.md),
[동결 규칙의 fold 한계](../incubator/docs/inc130_exp123_frozen_fold_stability_result.md).
