# EXP122A — 공식 baseline prompt 정합성 probe 결과

## 목적과 변경 범위

EXP109는 이름과 달리 organizer baseline과 완전히 같지 않았다. 공식 baseline은 metadata를
`- 필드: 값` 줄 목록으로 넣는데, shared pipeline 기본값은 JSON block(`full_json`)이었다.
또한 submission entrypoint는 `metadata_style`과 `item_catalog_style`을 runtime config에서
pipeline으로 전달하지 않았다.

이번 수정은 이 재현성 결함을 고친 것이다. canonical `config.yaml`과
`submission/runtime_config.json`은 `official_lines`를 명시하고, submission entrypoint도 모든
prompt policy field를 전달한다. `tests/test_pipeline.py`는 organizer baseline과 동일 record의
system/user messages가 byte-level로 일치하는지, `tests/test_submission.py`는 runtime forwarding을
검사한다.

historical EXP109은 소급 변경하지 않았다. 기존 결과는 `full_json` historical audit으로 보존한다.

## 실행

- config: `configs/config.exp122a-exact-organizer-baseline-fast-panel.yaml`
- base: `configs/config.exp109-official-baseline-v1-ve-full200.yaml`
- declared policy delta: `prompt.metadata_style: full_json -> official_lines`
- cohort: frozen `configs/dev_fast_panel_v1.json` 20건
- model: existing OpenRouter Gemma, temperature 0, seed 20260826, V/E output
- validation: preflight, byte-parity regression test, mock run 통과
- actual runtime: 343.635초, 20/20 완료. OpenRouter 지연 두 건은 있었으나 실패/재시도 오류는 없었다.

## 결과

| 비교 대상 | fast-20 macro positive-F1 |
| --- | ---: |
| historical EXP109 (`full_json`) | 0.205788 |
| EXP122A exact organizer lines | 0.161210 |

두 결과 사이에서 25개의 v cell이 바뀌었다. 새 결과가 맞춘 cell 13개, 틀린 cell 12개로 거의
상쇄됐지만 macro-F1은 v2·v4의 positive recall 하락 때문에 낮아졌다. 반면 v19/v24 일부는
개선됐다. EXP122A의 evidence validity는 0.800 (30 positive cases), schema/CSV validation은 통과했다.

## 해석과 결정

이 20건은 **성능 승격 근거가 아니다**. historical EXP109과 독립된 원격 생성 호출이라 format
change와 provider variation을 완전히 분리할 수 없고, cohort도 canonical selection용이 아니다.
그러나 공식 baseline input과 submission input이 서로 달랐다는 결함은 사실이므로, exact parity
수정은 유지한다. "공식 baseline" 성능을 주장할 때에는 EXP109 수치를 사용하지 않는다.

EXP123의 public 0.26045 (local 0.31780)도 함께 보면, dev의 특정 v rule/card를 계속 덧붙이는
방식은 일반화 가능성이 낮다. 다음 탐색은 개별 threshold/override가 아니라, organizer가 허용한
20k unlabeled notice를 이용해 **문서·업무 유형 coverage를 먼저 설계한 뒤** 좁고 provenance가 있는
self-label precedent를 만드는 방향만 검토한다. 이미 수행한 단순 키워드/card lexical retrieval은
보일러플레이트를 잘못 가져와 종료했다(`docs/precedent_s0_result.md`).
