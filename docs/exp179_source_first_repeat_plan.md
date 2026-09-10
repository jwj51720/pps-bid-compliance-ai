# EXP179 — source-first/full-final repeat fast-20

작성일: 2026-09-10 (dev / mac)

## 목적

EXP171(source-first/full-final dev-200)과 EXP172(capacity-matched one-stage
control)의 차이는 `+0.048681` macro F1이었다. 동시에 OpenRouter는 temperature 0과
seed 고정에도 provider path별 label 변동 및 completion cap non-parity를 보인 적이 있다.
따라서 새 architecture를 추가하기 전에 EXP167의 **정확히 같은** fast20 policy를 새 remote
request로 한 번 반복해 source-first gain의 관측 안정성을 확인한다.

이 run은 source-first를 submission default로 승격하는 실험이 아니다. full vLLM runtime과
evidence warning이 여전히 미해결이므로, 결과가 좋아도 submission package는 바꾸지 않는다.

## 단일 허용 변경

`configs/config.exp179-source-first-full-final-repeat-fast-panel-c4.yaml`은 EXP167을 base로 하며
`output.dir`만 다르다. 다음은 동일하다.

- 32k exact-token source admission, ordered overflow packing, cards v6, 21 readable metadata
  fields, friendly organizer product fact
- `fact_inventory_full_final_v1`: non-final raw source fact navigation → full-source final V/E
- V/E schema, evidence resolver, absence/non-absence merge, EXP123 frozen postprocess
- model/provider/temperature=0/seed/max_tokens=2500/retry/concurrency=4
- fast cohort, source selection, active 24 items

raw law/case RAG, new rule, item grouping, prompt copy, decoder change, Python label correction은
추가하지 않는다.

## 유료 전 gate

1. `preflight_experiment.py`가 base 대비 output path 외 policy diff가 없다고 확인한다.
2. EXP167의 exact staged rendered review를 재사용한다. `outputs/exp-167-source-first-full-final-fast-panel-c4-mock/staged_input_examples.md`의 PPS-DEV-062(짧음), PPS-DEV-169(첨부+overflow), PPS-DEV-01(다중 사실)은 policy-identical이므로 동일하다.
3. 새 config 자체로 mock fast20을 실행해 parser/CSV/output 경로를 재검증한다.
4. local regression suite 및 source coverage/profile artifact의 conclusion은 EXP167과 동일하다:
   final source omission 0이며 navigation null은 final 0이 아니다.

## 판정 기준

- 필수: 20/20 completion, parser/CSV error 0, final recovery 0, source omission 0.
- 관측: macro F1, P/R/F1 per item, changed-cell agreement with EXP167, prompt/completion token,
  evidence warnings.
- EXP167 fast20 `0.286111`에서 큰 폭으로 하락하면, EXP171의 dev200 이득을 단일 remote
  관측으로만 취급하고 새 source-first topology에 돈을 더 쓰지 않는다.
- 비슷한 범위면 source-first v1의 repeatability evidence로 기록한다. 다음 architecture는
  별도 one-variable fast20 후보로만 진행한다.

## 유료 전 gate 결과

- Preflight: base EXP167 대비 controlled difference 없음. output directory는 preflight의
  effective policy 비교 대상이 아니며, policy field 변경은 없었다.
- Mock fast20: 20/20 completion, parser/CSV validation PASS.
- Regression: `144 passed`.
- Semantic-input contract: 24/24 PASS. 새로 export/read한 exact final messages는 ignored
  `outputs/exp179-semantic-contract-audit-v1/rendered_inputs/`의 PPS-DEV-01(짧음),
  062(첨부), 169(overflow)에 있다.
- Historical EXP167 raw prediction artifact와 current EXP179 artifact를 직접 대조했다.
  20/20 record의 Stage-1 input message는 byte-for-byte 동일했다. Final의 static
  system/card/metadata/source portion은 19/20 동일했다. PPS-DEV-169의 한 건은
  Stage-1 navigation 생성 길이가 달라 final exact-token pack boundary가 달라졌으며,
  이는 policy drift가 아니라 source-first design의 intended dynamic admission이다.

## EXP179 remote fast-20 결과

EXP179은 20/20 complete, parser error 0, final recovery 0, CSV validation PASS로
완료됐다.

| policy | macro F1 | wall time | evidence validity | validation warnings |
| --- | ---: | ---: | ---: | ---: |
| EXP167 source-first v1 | 0.286111 | 165.0 s | .7000 | 6 |
| **EXP179 source-first v1 repeat** | **0.287500** | **263.4 s** | **.8571** | **3** |

두 run 사이 label은 480 cell 중 7개만 달랐다. 따라서 fixed temperature/seed에서도
완전한 bit-level 결정성은 아니지만, macro F1은 `+0.001389` 차이로 사실상 같은 범위였다.
이 repeat은 EXP167의 fast signal을 지지한다. 다만 같은 run에서 OpenRouter가 configured
`max_tokens=2500`보다 큰 completion usage를 3건(최대 3,791) 보고했으므로, remote wall
time과 usage는 submission vLLM runtime/cap의 근거가 될 수 없다.

이 결과는 source-first v1을 complete-source branch의 반복 관측 incumbent로 유지하지만,
fast panel 반복일 뿐 independent holdout/dev200 재실행이나 submission promotion을 뜻하지
않는다. 다음 candidate는 navigation의 count/position/taxonomy 재조정이 아니라 완전히 다른
semantic operation이어야 한다.
