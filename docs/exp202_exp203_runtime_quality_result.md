# EXP202 direct control and EXP203 v24 fact-first result

작성: 2026-09-14, dev / mac

## 결론

EXP202 corrected direct full-source는 public runtime 방향의 새 control로 유효하다. dev200
exact admission은 217 calls로 EXP200의 438 calls보다 절반 이하이고, supplied 374 documents를
하나도 누락하지 않는다. 다만 fast20 quality는 `.239683`으로 낮아 EXP200의 품질을 그대로
유지하지 못한다.

EXP203 one-call v24 fact-first는 fast20 final macro를 `.255556`으로 `+.015873` 올렸지만
사전 target gate를 실패했다. v24는 EXP202의 `TP 0 / FP 0 / FN 3`에서
`TP 0 / FP 3 / FN 3`으로 악화됐다. 따라서 holdout20과 dev200은 실행하지 않으며 이
schema를 canonical 또는 submission candidate로 승격하지 않는다.

## 재현과 artifacts

- control config: `configs/config.exp202-corrected-input-direct-fast-panel-c4.yaml`
- treatment config: `configs/config.exp203-v24-fact-first-single-pass-fast-panel-c4.yaml`
- control output: `outputs/exp-202-corrected-input-direct-fast-panel-c4/`
- treatment output: `outputs/exp-203-v24-fact-first-single-pass-fast-panel-c4/`
- preflight/render/audit: `outputs/exp203-preflight/`
- paired comparison: `outputs/exp203-preflight/paired_exp202_exp203.json`
- tests: `.venv/bin/python -m pytest -q` → 200 passed

## Quality와 runtime

| 지표 | EXP202 direct | EXP203 v24 fact-first | 변화 |
|---|---:|---:|---:|
| fast20 final macro positive-F1 | .239683 | .255556 | +.015873 |
| model-owned macro positive-F1 | .198016 | .221825 | +.023810 |
| TP / FP / FN (24항목 합계) | 13 / 10 / 25 | 13 / 6 / 25 | FP -4 |
| 전체 positive recall | .342105 | .342105 | 0 |
| v23 F1 | .285714 | .666667 | +.380952 |
| v24 TP / FP / FN | 0 / 0 / 3 | 0 / 3 / 3 | FP +3 |
| calls | 24 | 24 | 0 |
| remote runtime | 59.1 s | 76.8 s | +17.7 s |
| prompt tokens | 363,834 | 369,355 | +5,521 |
| completion tokens | 17,747 | 25,917 | +8,170 |
| parse-error records | 0 | 0 | 0 |

총점 상승은 target인 v24가 아니라 v23 FP가 5→1로 줄어든 우연한 cross-item 변화에서 왔다.
같은 TP/FN에서 FP만 4개 줄었고, v24에서는 정확히 반대로 FP 3개가 생겼다. 이는 fast20의
prompt perturbation 효과이지 v24 relation extraction 성공의 증거가 아니므로 holdout 비용을
쓸 근거가 없다.

## Observable review 진단

20 notices의 24 admitted passes에서 96개 review가 생성됐다. Gemma는 optional instruction에도
매 pass마다 예산·계약방법·지역제한·업종 4개를 모두 채웠다.

- non-null 원문값 77개 중 exact/whitespace-normalized substring valid 72개(93.5%).
- null 19개, non-null invalid 5개.
- 관계: 양립가능 93, 양립불가능 3, 판단불가 0.
- 양립불가능 3개가 모두 v24 FP가 됐다.

즉 원문값 복사는 대체로 성공하지만, 어떤 source phrase와 어떤 metadata field가 같은 의미인지,
분류 차이가 실제 불일치인지 판단하는 단계가 실패했다. 예를 들어 `협상에 의한 계약`은
낙찰방법인데 `계약방법=제한경쟁`과 양립할 수 있으며, source의 `제한경쟁`과 metadata의
`일반경쟁`은 실제 비교 대상이다. EXP203은 이 field role을 안정적으로 분리하지 못했다.

반대로 fast gold-positive PPS-DEV-072의 source 지역은 `경기도의 특정 기초지역 또는 제주도`이고
metadata 지역은 `경기도` 하나인데도 `양립가능`으로 냈다. PPS-DEV-049와 PPS-DEV-062는 현재
보이는 네 field만으로는 source와 metadata가 대부분 일치해 label/card concordance를 추가로
확인해야 한다. organizer 항목표는 네 field 이름 외 세부 truth condition을 제공하지 않는다.

## 다음 결정

1. 제출 topology는 EXP202의 one-stage 217-call 구조를 runtime-safe floor로 유지한다.
2. EXP203을 wording 변경으로 반복하거나 24-item relation ledger로 확대하지 않는다.
3. 다음 유료 실험 전에 dev의 v24 positive 8건과 matched negative를 field-role 단위로 수동
   concordance audit하여 card가 gold를 설명하는지 먼저 확정한다.
4. 동시에 zero-TP이면서 truth condition이 비교적 명시적인 v20 또는 v6/v7 card를 organizer
   source로 역추적한다. semantic contract가 이미 표현 가능한 경우 새 schema를 만들지 않고,
   card/calibration 한 변수만 실험한다.
5. 동료의 near-vanilla public `.32734` artifact가 확보되면 어떤 prompt 실험보다 먼저 exact
   runtime/config/template diff를 수행한다. 현재 가장 큰 미확인 변수는 입력 누락이 아니라
   evaluator에서 실제로 빠르게 동작한 execution contract다.
