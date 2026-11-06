# EXP-C005H / C005HR v19 holdout 결과

실행일: 2026-09-21  
결론: **방향 개선, completeness gate 실패 — dev200 보류**

## C005H label 결과

- output: `outputs/clean-exp-c005h-v19-requirement-holdout-v2/holdout20/`
- candidate calls: 18
- OpenRouter wall time: 37.405초
- prompt/completion tokens: `53,172 / 8,933`
- v19 TP/FP/FN: C004S `0/1/0` → C005H `0/0/0`
- holdout Macro는 positive가 없는 v19의 metric 정의상 `.430556`으로 동일
- non-v19 changed cells: 0
- v19 positive without evidence: 0

독립 holdout에서 기존 FP `PPS-DEV-050`을 제거했으므로 specificity 방향은 fast와 일치한다.
그러나 `PPS-DEV-192__p01` 한 건이 `finish_reason=length`여서 invalid 1, run status
`INCOMPLETE`다.

## C005HR exact retry

- output: `outputs/clean-exp-c005hr-v19-holdout-recovery-v1/`
- exact task hash: MATCH
- target: `PPS-DEV-192__p01` only
- normal responses re-called: 0
- recovery calls: 1
- result: 다시 `finish_reason=length`, 1,536 completion tokens

두 attempt 모두 observation의 첫 6개 field를 출력한 뒤 whitespace loop에 들어갔다. Non-space
tail은 `quoted_text` value 직후에서 끝나며 나머지 세 field와 JSON closing braces가 없다.
따라서 완성 JSON 뒤 trailing whitespace를 제거하는 문제가 아니고, 누락 field를 Python default로
채울 수도 없다.

## 판정

Fast v19 F1 `1.0`과 holdout FP `1→0`은 구조 가설을 지지한다. 하지만 predeclared invalid=0
gate를 충족하지 못했으므로 현재 manifest로 dev200을 실행하지 않는다. 반복 exact retry는 같은
deterministic failure를 재현했으므로 추가 실행하지 않는다.

허용 가능한 다음 최소 진단은 semantic contract를 전혀 바꾸지 않고 JSON key/enum 표현만
축약한 serialization-only target probe다. 성공해도 먼저 stored holdout responses와 결합해
invalid 0 및 동일 label 방향을 검증한 뒤에만 dev200을 고려한다.
