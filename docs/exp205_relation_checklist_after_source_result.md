# EXP205/208 relation checklist result

작성: 2026-09-14, dev / mac

## 결론

긴 공고 원문을 읽은 직후, 최종 V/E 출력 전에 semantic relation을 짧게 재확인시키는 한 호출
방식은 세 cohort에서 모두 matched direct control을 이겼다. 새 schema, 추가 호출, 법령 원문,
dev 예시, Python label rule은 사용하지 않았다.

| cohort | direct control | checklist | delta |
|---|---:|---:|---:|
| fast20 | EXP202 `.239683` | EXP205 `.325000` | `+.085317` |
| independent holdout20 | EXP207 `.138889` | EXP206 `.208333` | `+.069444` |
| dev200 | EXP209 `.257457` | EXP208 `.292959` | `+.035502` |

dev200에서 TP/FP/FN은 `46/100/107`에서 `51/78/102`로 변했고, 전체 양성 재현율은
`.300654`에서 `.333333`으로 올랐다. 동일 input/label hashes를 사용한 paired comparison에서
관계 대상 변화는 47 corrected / 31 regressed, 비대상 변화는 23 corrected / 12 regressed였다.

## 무엇이 실제로 개선됐는가

- v22: `.363636 -> .909091`; 설명회라는 행사 역할과 불참의 참가자격 결과를 같이 보라는
  확인이 FP를 `13 -> 1`로 줄이고 FN도 제거했다.
- v8: `0 -> .500000`; 실적·지역 제한이 같은 입찰자와 같은 자격조항에 함께 적용되는지
  확인하면서 6개 양성 중 3개를 회복했다.
- v23: `.122449 -> .150000`; 날짜가 아니라 날짜 역할을 대조해 FP를 `41 -> 32`로 줄였다.
- v24: `.166667 -> .235294`; 같은 metadata 역할끼리 비교해 TP가 `1 -> 2`로 늘었지만,
  dev gold와 visible source의 불일치가 의심되는 사례가 있어 아직 약하다.
- v3와 v21은 기존 1.0을 유지했고 v9는 `.500000 -> .526316`으로 소폭 개선됐다.

관계 강조 자체가 항상 좋은 것은 아니다. v19는 recall 1.0을 얻는 대신 FP가 `3 -> 9`로
늘어 F1이 `.615385 -> .571429`로 하락했다. 비표적 v5와 v15도 손상됐다. 이 결과를 근거로
dev 문구 패턴, item별 threshold 또는 Python override를 추가하면 과적합 위험이 크다.

## Runtime과 안정성

EXP208과 EXP209는 동일한 one-stage/full-source admission 구조다. 체크리스트의 고정 토큰이
overflow 경계의 분할을 조금 앞당겨 EXP208은 219 source-pack messages, EXP209는 217
messages였다. 별도 검증 pass는 없다. EXP208 OpenRouter wall time은 541.5초, EXP209는
492.2초였다. EXP208에는 parse-error event 5개와 evidence warning 30개, EXP209에는
parse-error 0개와 warning 38개가 있었다. 모든 submission CSV validation 자체는 통과했다.

EXP200 repaired의 dev200 `.324798`은 여전히 더 높지만 438-call source-first submission이
실제 evaluator에서 120분을 초과했다. EXP208은 `.031839`의 local score를 양보하고 call
topology를 219로 줄이는 현재의 가장 근거 있는 runtime-compatible 후보다. OpenRouter 시간은
vLLM 시간을 예측하지 않으므로 evaluator GPU/vLLM runtime은 미검증 limitation이다.

## 재현 자료

- configs: `configs/config.exp202-corrected-input-direct-fast-panel-c4.yaml`,
  `configs/config.exp205-relation-checklist-after-source-fast-panel-c4.yaml`,
  `configs/config.exp206-relation-checklist-after-source-holdout-c4.yaml`,
  `configs/config.exp207-corrected-input-direct-holdout-c4.yaml`,
  `configs/config.exp208-relation-checklist-after-source-dev200-c4.yaml`,
  `configs/config.exp209-corrected-input-direct-dev200-c4.yaml`
- rendered review: `outputs/exp205-preflight/rendered_inputs/`
- paired fast: `outputs/exp205-preflight/paired_exp202_exp205.json`
- paired holdout: `outputs/exp206-preflight/paired_exp207_exp206.json`
- paired dev200: `outputs/exp208-audit/paired_exp209_exp208.json`
- postprocess audits: `outputs/exp208-audit/postprocess_audit.json`,
  `outputs/exp209-audit/postprocess_audit.json`

## 결정

관계 체크리스트 가설은 채택한다. 다음 submission 후보로 만들 때도 카드·metadata/product facts,
모든 tokenizer-admitted 원문, V/E schema와 frozen postprocess는 그대로 유지한다. 별도 단계나
v-grouping을 곱하지 않는다. 제출 승격 전 exact staged zip mock, 49-column/evidence validation,
static asset 검증과 가능한 vLLM runtime smoke를 새 책임 단위로 수행한다.
