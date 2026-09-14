# EXP203 one-call v24 fact-first plan

작성: 2026-09-14, dev / mac

## 가설과 최소 변경

EXP200은 원문 navigation에서 gold evidence를 자주 찾고도 final에서 v24 관계를 놓쳤으며,
두 번의 full-source read 때문에 public 120분을 초과했다. EXP203은 EXP202의 corrected direct
full-source control을 유지하면서 **같은 한 호출 안에서** v24 원문↔메타 대조를 먼저 출력하고
그 뒤 v1–v24 V/E를 최종 판정하게 한다. 별도 stage, verifier, item grouping은 추가하지 않는다.

- base: `configs/config.exp202-corrected-input-direct-fast-panel-c4.yaml`
- treatment: `configs/config.exp203-v24-fact-first-single-pass-fast-panel-c4.yaml`
- `allowed_policy_changes`: `prompt.mode` 하나
- 고정: cards v6, metadata/product/anonymization facts, 모든 admitted source, tokenizer budget,
  model/provider parameters, evidence/overflow merge, frozen postprocess

응답의 첫 키 `v24대조`는 예산·계약방법·지역제한·업종에 대해 원문값, 메타값,
양립가능/양립불가능/판단불가를 최대 4개 기록한다. 두 번째 키 `판정`은 기존 24개 V/E다.
Python은 원문값의 substring 여부를 기록할 뿐 대조값을 v24 label로 변환하거나 override하지 않는다.

## 유료 전 gate

1. preflight가 `prompt.mode` 외 effective policy 차이를 거부한다.
2. exact-token admission에서 supplied source omission과 over-budget가 0이고 call count를 기록한다.
3. short complete, attachment, overflow의 실제 system/user message와 schema를 export해 읽는다.
4. 24/24 semantic-input contract가 final rendered prompt에 존재한다.
5. exact config mock이 20 rows, 49 columns, ID/evidence validation을 통과한다.
6. parser test는 malformed review를 거부하고, review의 관계가 label을 바꾸지 않음을 증명한다.

## 평가와 중단 규칙

fast20은 `configs/dev_fast_panel_v1.json`만 사용한다. EXP202와 비교해 macro가 상승하고,
v24 TP/FP 및 전체 positive recall이 악화되지 않으며 parse/recovery error가 0일 때만 frozen
independent holdout20으로 확장한다. gate 실패 시 wording 반복이나 multi-item schema 확장 없이
종료하고 Phase C card/calibration audit로 넘어간다. holdout도 같은 방향일 때만 dev200을 실행한다.

결과에는 config, metrics, per-item TP/FP/FN, parse errors, evidence validity, call count, runtime,
token usage, rendered-input review, v24 review source-validity를 isolated output과 문서에 남긴다.

## 2026-09-14 preflight 기록

- policy preflight: 통과. effective difference는 `prompt.mode` 하나다.
- fast20 exact admission: 17×1 pass, 2×2 pass, 1×3 pass로 총 24 calls.
- dev200 complete-fact admission: 200 records / 374 supplied documents, omission 0,
  metadata omission 0, over-budget pack 0, 185×1 + 13×2 + 2×3 = 217 calls.
- semantic-input contract: PPS-DEV-062(short complete), PPS-DEV-194(attachment) 모두 24/24 통과.
- rendered review:
  `outputs/exp203-preflight/rendered_inputs/`의 PPS-DEV-062, PPS-DEV-194, PPS-DEV-169을 읽었다.
  세 경우 모두 24 cards, human-readable metadata, anonymization semantics, condition-aware product
  fact, 실제 source가 존재한다. PPS-DEV-194에는 공고문+규격서가 있고 PPS-DEV-169 overflow는
  세 pack 모두 fixed inputs를 유지하며 D0/D1 및 D1 continuation을 exact admission한다.
  `v24대조` instruction이 판정보다 앞에 있고 원문 substring·비자동판정 contract가 명시됐다.
