# D0 — 동일 공고의 decoding 다양성 관측 계획

작성일: 2026-09-07 (mac / dev)

## 질문

지금까지의 실험은 입력 문맥, 법령, 카드, 사례, 문서 분할을 바꾸는 방식이었다.
그 대부분은 성능 또는 runtime에서 반증됐다. 한 공고를 한 번의 greedy Gemma 판정으로
고정하는 것이 남은 별개의 병목인지 확인한다.

이 실험은 새 정보ㆍ새 규칙ㆍ새 retrievalㆍ새 merge 정책을 넣지 않는다. 동일한
organizer-baseline V/E 요청에서 stochastic decoding이 실질적으로 다른, 유효한 판단을
만드는지 먼저 관측한다.

## 고정 control과 treatment

Control은 이미 완료된 `exp-125a-exact-baseline-ve-fast-panel`이다.

- 공고 context: ordered 4,000자, `single`, overflow 없음
- prompt: `official_baseline_v1`, plain, minimal item list, `official_lines`
  metadata, card/RAG/product context 없음
- V/E JSON schema, token reserve 1,536, actual-document evidence 계약, provider 및
  scheduler는 동일
- control decoding: temperature 0.0, seed 20260826

첫 treatment (`exp-126a`)의 유일한 유효 정책 차이는 `temperature: 0.2`,
`seed: 20260907`이다. seed 변경은 sampling sequence를 독립화하기 위한 transport
parameter이며 prompt, model, schema, parsing, merge, evidence gate를 바꾸지 않는다.

## D0a: 단일 20-notice probe

1. `scripts/preflight_experiment.py`로 declared diff가 temperature/seed/output path뿐인지
   검사한다.
2. mock 20건 및 exact tokenizer admission을 통과시킨다.
3. 고정 `dev_fast_panel_v1` 20건에서 Gemma를 한 arm만 호출한다.
4. control 대비 다음을 기록한다.
   - V cell 변화율과 per-item 변화
   - positive recall/precision/F1, TP/FP/FN 변화
   - parse error, evidence validity, input/output token, wall time
   - positive로 바뀌거나 사라진 각 cell의 gold/문구/evidence 상태

## D0b 승격 gate

아래를 **모두** 만족할 때만 seed 2개를 추가한다.

- 480 V cells 가운데 서로 다른 label이 24개(5%) 이상이다.
- parse error 0, non-absence evidence validity가 control 대비 하락하지 않는다.
- treatment macro-F1이 control보다 0.02 이상 낮지 않다.

미달이면 stochastic ensemble은 실질적인 독립 판단자가 아니거나 안전하지 않으므로
종료한다. D0b는 `temperature=0.2`에서 seed만 다른 두 run을 추가하고, OR/majority/
unanimous 결합의 dev 결과를 **진단용으로만** 계산한다. fast panel의 최선 vote를
submission 또는 dev-200 정책으로 승격하지 않는다.

## D1 이후의 엄격한 조건

D0b 후에는 vote 방식 하나를 label 논리로 사전 고정하고 독립 holdout에서 재현해야
한다. holdout에서도 control 대비 macro-F1 및 positive recall이 모두 개선되고, 3회
runtime projection이 2시간 이내일 때만 dev-200을 고려한다. evidence는 선택된 positive
sample의 unchanged source substring만 채택하며, vote로 label만 바꾸고 evidence를
추정하지 않는다.

## 제외

- temperature 탐색을 dev F1에 맞춰 반복하지 않는다.
- top-p/top-k/repetition penalty를 동시에 바꾸지 않는다.
- dev error별 vote threshold 또는 v별 merge rule을 만들지 않는다.
- Luna/teacher를 사용하지 않는다.
