# EXP175 source-first navigation position ablation

작성일: 2026-09-10 (dev / mac)

## 근거

EXP171 source-first/full-final은 capacity-matched one-stage EXP172보다 dev200 macro F1이
0.307962 대 0.259281이었다. 반면 facts를 category당 3→4개로 늘린 valid EXP174 fast20은
navigation 중앙 수를 12→15로 높였지만 F1을 0.286111→0.269444로 낮췄다. 따라서 다음
질문은 “더 많은 candidate인가”가 아니라 **같은 navigation이 final reader의 어느 위치에서
주의를 돕는가**다.

## 단일 변경

EXP175는 EXP167 v1과 같은 7개 category·category당 3개 cap·source-only stage 1·complete
source final을 유지한다. v1은 navigation을 원문 뒤의 별도 user message로 붙인다. v3는
동일 navigation을 human-readable metadata 뒤, `[공고 자료 원문]` 앞에 넣는다.

모든 original source 문자열, card v6, product/metadata text, output schema, model/decoder,
exact token packer, merge와 Python postprocess는 고정한다. navigation은 계속 non-final이며
누락이 final 0이 되는 일은 없다.

## 해석

- v3가 v1보다 좋으면 source-first의 이점은 recency보다 사전 orientation/reading order에
  가까울 수 있다.
- v3가 나쁘면 v1의 “원문을 모두 읽은 후 목록으로 재주목시키기”가 핵심 신호일 수 있다.
- 어느 경우에도 fast20 하나만으로 dev200/submission으로 승격하지 않는다. score가 동등
  이상이고 evidence/runtime도 나쁘지 않을 때만 frozen holdout20을 수행한다.

유료 전에는 exact admission 0 omission, semantic contract, short/attachment/overflow
rendered messages, mock, full regression을 다시 통과한다.

## 유료 전 검토

Preflight는 EXP167 대비 `staged_run.mode` 하나만 v1→v3로 바뀐 것을 확인했다. exact
admission은 dev200 source 374/374, metadata 21/21, active card 24/24, over-budget 0,
final pack 1회 186·2회 12·3회 2건이었다. semantic contract은 24/24 PASS다.

`outputs/exp-175-source-first-full-final-v3-fast-panel-c4-mock/staged_input_examples.md`의
PPS-DEV-062/169/01을 읽었다. Stage 1은 raw source-only fact collection이고, final user
message에서는 metadata → non-final navigation → `[공고 자료 원문]` 순서다. 각 actual
source document 문자열은 marker 뒤에 그대로 남고, navigation null은 final 0이 아니다.
mock 20/20 및 full regression 144 passed를 확인했다.

## EXP175 valid fast-20 결과

EXP175는 20/20 complete, stage-1 parse error 0, final recovery 0, CSV validation PASS였다.
Stage-1 23회 + final 24회로 EXP167과 같은 47 calls였고 navigation 중앙값도 12개였다.
따라서 비교는 source scope/candidate cap/call topology가 아닌 final reading order만 다르다.

macro F1은 **0.263889**로 EXP167 v1의 0.286111보다 -0.022222였다. evidence validity는
.765(v1 .700), warning은 4(v1 6)로 개선됐지만 decision quality 하락을 상쇄하지 못했다.
runtime 133.9초(v1 165.0초)와 token 662,128(v1 659,207)은 remote variance를 고려하면
quality 선택 근거가 아니다.

결론: navigation은 metadata와 source 사이가 아니라 **complete source 뒤의 별도 final
message**에 두는 v1 순서를 유지한다. EXP175는 holdout/dev200으로 확대하지 않는다.
