# N004 v1 bidder-relation fast20 result

작성일: 2026-09-22

결론: **FAIL; holdout/dev200으로 확장하지 않는다.**

고정 `configs/dev_fast_panel_v1.json` 20건에서 TP/FP/FN은 3/1/0,
positive F1은 `0.8571428571`이다. U 0, invalid 0이며 20 logical
calls, prompt 129,931 tokens, completion 550 tokens, remote wall time
22.766초였다.

N003 대비 exact-quote malformed 2건과 raw semantic FP 하나는
사라졌지만, 남은 FP `PPS-DEV-051`에서 모델은
`3억원 이상 대학병원에 납품한 실적`을 과거 납품 상대방이 아니라
현재 입찰자 기관유형으로 판정했다. 응답은 `target=Y, allowed=N`이고
원문 quote도 유효했다. 즉 source coverage, parsing, evidence 문제가
아니라 명시적 관계 제외를 따르지 않은 semantic error다.

fast gate TP=3, FP=0, FN=0, U=0을 충족하지 못했다. 특히 frozen
baseline의 이 panel v1 F1이 1.0이므로 N004는 독립 owner로 승격할
근거가 없다. 같은 문장을 더 강조하는 prompt-only 반복은 중단한다.
다음 후보가 필요하다면 먼저 과거 실적의 `발주처/납품처`와 현재
입찰자 속성 사이 관계를 source-grounded typed fact로 분리하는 것이
기존 truth condition으로 표현 불가능한지 별도 무호출 probe로
입증해야 한다.

근거:

- `outputs/clean-exp-n004-v1-bidder-relation-fast-v1/fast20/run_report.json`
- `outputs/clean-exp-n004-v1-bidder-relation-fast-v1/fast20/observations.json`
- `outputs/clean-exp-n004-v1-bidder-relation-fast-v1/fast20/responses/PPS-DEV-051.json`
