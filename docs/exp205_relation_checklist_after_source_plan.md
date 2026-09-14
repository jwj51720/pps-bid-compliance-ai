# EXP205 relation checklist after source plan

작성: 2026-09-14, dev / mac

## 가설

EXP203/204는 v24 원문 추출과 metadata 전달이 되어도 semantic role을 잘못 짝지었고,
v24 dev labels 자체에도 visible-source와 concordance가 낮은 사례가 있었다. v24 wording을
더 조정하지 않는다. 대신 기존 카드에서 이미 요구하지만 긴 원문 뒤에서 누락되는 관계 검증을
판정 직전에 짧게 재호출한다.

공통 검증 순서는 다음 네 질문이다.

1. 두 사실의 대상·주체가 같은가?
2. 수치·날짜·계약·지역·업종의 semantic role이 같은가?
3. 같은 참가자격 조항 또는 명시적 AND/OR 범위에 함께 적용되는가?
4. 카드의 적용범위·0 조건·예외를 확인했는가?

이를 source 뒤에 배치하고 v3, v8, v9, v19, v21–v24의 기존 관계 조건을 한 줄씩 다시
확인시킨다. 새 법률조건, dev 사례, gold label, threshold는 넣지 않는다. 출력은 기존 24 V/E
그대로이며 별도 review field나 호출이 없다.

## base와 허용 변경

- base: `configs/config.exp202-corrected-input-direct-fast-panel-c4.yaml`
- candidate: `configs/config.exp205-relation-checklist-after-source-fast-panel-c4.yaml`
- allowed change: `prompt.mode` 하나
- 고정: cards, metadata/product/anonymization facts, source scope/admission, V/E schema,
  model/provider, evidence, overflow merge, frozen postprocess
- Python label/법률 rule 없음

## gates

preflight, exact admission, rendered short/attachment/overflow, 24-item contract, mock, full tests 후
fast20을 한 번 실행한다. EXP202 대비 macro와 total recall이 개선되고 관계 항목의 개선이
비관계 항목 손상보다 크며 parse/evidence가 유지될 때만 holdout20으로 간다. target 변화 없이
provider/prompt perturbation만 보이면 중단한다.

## 2026-09-14 preflight 기록

- preflight: 통과, EXP202 대비 effective difference는 `prompt.mode` 하나.
- fast20 exact admission: 24 calls; dev200: 184×1 + 13×2 + 3×3 = 219 calls.
- dev200 374/374 source documents, metadata/card/organizer semantics/product fact omission 0,
  over-budget pack 0.
- semantic contract: short와 attachment 모두 24/24 통과.
- rendered short/attachment/overflow를 읽어 checklist가 각 admitted source 뒤에 있고 모든 fixed
  input이 유지됨을 확인했다. 원문, 카드, metadata를 대체하지 않으며 schema는 기존 V/E다.

## Fast20 result와 holdout 승인

- EXP202 `.239683` → EXP205 `.325000` (`+.085317`).
- TP/FP/FN `13/10/25` → `14/4/24`, total recall `.342105` → `.368421`.
- relation focus changes: 7 corrected / 2 regressed. v8 F1 `0→1`, v22 `.667→1`,
  v23 `.286→1`; off-target changes 2개는 모두 corrected.
- 24 calls, 46.7 s, parse error 0. validation warning은 2개이며 v8/e8과 v23/e23의
  positive evidence가 비어 있다. label gain과 별개로 submission evidence risk로 추적한다.
- model-owned macro `.269949`, frozen postprocess 후 `.325000`.

사전 quality gate를 통과했다. policy-identical holdout은
`configs/config.exp206-relation-checklist-after-source-holdout-c4.yaml`로 실행한다.

Holdout의 historical EXP170은 corrected card/product/metadata/semantics가 달라 matched control이
아니다. EXP206과 같은 cohort에서 EXP202 policy를 실행하는 control은
`configs/config.exp207-corrected-input-direct-holdout-c4.yaml`이다. 두 결과를 paired 비교한
후에만 dev200 진입을 결정한다.

## Holdout result와 dev200 승인

- matched control EXP207 `.138889`; checklist EXP206 `.208333`; delta `+.069444`.
- TP/FP/FN `4/7/11` → `5/11/10`, recall `.266667` → `.333333`.
- v22 TP를 회복했고 v23 F1은 `.333→0`으로 악화했다. FP 증가는 dev200에서 반드시
  precision/item별로 재평가한다.
- fast와 holdout 모두 macro/recall이 같은 방향이므로 policy-identical dev200 EXP208을 승인한다.

EXP208의 순수 checklist delta는 corrected direct dev200 control EXP209와 paired 비교한다.
EXP200은 source-first topology, EXP172는 corrected inputs 이전이므로 어느 쪽도 matched control이 아니다.

## Dev200 result

- matched direct control EXP209 `.257457` -> checklist EXP208 `.292959`, delta
  `+.035502`. Input/label hashes와 200개 ID가 동일하다.
- TP/FP/FN `46/100/107` -> `51/78/102`, total recall `.300654` -> `.333333`.
- focus change는 47 corrected / 31 regressed, off-target change는 23 corrected / 12
  regressed였다. 단순히 1 예측을 늘린 효과가 아니라 전체 FP도 22개 줄었다.
- 큰 이득은 v8 `0 -> .500`, v22 `.364 -> .909`; 작은 이득은 v9 `.500 -> .526`,
  v23 `.122 -> .150`, v24 `.167 -> .235`다. v3/v21은 1.0을 유지했다.
- v19는 모든 양성을 찾았지만 FP가 `3 -> 9`로 늘어 F1 `.615 -> .571`로 하락했다.
  비표적 v5 `.364 -> .222`, v15 `.250 -> 0`도 손상됐다. 따라서 관계 지시를 더
  강하게 일반화하거나 dev item별 threshold/rule로 보정하지 않는다.
- EXP208은 219 admitted source-pack messages, 541.5 s, prompt/completion
  `3,443,624/139,163`, parse-error event 5, evidence warning 30이었다. EXP209는
  217 messages, 492.2 s,
  `3,306,401/149,620`, parse-error 0, evidence warning 38이었다. OpenRouter wall time은
  evaluator vLLM runtime의 근거가 아니다.
- EXP200 repaired `.324798`보다는 `.031839` 낮지만, EXP200의 438-call two-stage submission은
  120분을 초과했다. EXP208은 입력 완결성과 full-source coverage를 유지하면서 1-stage 219-call
  topology에서 확인된 현재의 runtime-compatible 후보다. 실제 evaluator vLLM smoke/runtime은
  아직 미검증이다.

결론: 관계형 의미 역할을 원문 뒤에서 판정 직전에 재확인시키는 가설은 fast, independent
holdout, matched dev200에서 모두 같은 방향으로 통과했다. 다만 canonical/submission 승격은
별도 packaging과 exact staged mock, vLLM runtime 검증 뒤에 결정한다.
