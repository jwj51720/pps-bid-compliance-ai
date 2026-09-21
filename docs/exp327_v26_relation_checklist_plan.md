# EXP327 — v26 완결 카드 + one-stage 관계 체크리스트

작성: 2026-09-18, dev / mac

## 가설

EXP323의 v26 one-stage V/E는 fast20 `.198611`이었다. 카드 기준과 원문은 전달됐지만 18개
항목에서 positive recall이 0이었다. EXP205/206/208은 기존 v10 입력에서 원문 뒤 짧은 관계
체크리스트 하나만 추가해 matched direct control을 fast `+.085317`, holdout `+.069444`,
dev200 `+.035502` 이겼다. Python 후처리를 제거한 저장 model output만 다시 계산해도 dev200
direct `.187695` 대비 checklist `.219569`로 방향이 유지된다.

가설은 v26의 긴 기준을 더 늘리는 것이 아니라, 모델이 원문을 읽은 직후 적용대상·실제
참가조건·수치/날짜 역할·예외·부재범위를 짧게 재대조하게 하면 완결 정보가 final V/E에 더
잘 반영된다는 것이다.

## 변경 통제

- base: `configs/config.exp323-v26-ve-fast-panel-c4.yaml`.
- sole allowed change: `prompt.mode: baseline -> relation_checklist_after_source_v1`.
- v26 card, metadata/product renderer, all-document admission, V/E schema, merge, provider,
  active items와 `frozen_rule_set: null`은 고정한다.
- 한 호출 안의 마지막 지시만 추가한다. stage, V-only, grouping, RAG, Python label rule은 없다.

## gates와 승격

paid 전 preflight, dev200 exact tokenizer coverage, 062/194/143 rendered semantic contract,
exact fast20 mock와 49열/evidence validation을 통과해야 한다.

fast20에서 EXP323 `.198611`보다 macro F1과 positive recall이 개선되고 치명적 FP가 늘지 않을
때만 policy-identical independent holdout20을 실행한다. holdout에서도 direct v26 control과
같은 방향을 확인한 뒤에만 dev200으로 확장한다. fast에서 실패하면 v26 checklist wording을
튜닝하지 않는다.

## Fast20 결과

EXP327은 `.263194`로 direct v26 EXP323 `.198611`보다 `+.064583` 높았다. provider call은
27개, runtime 108.5초, prompt/completion tokens는 `533,513 / 20,713`이다. 한 record의
empty-content transport 실패는 configured retry에서 회복됐고 최종 record 누락은 없다.

이 결과는 fast 승격 gate를 통과한다. EXP328 direct와 EXP329 checklist를 같은 independent
holdout20에서 함께 실행해 cohort-matched delta를 확인한다.

## Holdout20 결과와 결정

- EXP328 direct v26: `.1666666667`, runtime 200.2초, 23 calls.
- EXP329 checklist: `.0833333333`, runtime 271.0초, 24 calls.
- delta: `-.0833333334`.

checklist는 direct가 맞춘 v1·v2 양성을 잃었고 새 true positive를 만들지 못했으며
v17·v19·v24 false positive를 추가했다. fast의 `+.064583`은 independent holdout에서 반전됐다.
따라서 dev200으로 확장하지 않고 checklist wording 재조정도 하지 않는다.
