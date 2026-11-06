# EXP164 결과 및 EXP165/166 독립 holdout 계획

작성일: 2026-09-09 (dev / mac)

## EXP164: 완결 fast-20

EXP164는 EXP154의 32k complete-fact one-stage V/E policy에서, organizer metadata/CSV가
명시적으로 항목의 적용 전제를 부정한 경우만 0/null로 조립하는 `safe_v1` gate를 추가했다.
원문에서 위반·예외를 찾거나, 제품 코드를 추론하거나, dev label로 threshold를 조정하지 않는다.

사전 검증은 `docs/applicability_gate_v1_plan.md`에 남겼다. 특히 full dev-200 exact
admission은 source 374/374, required metadata 21/21, active-card omission 0, over-budget 0을
확인했고 mock은 fast20 20/20이었다.

| arm | macro positive-F1 | calls | runtime | total tokens | errors |
| --- | ---: | ---: | ---: | ---: | ---: |
| EXP154 no gate (earlier run) | 0.241667 | 22 | 40.5 s | 350,850 | 0 |
| EXP164 safe_v1 | **0.258333** | 22 | 47.8 s | 343,302 | 0 |

EXP164은 20/20 response로 끝났으며 `errors.csv`에는 evaluation mismatch만 있고 provider,
JSON parser, CSV validation error는 없다. 70개 gated fast-panel pair는 모두 gold 0이었다.
EXP154 output에서는 그 70개 중 4개가 FP(v13 1개, v15 1개, v23 2개)였고 EXP164은 모두
0으로 조립했다.

그러나 fast panel은 작고, OpenRouter 동일 decoder 설정도 raw response가 완전히 고정되지
않는다. 실제 macro 변화에는 gate가 건드릴 수 없는 v12 +1.0 및 v19 -0.667도 섞였다. 따라서
EXP164 단독의 +0.016667을 gate의 인과 효과나 canonical/submission 승격 근거로 해석하지
않는다.

## 다음 검증: 고정 독립 holdout의 동시대 쌍

`configs/dev_prompt_holdout_v1.json`은 fast panel/결과와 독립적으로 고정된 20건이다. card,
source document, friendly metadata/CSV, 32k token admission, output V/E, decoder, frozen rule,
concurrency를 완전히 고정하고 다음 두 arm을 실행한다.

| config | gate | 역할 |
| --- | --- | --- |
| `config.exp165-complete-source-no-gate-holdout.yaml` | off | 동시대 control |
| `config.exp166-complete-source-safe-applicability-holdout.yaml` | safe_v1 | 처리군 |

두 config는 EXP164를 base로 한다. cohort/output은 preflight policy 비교에서 제외되는
evaluation routing이고, EXP165의 유일한 policy change는 `safe_v1 → off`다. 새 card, source
selection, prompt, LLM, Python positive rule, merge를 추가하지 않는다.

각 arm에는 유료 호출 전에 preflight, mock, full holdout exact-admission, semantic contract,
그리고 short/attachment/overflow rendered-message human review를 적용한다. 한 arm이라도
20/20 response가 아니면 그 쌍은 비교하지 않는다. 결과는 macro positive-F1뿐 아니라
gate 대상의 gold-positive coverage, paired FP/TP/FN transition, calls, prompt/completion tokens,
parser/evidence 오류를 함께 기록한다.

safe_v1가 fast와 holdout 모두에서 control 대비 macro 및 gated FP를 개선하고, gold-positive
gate coverage가 0이며 runtime 증가가 없을 때에만 dev-200 후보가 된다. 반대면 gate는
reject하고 complete-fact source policy의 다른 대형 탐색으로 돌아간다.

## EXP165/166 유료 전 검토 (2026-09-09)

- Preflight: EXP165는 EXP164 대비 `applicability_gate.mode: safe_v1 → off`만,
  EXP166은 policy difference 0을 확인했다. 두 arm의 cohort는 같은 frozen
  `dev_prompt_holdout_v1`이다.
- Full dev-200 exact-admission: no-gate EXP165도 PASS — source 374/374, metadata 21/21,
  active card omission 0, over-budget 0, pass 1:193 / 2:6 / 3:1. EXP166은 EXP164와 같은
  dynamic safe-gate policy로 이미 같은 full-population audit PASS를 받았다.
- Semantic contract: `outputs/exp165-semantic-contract-audit-v1/` 및
  `outputs/exp166-semantic-contract-audit-v1/` 모두 PASS. holdout의 short PPS-DEV-094,
  attachment PPS-DEV-046, overflow PPS-DEV-082를 검사했다.
- Rendered-message review: `outputs/exp165-prompt-review/`,
  `outputs/exp166-prompt-review/`를 읽었다. control은 세 공고 모두 card 24개, 처리군은
  17/20/17 active cards이며 gate 사유는 companion audit JSON에만 있다. metadata와 실제
  source document sections는 두 arm에 모두 남고, 처리군에는 active item의 card/output key만
  남는다.
- Mock: 두 arm 모두 20/20, parse·CSV validation error 0. Regression suite 144 passed.

이제 policy, fixture, parser, source completeness가 모두 고정됐으므로 EXP165를 먼저
완결 실행하고, 이어 EXP166을 같은 조건으로 완결 실행한다.

## EXP165/166 holdout 결과 — gate reject

두 arm 모두 20/20 response와 valid submission CSV를 만들었다. provider/JSON parser/CSV
validation failure는 없었다.

| arm | macro positive-F1 | calls | runtime | prompt / completion tokens | cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| EXP165 control (`off`) | 0.125000 | 22 | 46.2 s | 322,969 / 13,945 | $0.03555 |
| EXP166 treatment (`safe_v1`) | 0.125000 | 22 | 65.7 s | 312,618 / 17,122 | $0.03770 |

처리군은 control의 명시적으로 부적용인 FP를 실제로 제거했다: v13 두 건, v23 세 건,
v22 한 건이다. 그러나 gate가 소유하지 않는 active model output에서 v17 FP가 하나 새로
생겼고, 동일 cohort의 다른 non-gated label 변화도 있었다. positive-class F1은 v8/v13/
v17/v22/v23에서 모두 0으로 남거나 변화가 상쇄되어 macro는 동일하다. 따라서 fast의
상승과 holdout의 무변화는 `safe_v1`을 dev-200 혹은 submission으로 승격할 증거가 아니다.
gate registry는 source-traced safety utility로 보존하되 candidate policy에서는 **off**를
유지한다.

### Remote decoder observability 경고

두 response에서 OpenRouter usage가 request의 `max_tokens: 1536`보다 큰 completion을
보고했다: control PPS-DEV-27=1,583, treatment PPS-DEV-27=1,613 및 PPS-DEV-050=4,599.
adapter가 request payload에 `max_tokens`와 `provider.require_parameters: true`를 보냈고,
raw JSON은 schema-valid/`finish_reason: stop`이었다. 따라서 local measurement를 고쳐
쓸 근거는 없지만, remote usage·wall time은 vLLM 제출 runtime의 정확한 proxy가 아니다.
이 결과는 같은 remote arm끼리의 관측값으로만 사용하고, staged submission runtime은
대회 vLLM 환경에서 별도 검증해야 한다.

**결정:** EXP165/166 이후 safe-applicability branch를 종료한다. 다음 넓은 후보는 이미
complete-source admission과 mock을 갖추었으나 credit 문제로 quality를 전혀 측정하지 못한
source-first/full-final architecture다. 새 ID에서 다시 사전검토하고, 기존 EXP160–162의
partial output은 사용하지 않는다.
