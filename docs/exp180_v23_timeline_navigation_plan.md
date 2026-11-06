# EXP180 — v23 source-timeline navigation 계획

작성일: 2026-09-10 (dev / mac)

## 질문

Current source-first v1은 `일정_설명회` category에 raw source snippets를 모으지만, 각
날짜가 **공고일·현장설명회·제안서 마감·가격입찰 마감 중 무엇인지**를 final task에 명시하지
않는다. v23은 지방 협상계약에서 공고일과 현장설명회/제안서 마감일의 minimum interval을
대조하는 항목이므로, 날짜 문자열 자체뿐 아니라 source-grounded role relation이 필요하다.

이 후보는 law text, example/case retrieval, dev label, 새 numeric threshold, Python final
label rule을 추가하지 않는다. v23 card의 기존 10/20/40일 기준과 final stage의 complete
source/card/metadata는 그대로 유지한다.

## 최소 source-observation operation

기존 `fact_inventory_full_final_v1`에 stage-1b 하나를 조건부로 추가한다.

### Router (Python; 판단 아님)

`적용계약법=지방계약법`이고 `낙찰방법=협상에의한계약`인 notice만 선택한다. 이는 v23
semantic contract의 official applicability fact이며 label/문구/score를 사용하지 않는다.
비적용 notice는 stage-1b 호출도 navigation section도 없고 EXP179와 동일하게 실행된다.

### Stage-1b output (Gemma; source fact only)

각 exact-token source pack에서 다음 다섯 source role별로 0–2개의 **변경 없는 원문
substring**만 반환한다.

- `공고일`
- `현장설명회일시`
- `제안서_접수마감`
- `가격입찰_마감`
- `긴급_재공고_표시`

Gemma는 날짜 차이 계산, 최소일수 적용, 위반/비위반, 증거 확정, metadata 값 복사를 하지
않는다. source에 해당 역할 문구가 없으면 빈 배열이다. parser는 original source substring만
수집·중복제거·document id resolution을 하며, 빈 배열/parse failure가 v23=0이 되지 않는다.

### Final V/E

Stage-2는 EXP179와 같은 cards v6, human-readable metadata, product fact, all admitted source,
V/E schema, merge, evidence resolver, frozen v2/v3/v21 postprocess를 유지한다. 적용 notice에만
아래처럼 사람 친화적인 보조 원문 목록을 추가한다.

```text
[일정 원문 사실 안내 — 최종 판정이나 법령 근거가 아님]
- 공고일: [D0] "..."
- 제안서 접수마감: [D0] "..."
```

Final은 이 목록을 신뢰해 label을 고정하지 않고, complete original source와 card/metadata를
다시 대조한다. Python은 v23 또는 다른 v의 label을 덮어쓰지 않는다.

## label-blind feasibility 결과

이 계획을 만들기 전에 EXP167의 32k exact context builder로 applicability만 계산했다.

| cohort | eligible notices | exact source packs |
| --- | ---: | ---: |
| dev-200 | 41/200 (20.5%) | 41 (각 1 pack) |
| fixed fast20 | 6/20 | 6 |
| supplied test sample 10 | 2/10 | 측정 대상 외 |

따라서 dev200 worst observed topology는 source-first v1의 435 calls에서 최대 476 calls가
된다. 5× document split이나 v group multiplication이 아니다. 실제 evaluation distribution은
unknown이므로, submission runtime은 fast/holdout/dev200 quality gate와 별도의 exact count
projection 없이 주장하지 않는다.

## 비교 계약

Base는 repeatability evidence를 가진 EXP179 source-first/full-final v1이다. declared policy
difference는 `staged_run.mode` 하나다. 새로운 source stage가 해당 notice에만 붙을 뿐,
existing generic source-fact stage와 final policy는 유지한다.

## 유료 전 gate

1. versioned config의 preflight가 mode 하나만 보고하는지 확인한다.
2. short non-applicable, local-negotiated short, local-negotiated attachment/overflow record의
   exact Stage-1a, Stage-1b, final inputs을 markdown으로 export하고 읽는다.
3. semantic-input contract v1의 v23 applicability/1-condition/0-condition/metadata/document
   scope가 final exact message에 모두 존재함을 audit한다. Stage-1b는 final legal contract를
   대체하지 않는다.
4. exact Gemma tokenizer로 full dev200 admission을 검사한다. Stage-1b navigation까지 붙인
   final source omission은 0이어야 한다.
5. mock: ineligible skip, eligible raw source quote, malformed timeline, duplicate quote,
   multiple source packs, final parse recovery, unchanged evidence validation을 test한다.

## fast/holdout/dev200 gate

- Fast20: parser/CSV 20/20, stage-1b malformed 0, source omission 0, final recovery 0이
  필수다. headline뿐 아니라 v23 TP/FP/FN 및 all-item changed-cell ledger를 보존한다.
- Fast의 v23 F1이 EXP179보다 높고 non-v23 global damage가 없을 때만 policy-identical holdout20.
- Holdout도 같은 방향일 때만 dev200. fast-only gain으로 제출·card·canonical policy는 바꾸지
  않는다.
- stage-1b가 actual source role을 일관되게 못 찾거나 F1이 낮으면 날짜 표현/keyword를 dev에
  맞춰 튜닝하지 않고 branch를 종료한다.
