# EXP-C004RR v3 keyed recovery 결과

실행일: 2026-09-21

**PASS.** `PPS-DEV-08`, `PPS-DEV-157`의 exact task를 append-only로 각각 한 번 재호출했다.

- task hash: base와 61/61 MATCH
- new attempts: 2
- normal responses replayed: 0
- recovered valid: 2/2
- remaining invalid: 0
- permitted/forbidden cell changes: 0/0
- final score: v3 TP 7 / FP 1 / FN 1 / F1 .875, Macro .8009804827

두 recovery response는 모두 candidate를 `OTHER`, amount null로 구조화해 정상 semantic fallback
0을 유지했다. Recovery는 점수를 바꾸지 않았으며 실행 무결성만 완성했다.

