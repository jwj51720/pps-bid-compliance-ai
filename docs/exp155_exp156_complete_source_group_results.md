# EXP155·EXP156 — 32k complete-source item partition fast-20 결과

작성일: 2026-09-09 (dev / mac)

## 공통 불변 조건

두 실험은 EXP154의 complete-fact input을 유지했다. 즉 card v6, human-readable organizer
metadata, friendly exact competition-product fact, 모든 supplied notice source, 32k exact
token admission, V/E schema, absence AND, frozen v2/v3/v21 rule, model/decoder는 같다.
각 group은 모든 source를 독립적으로 읽고, final row는 disjoint item ownership으로
concatenate한다. source document를 group마다 선택·삭제하거나 labels를 보고 membership을
정하지 않았다.

## EXP155: 기존 19+5 document-restrictions partition

`document_restrictions_two_way_v1`은 G01 19개 remainder와 G02
`v6/v7/v8/v9/v19`를 나눈다. group semantic contract audit 24/24, exact input review,
mock, preflight를 통과했다.

| 항목 | 값 |
| --- | ---: |
| fast20 macro positive-F1 | 0.237500 |
| calls | 42 (G01 22, G02 20) |
| prompt/completion tokens | 581,541 / 18,155 |
| aggregate cost | 0.062853 |

EXP154 0.241667보다 낮다. v8/v12/v19 일부 FN은 회복했으나 v8/v17/v19/v23 FP가 증가했다.
따라서 이 19+5 split은 확장하지 않는다.

## EXP156: truth-condition family 14+10 partition

EXP155 error row를 보고 만든 조정이 아니다. G01은 qualification/document/procedure/
consistency (`v1–v9`, `v19`, `v21–v24`), G02는 exact-product/whole-notice absence
(`v10–v18`, `v20`)다. G02만 absence AND를 사용한다. audit, mock, preflight 및 72
regression tests를 통과했다.

| 항목 | 값 |
| --- | ---: |
| fast20 macro positive-F1 | 0.213889 |
| wall time | 45.67초 |
| calls | 40 (각 group 20) |
| prompt/completion/total tokens | 563,882 / 15,844 / 579,726 |
| aggregate cost | 0.060657 |

v8의 TP는 맞았지만 v13/v15/v17 및 v19/v23 FP가 증가했고, v4/v6/v7/v9/v10/v11/v14/
v16/v18/v20/v22/v24의 FN은 여전히 남았다. EXP154보다 `-0.027778`이다.

## 결정

두 종류의 disjoint two-way partition이 모두 complete-source one-stage보다 낮았다. 따라서
이 시점에서 v membership을 더 잘게 바꾸거나 dev error 기반으로 재배치하지 않는다.
이는 4k clipping을 복구하라는 결론도 아니다. 다음 architecture는 all-source admission을
유지하면서, source에서 추출한 사실을 24-item final task에 전달하는 **표현과 역할 분리**를
바꿔야 한다. EXP153의 pack×24 excerpt inventory는 gold positive evidence coverage 15.8%
로 이미 종료됐으므로 그대로 재실행하지 않는다.
