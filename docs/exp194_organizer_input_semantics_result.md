# EXP194: 주최 측 익명화 표기 의미 전달 결과

작성: 2026-09-11, dev / mac

## 결론

주최 측 README의 익명화 표기 규약이 prompt에 없던 의미 입력 결함을 versioned
`anonymization_v1` context로 복구했다. 기술적 완결성은 dev200 전수 admission audit으로
확인했다.

fast20 macro positive-F1은 EXP169 `.262500`에서 `.256944`로 `.005556` 하락했다.
따라서 이 한 번의 실행으로 canonical이나 holdout으로 승격하지 않는다. 다만 가설 대상
항목에서는 3 cell이 바뀌어 2개가 교정되고 1개가 회귀했다. 반면 가설 비대상 항목에서
11 cell이 변했다. headline 하락의 전부를 표기 규약의 인과 효과로 해석하지 않는다.

## 실행 결과

- config: `configs/config.exp194-organizer-input-semantics-fast-panel-c4.yaml`
- output: `outputs/exp-194-organizer-input-semantics-fast-panel-c4/`
- cohort: `configs/dev_fast_panel_v1.json`, 20건
- call: 23
- runtime: 52.057초
- prompt/completion tokens: 349,007 / 16,436
- parse error: 0
- evidence validity: .9000, validation warning 2건
- paired comparison: `outputs/exp-194-organizer-input-semantics-fast-panel-c4/paired_comparison.json`

## 가설 대상 변화

focus는 익명화된 기관·지역·대조 의미와 직접 관련된 v1, v5–v8, v24로 사전 정의했다.

| 항목 | EXP169 | EXP194 | 변화 |
| --- | --- | --- | --- |
| v1 | 2/0/1, F1 .8000 | 3/0/0, F1 1.0000 | DEV072 FN 교정 |
| v5 | 0/0/1, F1 0 | 0/0/1, F1 0 | 불변 |
| v6 | 0/0/1, F1 0 | 0/0/1, F1 0 | 불변; 기존 card 적용범위가 그대로임 |
| v7 | 0/0/2, F1 0 | 0/0/2, F1 0 | 불변; 기존 card 적용범위가 그대로임 |
| v8 | 0/0/1, F1 0 | 1/1/0, F1 .6667 | DEV042 TP 회복, DEV072 FP 추가 |
| v24 | 0/0/3, F1 0 | 0/0/3, F1 0 | 불변 |

focus changed cell은 3개, corrected 2, regressed 1이다. off-target은 11개,
corrected 6, regressed 5이다. off-target 변동이 focus보다 크므로 1회 실행의 macro 차이만으로
규약을 기각하거나 승격하지 않는다.

## 판정과 후속

- README 의미 누락 수정: 완료
- canonical 성능 정책: 미승격
- holdout20: fast macro gain 미확인으로 보류
- EXP193과의 결합: 아직 미실행. 두 변경의 상호작용을 별도 2×2 해석으로 선언해야 한다.
- 다음: v7 적용범위를 독립 source-audit하고, v6/v7 target 효과를 off-target 호출 변동과
  분리한다.
