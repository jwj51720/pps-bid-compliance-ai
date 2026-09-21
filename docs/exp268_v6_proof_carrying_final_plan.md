# EXP268 — v6 proof-carrying one-call final

작성: 2026-09-15, dev / mac

## 확인된 실패와 가설

EXP264–266에서 corrected v6 card를 쓴 V/E와 V-only가 모두 fast20의 유일한 v6 양성
`PPS-DEV-072`를 놓쳤다. EXP267은 별도 source-only pass에서 이 공고의 본점 소재지
참가자격과 계약방식을 정확히 발췌했지만, full-source final이 그 발췌와 같은 원문을 다시
인용하면서도 v6=0을 냈다. 따라서 입력·탐색·evidence 부담이 아니라, 최종 응답에서 금액
적용범위·지역문구 역할·기초지역 단위·계약절차 예외를 끝까지 결합하지 않는 것이 최소
확인 병목이다.

가설은 v6-only 단일 호출의 응답에서 아래 observable proof를 판정보다 먼저 의무화하면,
Gemma가 이미 읽은 사실을 카드의 truth condition과 연결할 수 있다는 것이다.

- 적용 금액 구간: 고시금액 미만/이상/불명
- 지역 참가자격의 변경 없는 원문
- 해당 문구의 역할: 참가자격/현장·납품지/기타/없음/불명
- 참가 허용범위에 시·군·구급 기초지역이 포함되는지
- 계약절차: 제한경쟁/2인 이상 견적 수의/기타/불명
- 시·군·구 제한 허용요건: 충족/불충족/불명
- 카드 대조: 1조건충족/0조건충족/판단불가

이 필드는 관찰 기록이고 Python은 어떤 조합도 label로 변환하거나 override하지 않는다.
같은 JSON의 `판정.v6`가 유일한 최종 V/E 소유자다.

## 통제 정책

- base: `configs/config.exp265-v6-threshold-ve-fast-panel-c4.yaml`.
- allowed policy change: `prompt.mode` 하나.
- active item v6, corrected card v17, V/E, human-readable metadata, organizer semantics,
  product fact, 모든 admitted original source, exact tokenizer admission, merge, frozen
  postprocess와 provider parameters는 고정한다.
- Stage 1, 반복 판정, voting/OR/AND, raw law, Python 지역·금액·법률 rule을 쓰지 않는다.
- proof의 원문 필드는 source substring 검증 결과를 diagnostics에 남기되, 검증 실패도
  Python label 변경 사유가 아니다. 기존 e6 validator와 500자 계약은 그대로다.

## 유료 전 gate

1. schema/parser가 필드 enum과 atomic `판정.v6`를 강제하고 malformed는 기존 pass recovery로
   처리하는지 test한다.
2. preflight가 `prompt.mode` 하나만 보고해야 한다.
3. exact dev200 admission에서 cards/metadata/semantics/source omission 0과 call topology를
   기록한다.
4. short `PPS-DEV-062`, attachment `PPS-DEV-194`, overflow `PPS-DEV-169`, positive
   `PPS-DEV-072`의 actual rendered system/user messages를 읽고 active-v6 semantic contract를
   감사한다.
5. exact mock 20/20과 49-column/evidence validation을 통과한다.

## 승격 기준

fast20에서 EXP265의 v6 `TP 0 / FP 0 / FN 1`보다 F1을 개선하고 parse/source failure가
없어야 independent holdout20으로 간다. holdout에는 v6 positive가 없으므로 EXP265와 동일한
policy의 matched control과 비교해 FP가 늘지 않아야 dev200으로 확장한다. fast 실패 시 proof
wording이나 enum을 같은 표본에 맞춰 반복 수정하지 않는다. 이 실험은 local-quality probe이며,
성공해도 all-item base에 통합하거나 submission topology로 승격하려면 별도 실험이 필요하다.

## Pre-provider gate (2026-09-15)

- preflight는 EXP265 대비 `prompt.mode: baseline -> v6_geography_proof_v1` 하나만
  검출했다.
- exact-token dev200 audit는 200 records, 374/374 source documents, source/metadata/card/
  organizer-semantics omission 0, over-budget pack 0이다. pass 분포는 `199×1 + 1×2`, 총
  201 calls다. fast20은 전부 one-pass로 20 calls다.
- short `PPS-DEV-062`, attachment `PPS-DEV-194`, overflow `PPS-DEV-169`, positive
  `PPS-DEV-072`의 actual rendered system/user message를 읽었다. 네 message 모두 corrected
  v6 card, 필요한 human-readable metadata, organizer anonymization semantics와 모든 admitted
  원문을 유지하며, proof 지시는 원문 뒤에 위치한다.
- active-v6 semantic-input contract는 네 fixture에서 각각 1/1 통과했다.
- exact mock output:
  `outputs/exp-268-v6-geography-proof-fast-panel-c4-mock/`. 20/20 완료, proof payload가
  parse error 없이 diagnostics에 직렬화됐고 49-column/evidence validation이 통과했다.
- 최초 mock에서 새 nested schema를 기존 `MockClient`가 인식하지 못해 recovery로 떨어지는
  사전검증 결함을 발견했다. provider 실행 전에 v6 proof mock payload 지원과 regression test를
  추가하고 exact mock을 다시 실행해 parse error 0을 확인했다. 이 변경은 provider transport,
  prompt, label logic을 바꾸지 않는다.
- full tests: `.venv/bin/python -m pytest -q` → `234 passed`.

따라서 구현·입력·provenance·render·mock gate가 모두 충족됐고 fast20 provider 실행만
승인한다.

## Fast20 result and decision (2026-09-15)

- output: `outputs/exp-268-v6-geography-proof-fast-panel-c4/`.
- 20 calls, 23.113 seconds; prompt/completion `269,955/3,858` tokens; cost $0.02501175;
  parse errors 0.
- v6는 EXP265 `TP 0 / FP 0 / FN 1`에서 `TP 0 / FP 6 / FN 1`로 악화했다. F1은
  여전히 0이고 evidence validation warning도 4건 생겼다.
- `PPS-DEV-072`의 proof는 `고시금액미만`, `참가자격`, `기초지역참가제한=포함`,
  `계약절차=제한경쟁`, `카드대조=1조건충족`을 정확히 기록하고 source excerpt도 검증됐다.
  그런데 `허용요건=충족`이라고 쓴 뒤 최종 v6=0을 냈다. 관찰과 final의 내부 모순이다.
- 여섯 FP 중 네 건은 proof 자체가 `기초지역참가제한=미포함` 또는 지역문구 없음이라고
  기록했는데도 `카드대조=1조건충족`, v6=1을 냈다. 두 건의 광역 시·도 참가제한도 v6로
  잘못 올렸고 네 positive evidence는 기존 validator를 통과하지 못했다.

따라서 proof schema는 읽은 사실을 노출하는 데 성공했지만 논리 일관성을 강제하지 못했고,
precision을 크게 파괴했다. Python이 proof 조합으로 label을 고치는 것은 금지된 법률 판정
rule이므로 하지 않는다. predeclared fast gate를 실패했으므로 holdout/dev200으로 확장하지
않으며, 이 fast panel에 맞춘 enum/wording 재조정도 하지 않는다. EXP267과 함께 v6의 다음
작업은 추가 호출이 아니라 organizer source에서 허용요건과 v6/v7 경계를 다시 확인하는
offline card audit이어야 한다.
