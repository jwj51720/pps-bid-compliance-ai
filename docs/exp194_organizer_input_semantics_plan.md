# EXP194: 주최 측 입력·익명화 표기 의미 전달

작성: 2026-09-11, dev / mac

## 문제와 가설

배포 `README.md`는 익명화 토큰이 보존하는 의미를 명시하지만, 현재 final
rendered prompt는 원문 토큰만 보여 주고 해독 규약을 제공하지 않는다. 이는 법령
추론이나 dev label 사실이 아니라 organizer-provided input semantics의 실제 누락이다.

가설은 README의 표기 규약을 짧은 human-readable context로 제공하면 Gemma가
지역 단위, 서로 다른 지역, 기관 유형을 원문의 실제 조건과 올바르게 연결할
수 있다는 것이다. 표기 설명 자체는 어떤 v도 자동으로 1로 만들지 않고, 카드·
metadata·원문을 모델이 다시 대조한다.

## 출처 계약

`data/raw/open/README.md` 4절의 다음 사실만 전달한다.

1. 기관명·담당자·연락처·주소·공고번호는 익명화 토큰으로 치환됐다.
2. `[수요기관(기초자치단체)|지역=r1]`같은 토큰은 기관 유형을 보존한다.
3. `[지역:r1|단위=기초|광역=경기도]`같은 지역 계층을 보존한다.
4. 같은 문서에서 `r1`과 `r2`는 서로 다른 지역이다.
5. 금액·수량·날짜·법령 조문·품명·규격은 치환되지 않았다.

토큰의 숨겨진 실제 지역명을 복원하거나, `r1`을 특정 지역으로 추정하거나,
표기 존재를 위반으로 자동 변환하지 않는다.

## 변경 통제

- `experiment.base_config`: `configs/config.exp169-complete-source-2500-fast-panel-c4.yaml`
- `experiment.allowed_policy_changes`: `prompt.organizer_input_semantics_mode`
- base: `off`
- candidate: `anonymization_v1`
- card, 제품 context, 원문 범위, output schema, merge, model/provider 파라미터는
  변경하지 않는다.

EXP193 v6 card와 결합하지 않는다. 우선 표기 의미 전달 자체의 효과와
부작용을 분리한다.

## 구현 계약

- 규약은 fixed, versioned renderer로 관리한다.
- raw metadata JSON, internal status/code, 법령 원문을 추가하지 않는다.
- source-first로 확장할 때 navigation과 final의 모든 exact-token admitted pack에
  같은 규약을 전달한다.
- 규약은 fixed context이므로 문서보다 먼저 token admission에 반영한다.
- 이 규약은 evidence가 아니며, e는 여전히 공고 원문 substring만 허용한다.

## 유료 실행 전 gate

1. unit test: mode 검증, off 회귀, 규약 정확 문구, label/evidence 자동판정 문구 비존재
2. preflight: 선언 외 effective policy 차이 0
3. exact tokenizer admission/source provenance profile
4. short complete, attachment, overflow의 실제 rendered system/user message 수동 검토
5. 24-v semantic-input contract audit
6. fast20 mock과 49열/evidence 검증

fast20은 `configs/dev_fast_panel_v1.json`만 사용한다. 성능 판정은 macro와 함께
v1, v5–v8, v24의 TP/FP/FN, 표기 토큰이 있는 공고와 없는 공고의 off-target
변동, parse/evidence/runtime을 따로 보고한다. fast gain이 확인된 뒤에만
holdout20, 그 뒤 dev200으로 확장한다.

## 실행 전 검증 기록

- preflight: 선언된 `prompt.organizer_input_semantics_mode` 하나만 차이, PASS
- exact tokenizer fast20: 18건 1 pack, 1건 2 packs, 1건 3 packs, 총 23 call
- dev200 complete-fact admission: 374 source documents, omission 0, metadata omission 0,
  semantics omission 0, over-budget 0, PASS
- semantic-input contract: 24/24 PASS
- mock: 20 rows, 49 columns/ID/evidence validation PASS
- rendered review:
  - short complete: `outputs/exp-194-organizer-input-semantics-fast-panel-c4/prompt_review/pps-dev-062.messages.md`
  - attachment: `outputs/exp-194-organizer-input-semantics-fast-panel-c4/prompt_review/pps-dev-194.messages.md`
  - overflow: `outputs/exp-194-organizer-input-semantics-fast-panel-c4/prompt_review/pps-dev-169.messages.md`
  - 기초지역 반례: `outputs/exp-194-organizer-input-semantics-fast-panel-c4/prompt_review/pps-dev-072.messages.md`

수동 검토에서 규약은 metadata 뒤·원문 앞에 한 번씩 있었고, overflow 3 pack
모두에 반복됐다. 숨겨진 지역명을 복원하거나 표기를 라벨로 바꾸는 문구는 없었고,
원문·카드·metadata 재대조 계약이 유지됐다.
