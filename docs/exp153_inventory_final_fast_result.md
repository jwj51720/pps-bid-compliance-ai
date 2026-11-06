# EXP153 — complete-source inventory → final fast-20 결과

작성일: 2026-09-09 (dev / mac)

## 구조

1차는 EXP152와 같은 exact-token complete-source packs를 읽고 v1–v24별 actual
source candidate excerpt 또는 null만 반환한다. label은 반환하지 않는다. 2차는
organizer 4k context와 source-labelled excerpt inventory를 받아 독립적으로 final V/E를
반환한다. inventory null은 final 0이 아니며, Python은 source substring 검증·중복 제거와
absence pack observation summary만 담당한다.

## 검증

- declared `staged_run.mode` one-field diff preflight 통과
- mock 20건 및 59 regression tests 통과
- inventory prompt에서 기존 V/E output contract를 제거하고 fact collection contract만
  남긴 exact rendered message를 검토했다
- inventory parse errors: 0; collected unchanged candidate excerpts: 98

## 결과

| 정책 | fast-20 macro positive-F1 |
| --- | ---: |
| EXP147 input-truthful 4k single | 0.291071 |
| EXP152 complete-fact one-stage | 0.224306 |
| **EXP153 inventory → final** | **0.280556** |

EXP153은 EXP152보다 +0.05625 회복했지만 EXP147보다 -0.01052다. runtime 75.664초,
total tokens 682,723, inventory pack distribution은 EXP152와 같이 1 pass 12, 2 pass 2,
3 pass 2, 5 pass 3, 6 pass 1이다. final evidence validation warning은 4건이다.

## 결론

full source를 one-stage final에 넣는 과적재는 완화됐지만, current broad inventory는
v4/v5/v7/v9/v10/v11/v14/v16/v20/v24의 FN을 회복하지 못했다. 따라서 EXP153은
holdout/dev200/submission으로 확대하지 않는다. 다만 label draft가 아닌
source-preserving inventory라는 구조가 EXP152보다 실질 회복을 냈다는 관측은 남긴다.
다음 수정은 v별 키워드 tuning이 아니라 inventory coverage를 label-blind source scope와
output burden 관점에서 분해한 뒤 결정한다.

## 종료 뒤 source coverage 평가

평가 label을 prompt나 inventory에 사용하지 않고, 종료 뒤에만 inventory의 unchanged
excerpt가 gold positive evidence와 겹치는지 측정했다. gold-positive evidence 38개 중
겹친 것은 6개(15.8%)뿐이었다. v2는 3개 중 2개, v3은 3개 중 3개, v22는 1개 중 1개를
찾았지만, 그 밖의 positive 항목은 0개였다.

따라서 이 결과는 “전문을 읽었으므로 필요한 사실을 수집했다”는 증거가 아니다. 한 pass에서
24개 항목 각각에 excerpt/null을 요구한 출력 부담이 너무 커 핵심 사실을 누락한 것으로
본다. 이 형태의 inventory에 v별 키워드나 dev 사례 보정을 더하는 것은 중단한다. 다음
후보는 source coverage를 먼저 보장할 수 있는 더 작은 사실 단위와 final 판단의 분리를
검증해야 한다.
