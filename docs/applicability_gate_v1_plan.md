# Applicability gate v1 — complete-fact 단일 호출의 안전한 출력 축소 후보

작성일: 2026-09-09 (dev / mac)

## 질문

모든 판정 사실을 넣어도 Gemma가 24개 법적 쟁점을 동시에 다루면서 놓친다면, **법적으로
명백히 성립 불가능한 항목만** 모델 출력 대상에서 제외하고 나머지를 complete-source 단일
V/E 호출로 맡기는 것이 도움이 되는가?

이는 4,000자 절단, 새 법령 RAG, dev 오류 기반 규칙, 문서 선택, Python 위반 탐지가 아니다.
각 제외는 card의 1 조건을 organizer metadata 또는 organizer CSV가 명시적으로 부정할 때만
일어난다. Python은 그 항목을 0으로 조립할 뿐, 원문에서 제한·예외·위반을 찾지 않는다.

## v1에 포함하는 좁은 registry

| Reason | 제외 항목 | 명시적 사실 | card 근거 |
| --- | --- | --- | --- |
| `exact_noncompetition` | v10, v11, v13 | metadata 상세품명 코드가 있고 exact 경쟁제품 CSV에 매칭되지 않음 | 각 카드의 ‘비경쟁제품·적용 불명 = 0’ |
| `below_100m` | v15, v16 | `입찰추정가격`이 정수로 1억원 미만 | 각 카드의 ‘1억원 이상’ 전제 |
| `at_least_100m` | v17, v18 | `입찰추정가격`이 정수로 1억원 이상 | 각 카드의 ‘1억원 미만’ 전제 |
| `explicit_non_negotiated` | v22 | `낙찰방법`이 organizer schema의 명시적 비협상 값 | ‘협상계약’ 전제 |
| `national_or_explicit_non_negotiated` | v23 | 국가계약이거나 지방계약 + 명시적 비협상 낙찰방법 | ‘지방계약 협상계약’ 전제 |

누락·새 enum·비정형 가격·unknown product status는 **절대 제외하지 않는다**. 경쟁제품임을
근거로 일반제품 항목(v12, v14–v18)을 제외하는 shortcut과, 지방 소액수의가 아니라고
v6–v8을 제외하는 shortcut은 dev positive coverage에서 반례가 나왔으므로 v1에서 금지한다.

## 먼저 해야 할 검증

`scripts/audit_applicability_gate_v1.py`는 prompt/API 호출 없이 다음을 남긴다.

1. registry와 card source trace
2. notice별로 줄어드는 active item 수
3. label을 **gate 정의 뒤에만** 읽어, gated-out gold positive가 0인지 확인

하나라도 gated-out positive가 있으면 registry를 dev label에 맞춰 고치지 않고 해당 reason을
후보에서 제거한다. 0이면 이것은 quality 증명이 아니라 다음 paid ablation의 admission
조건일 뿐이다.

## 유료 ablation 계약 — audit 통과 후에만

base는 EXP154 complete-source one-stage다. 허용 변화는 `applicability_gate.mode` 하나다.
각 notice에서 active v만 가진 동일 card subset, 동일 human-readable metadata, exact product
fact, 모든 supplied source, 동일 V/E schema를 한 번 또는 exact-token overflow pack으로
보낸다. 제외된 v는 source-traced 0/null로 조립한다. frozen EXP123 v2/v3/v21 postprocess는
그 뒤 동일하게 적용한다.

유료 전에는 active subset의 semantic-input contract, short/attachment/overflow rendered
messages, complete-source admission, mock parser/assembly를 다시 검토한다. EXP154와 fast20,
독립 holdout을 모두 비교하며, dev-200 확장은 둘 다 방향성이 확인될 때만 허용한다.

## EXP163 유료 전 admission 결과

`configs/config.exp163-complete-source-safe-applicability-fast-panel.yaml`은 EXP154에서
`applicability_gate.mode: off → safe_v1`만 바꾼 config다. `preflight_experiment.py`가 그
차이 하나만 확인했다.

- Gate coverage: `outputs/applicability-gate-v1-dev200.json`에서 857 item/notice pair가
  source-traced 0으로 제외됐고, dev-200 gold positive gated-out count는 **0**이다. 이
  label 확인은 registry를 만든 뒤의 coverage 검증일 뿐 gate 조건을 바꾸는 데 쓰지 않았다.
- Exact rendered fixture: `outputs/exp163-prompt-review/`의 PPS-DEV-01 (short), 03
  (attachment), 143 (overflow)을 읽었다. 세 request는 각 22 active items를 가지며
  schema·system card·output keys가 일치한다. 제외 사유는 companion request JSON의
  `applicability_inactive_items`에만 audit metadata로 남고 모델 메시지에는 노출되지 않는다.
- Dynamic semantic contract: `outputs/exp163-semantic-contract-audit-v2/` PASS. fixture의
  active item 수는 모두 22이며, gated items에는 card를 요구하지 않고 remaining items의
  card/metadata/CSV/source span을 검사한다.
- Full-population exact admission: `outputs/exp163-complete-fact-admission-dev200-v2.json`
  PASS — supplied source 374/374, 21 metadata fields, active card, product fact, budget
  exceedance 모두 0. dynamic subset 때문에 pass distribution은 1:194, 2:5, 3:1이다.
- Mock fast20: 20/20 rows, parser/CSV validation errors 0.

따라서 다음 OpenRouter fast20은 complete-source baseline EXP154와 **gate 하나만 다른**
유효한 quality ablation이다. provider partial/402 output은 점수로 쓰지 않는다.

## EXP163 실행 결과 — 무효

2026-09-09 OpenRouter fast20은 20건 중 11건만 response를 받고 나머지 9건은 동일한
`HTTP 402: This request would exceed your available credits given your current in-flight requests`
로 두 retry 모두 실패했다. runner가 partial checkpoint에 빠진 행을 0으로 채울 수 있으므로
이 artifact의 macro-F1·per-item metric은 **계산하거나 비교하지 않는다**. config는
`lifecycle: invalidated`로 전환했다.

이는 EXP160–162의 source-first/full-final 실패와 같은 현재 provider credit/reservation
제약이다. EXP163은 one-stage 20-call 후보라 architecture의 quality나 runtime 실패를
보여주는 결과가 아니다. 새 remote retry는 하지 않으며, credit이 안정화되거나 local vLLM
environment가 준비될 때에만 동일 config를 새 ID·fresh output으로 다시 gate한다.

## EXP164 재시도 전 검토 (2026-09-09)

사용자 확인으로 provider credit이 복구된 뒤, EXP163의 partial output은 재사용하지 않고
새 ID `exp-164-complete-source-safe-applicability-fast-panel`로 다시 시작한다. quality
policy는 EXP154 + `safe_v1` gate로 동일하며, `run.concurrency: 8`만 provider의 in-flight
reservation을 낮추기 위한 **명시적 scheduling 차이**다.

- Preflight: base EXP154 대비 `applicability_gate.mode: off → safe_v1` 및
  `run.concurrency: 20 → 8`만 확인했다.
- Mock: fast panel 20/20, parser·CSV 오류 0.
- Exact admission: `outputs/exp164-complete-fact-admission-dev200-v1.json` PASS.
  source 374/374, required metadata 21/21, active-card omission 0, over-budget pack 0,
  pass distribution 1:194 / 2:5 / 3:1.
- Semantic contract: `outputs/exp164-semantic-contract-audit-v1/` PASS. PPS-DEV-01,
  PPS-DEV-03, PPS-DEV-143에서 active cards, item-specific metadata/CSV fact, source spans를
  확인했다.
- Human rendered-message review: `outputs/exp164-prompt-review/`의 같은 세 공고를 읽었다.
  각각 22 active item이며, 0으로 assembly되는 v17/v18 또는 v15/v16의 gate reason은 audit
  JSON에만 있고 LLM에 전달되지 않는다. 모든 실제 공고문·첨부 문서는 user message에 포함된다.

위 검토를 충족한 상태에서만 EXP164 remote fast-20을 실행한다. 20/20 완결 응답이 아니면
metric을 사용하지 않고 다시 invalidated로 기록한다.
