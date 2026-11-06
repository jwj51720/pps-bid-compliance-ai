# EXP267 — v6 source-only geography relations, full-source final

작성: 2026-09-15, dev / mac

## Observed failure and hypothesis

EXP264–266에서 기존 V/E, threshold-corrected V/E, 동일 입력 V-only가 모두 fast v6
`TP 0 / FP 0 / FN 1`이었다. 수정 V/E는 양성 `PPS-DEV-072`의 실제 참가자격 문장인
`본점 소재지를 ... [지역:r1|단위=기초|광역=경기도] 또는 제주도`를 정확히 발췌했지만
0으로 판정했다. 따라서 source 발견·token admission·숫자 operand·evidence 출력 부담만으로는
이 오류를 설명할 수 없다. 같은 자격조항 안의 기초지역 제한, 추가 광역지역, 수행장소와
계약절차의 관계를 분리하지 못하는 것이 확인된 최소 병목이다.

가설은 첫 Gemma가 법률판정 없이 네 역할의 원문 관계를 구조화하고, 두 번째 Gemma가 그
후보와 corrected v6 card, 필요한 metadata, organizer semantics, 모든 admitted 원문을 다시
보면 v6 양성을 회복할 수 있다는 것이다.

## Two-stage contract

Stage 1은 각 exact-token admitted source pack에서 다음 변경 없는 원문만 최대 3개씩 반환한다.

- `참가자격_지역문구`: 본점·영업소·사업장 소재지 참가조건과 모든 대안 지역
- `현장납품지_지역문구`: 현장·납품지·시설·행사장소
- `계약방식_절차문구`: 제한경쟁·수의·견적제출 등 실제 절차
- `지역범위_보충문구`: 범위를 바꾸는 조건, 업체 수·유찰·인접 관계 등 보충 사실

Stage 1은 card, metadata, 제품 fact, 법령 원문, v6 이름, 0/1, 허용·예외 결론, 금액 계산을
보지 않으며 organizer anonymization 표기 규약만 받는다. Python은 malformed response를 빈
navigation으로 처리하고, 원문 substring/doc-id 연결·중복 제거만 한다. 어떤 fact도 label로
변환하지 않는다.

Stage 2는 EXP265와 같은 corrected v6 card + human-readable metadata + organizer semantics +
모든 admitted 원문을 다시 받고, 검증된 Stage-1 후보를 advisory navigation으로 추가한다.
Stage 2 Gemma만 v6/e6 최종 소유자다. navigation이 비어도 0을 강제하지 않으며 e6는 final
source의 변경 없는 500자 이하 substring이어야 한다.

## Controlled policy and exclusions

- base: `configs/config.exp265-v6-threshold-ve-fast-panel-c4.yaml`.
- sole semantic change is the new staged execution. Because the base serializes it as
  `staged_run: null`, preflight must declare both the parent `staged_run` shape change and
  `staged_run.mode`; neither permits another prompt/LLM policy change.
- card v17, active v6, V/E schema, metadata/source policy, exact tokenizer admission, merge,
  frozen postprocess와 provider parameters는 고정한다.
- 기존 7-category inventory, 24-item inventory, document×v grouping, V-only voting, Python
  지역/금액/법률 rule, raw-law prompt를 사용하지 않는다.

## Gates and promotion

유료 실행 전에 schema/parser/malformed/substr provenance tests, declared preflight, dev200
Stage-1/Stage-2 exact admission과 call topology, source coverage, actual short/attachment/overflow/
v6-positive rendered messages, v6 semantic-input contract, exact mock와 49-column validation을
완료한다. fast20에서 EXP265의 v6 F1 0을 개선하고 parse/source failure가 없어야 independent
holdout20으로 간다. holdout은 v6 positive가 없으므로 FP 비열화를 확인한 뒤에만 dev200으로
확장한다. 이 실험은 local-quality probe이며 2-stage call 비용이 evaluator-safe하다는 주장은
별도 vLLM runtime 증거 없이는 하지 않는다.

## Pre-provider gate (2026-09-15)

- `scripts/preflight_experiment.py`: base EXP265 대비 선언된 `staged_run` 및
  `staged_run.mode` 변경만 확인했다.
- exact-token conservative dev200 profile:
  - Stage 1: 200 calls, 모든 공고 single pack.
  - Stage 2: navigation 최대 payload를 넣은 상한 208 calls
    (`193×1 + 6×2 + 1×3`). 총 상한 408 calls.
  - 원문은 Stage 1/2 모두 374/374문서가 admitted됐고 누락은 0이다.
  - 최대 prompt token은 Stage 1 29,164, Stage 2 30,267이며 admission budget은
    30,268이다.
- semantic-input audit: short `PPS-DEV-062`, attachment `PPS-DEV-194`, overflow
  `PPS-DEV-169`, v6 positive `PPS-DEV-072`에서 active v6 contract가 모두 통과했다.
- rendered-message review:
  - Stage 1에는 실제 card/metadata/법률/label이 없고 네 geography relation schema와
    admitted 원문만 있다.
  - Stage 2에는 corrected v6 card, 필요한 human-readable metadata와 organizer semantics,
    advisory navigation, 모든 admitted 원문이 다시 존재한다.
  - attachment 및 overflow fixture에서도 원문 document type과 provenance가 유지된다.
- exact staged mock:
  `outputs/exp-267-v6-geography-inventory-full-final-fast-panel-c4-mock/`.
  20/20 완료, mode와 네 inventory key가 직렬화됐고 parse error 0, submission validation
  통과다.
- tests: `.venv/bin/python -m pytest -q` → `230 passed`.

따라서 fast20 유료 실행에 필요한 구현·입력·출력·provenance gate는 충족했다. 이 기록은
성능 결과가 아니라 실행 허가 근거다.

## Fast20 result (2026-09-15)

- output: `outputs/exp-267-v6-geography-inventory-full-final-fast-panel-c4/`
- runtime: 41.192 seconds; prompt 503,078 / completion 4,121 tokens; cost $0.04566084.
- parse errors 0, submission validation passed, evidence validity 1.0.
- v6: `TP 0 / FP 0 / FN 1`, positive-F1 0.0. EXP265 corrected-card V/E control과
  완전히 같다.
- 핵심 양성 `PPS-DEV-072`에서 Stage 1은 참가자격 문구 두 개를 정확히 찾았다. 특히
  `본점 소재지 ... 경기도 [지역:r1|단위=기초|광역=경기도] 또는 제주도`를 변경 없이
  추출했고 계약방식 문구도 별도 role에 넣었다. 그런데 Stage 2 raw response는 같은
  참가자격 문구를 근거로 인용하면서도 `v6=0`을 반환했다.

따라서 실패 원인은 source 누락, token admission, 발췌 실패, evidence 생성 부담으로
설명되지 않는다. 이 fixture에서는 Gemma가 card의 시·군·구 제한 truth condition과
anonymized `r1` 관계를 최종 법률판정으로 연결하지 못했다. 같은 사실을 한 번 더
source-only로 구조화하는 접근은 추가 정보가 없으므로 기각한다. fast gate를 넘지 못해
holdout/dev200으로 확장하지 않는다.
