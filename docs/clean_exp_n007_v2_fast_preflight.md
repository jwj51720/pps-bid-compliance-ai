# N007 v2 fast20 paid-run preflight

작성일: 2026-09-22

## 실험 선택과 변경 통제

- 가설: bounded all-document v2 view + v32 purchase-inclusive card +
  Gemma 관계 관측 + deterministic threshold/evidence projection이
  frozen v2 fast baseline을 재현할 수 있다.
- manifest: `experiments/manifests/clean_exp_n007_v2_performance_fast_v1.json`.
- `experiment.base_config`는 N006 fixed fast20 manifest이다. 이는
  v22→v2 **owner 교체의 변경 통제**이며 v22와 v2 점수를 직접
  인과 비교하는 ablation이 아니다. `allowed_policy_changes`는
  schema, card, source audit, view, task, owner 및 positive conjunction만이다.
  provider·generation·budget·fast20 cohort는 같다.
- `scripts/preflight_experiment.py` 결과 PASS, undeclared difference 0,
  unused declaration 0.

## 가설에 필요한 구성요소 점검

| 요소 | 선택된 구현·증거 |
| --- | --- |
| organizer 문서·metadata | `data/raw/open/dev.jsonl.gz`, v2 item-scoped human-readable metadata; 200건·374문서 scan |
| 범위 충돌 해소 | v31 보존, `scripts/build_v32_v2_purchase_scope_card.py` → v32 v2-only 변경; 주최측 조항 대조 문서 별도 보존 |
| exact source view | `build_v2_performance_view_v2`, doc-id/order/offset/SHA-256; gold e2 7/7 |
| 실제 prompt·schema | `build_v2_performance_task`, 200/200 exact admission, 최대 10,897토큰, task hash 200/200 |
| 관계 관측 | `performance_participation`, `procurement_role`, `explicit_allowance`, `enterprise_rule_applies`, exact quote |
| Python 투영 | `decide_v2_performance`; 금액은 organizer `입찰추정가격`만, 2.3억/7.1억 문턱; quote 검증 없으면 0 |
| 응답·출처 검증 | `parse_v2_response`; malformed/length/비원문 quote는 invalid→0 |
| isolated output | `outputs/clean-exp-n007-v2-performance-fast-v1/fast20`, mock은 `fast20-mock` 분리; response별 checkpoint |

## 렌더링 메시지 직접 검토

- dev200 audit 경로: `outputs/clean-native-v2-performance-task-v1/dev200/rendered_inputs/`.
  short `PPS-DEV-179`, attachment `PPS-DEV-196`, longest `PPS-DEV-140`,
  물품 구매 양성 `PPS-DEV-02`의 system/user를 직접 읽었다.
- 실제 fast20 preflight 경로:
  `outputs/clean-exp-n007-v2-performance-fast-v1/fast20-preflight/rendered_inputs/`.
  short 양성 `PPS-DEV-062`, attachment 음성 `PPS-DEV-131`, longest
  음성 `PPS-DEV-165`의 system/user를 직접 읽었다. long 사례에서
  제안서의 정량평가 실적과 참가자격 문구가 모두 보인다. 따라서
  둘을 분리해야 하는 0 조건의 source는 실제 렌더링에 있다.
- fast20 20건, 35문서, 191 source spans, exact task hash 20/20,
  token min/max 2,750/10,497, 한도 초과 0.
- v2 semantic-input contract는
  `docs/clean_exp_n007_v2_semantic_input_review.md`에 applicability,
  1/0 조건, 문서 유형, metadata를 원천과 span에 연결했다.

## Mock과 유료 실행 범위

`--mock`은 20 logical calls, invalid 0, expected all-zero를 정상 처리했다.
mock F1=0은 성능 측정이 아니다. 실제 paid call은 20건 단일 item 호출이며
mock response를 읽지 않는다. 실행 전 `OPENROUTER_API_KEY`가 `.env`에서
로드되는 엔트리포인트로 검증했고 secret은 출력하지 않았다.

검증: `pytest -q` 157 passed. fast 결과가 기준에 못 미치면 같은 panel에
임의로 조건을 연속 튜닝하지 않고 per-item 오류/근거/호출을 분석한다.
