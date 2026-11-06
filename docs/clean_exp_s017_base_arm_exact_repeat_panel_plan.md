# S017 — base r10/B/C24 hash-fixed exact-repeat micro panel 계획

작성일: 2026-09-23

상태: **계획 고정 — 구현·preflight 전**

## 2026-09-23 유료 호출 전 검토 기록

- manifest diff: PASS, undeclared 0
- exact task hash: frozen baseline과 6/6 일치
- tokenizer: 3,761~7,512 / budget 14,848, overflow 0
- source ledger: PPS-DEV-21 1/1문서, PPS-DEV-04 3/3문서 순서·hash 보존
- semantic task checks: 6/6 PASS
- 실제 rendered messages:
  - notice-only:
    `outputs/clean-exp-s017-base-arm-exact-repeat-panel-v1/rendered_inputs/{r10,B,C24}_PPS-DEV-21.json`
  - attachment:
    `outputs/clean-exp-s017-base-arm-exact-repeat-panel-v1/rendered_inputs/{r10,B,C24}_PPS-DEV-04.json`
- 사람 검토 결론: 세 arm 모두 정확한 공고 ID, human-readable F/meta, 해당 arm의 판단 계약,
  organizer 원문 S span과 strict output schema를 포함한다. attachment 공고는 공고문 D0뿐 아니라
  과업지시서 D2와 제안요청서 D1에서 뽑힌 관련 span이 arm 목적에 따라 실제 메시지에 나타난다.
  source ledger는 세 문서를 모두 보존한다. raw metadata dump나 내부 status를 판정 지시로 노출하지
  않고, 기존 frozen task와 byte-identical하다.
- overflow sample은 존재하지 않는다. 가장 큰 r10/PPS-DEV-04도 7,512 tokens로 단일 complete
  admission이며 omitted pass가 없다.

따라서 paid micro 전 계약을 충족했다. mock에서 600 stored-response 재조립과 single/joint replacement
격리를 확인한 뒤 6개 호출을 시작한다.

## 진단 질문

S014의 coarse distribution shift는 local-public gap의 약 9.42%만 설명했고, S016R의 v19 repeat
개선도 gap의 약 2.13% 크기였다. S006은 저장응답 조건에서 package/merge parity를 입증했다.
따라서 아직 직접 측정하지 않은 큰 축은 S001의 22개 base item을 공급하는 r10/B/C24 신규 생성의
변동성이다.

> 동일한 tokenizer task를 현재 OpenRouter Gemma에 다시 주었을 때 arm별 raw response 차이가
> 실제 final V 셀 변화와 정답 방향 변화로 얼마나 전파되는가?

이 실험은 prompt 개선이나 새 submission policy가 아니라 6-call generation diagnostic이다.

## label-blind 표본 선정

표본은 label, 기존 response, 기존 prediction을 보지 않고 organizer input과 tokenizer count만으로
선정했다.

1. S014 fixed strata 중 population weight가 가장 큰
   `direct|lt100m|notice_only`와 모집단 절대량이 큰
   `competitive|ge100m|attachment`를 고정했다.
2. 각 stratum에서 r10+B+C24 합산 prompt token의 중앙 순위 공고를 선택했다.
3. 같은 공고의 세 arm을 모두 반복해 arm 간 비교에서 source mix를 고정했다.

선택 결과:

| stratum | dev n | selected | docs | r10 | B | C24 | sum |
|---|---:|---|---:|---:|---:|---:|---:|
| direct, <1억, notice-only | 8 | PPS-DEV-21 | 1 | 4,952 | 3,761 | 6,240 | 14,953 |
| competitive, >=1억, attachment | 67 | PPS-DEV-04 | 3 | 7,512 | 6,321 | 5,135 | 18,968 |

총 새 호출은 `2 notices × 3 arms = 6`이다.

## 통제

- base config:
  `experiments/manifests/clean_exp_s016r_v19_json_fence_replay_v1.json`
- allowed change: `base_exact_repeat_panel`
- task builder/reference ZIP/model/provider parameters: L41 baseline과 exact 동일
- task hash: 기존
  `outputs/clean-reference-l41-openrouter-dev200-v1/preflight.json`과 일치해야 함
- original responses/rankings/other 594 tasks: byte-identical stored artifact 재사용
- 각 counterfactual은 repeat response 한 개만 교체한다.
- joint counterfactual은 selected 6개만 교체한다.
- 최종 영향은 L41 base row뿐 아니라 v3/v19를 S001 specialist 값으로 다시 덮은 실제 S001-equivalent
  row에서도 계산한다. 따라서 B의 v19 변화처럼 제출에서 specialist가 소유한 셀은 영향 0으로 분리된다.
- prompt/schema/reducer/merge/evidence/Python label rule: 변경 없음
- JSON fence가 발생해도 raw를 보존하며, frozen parser가 처리한 결과를 먼저 기록한다. 별도 parser
  변경을 이번 실험에 섞지 않는다.

## preflight

1. manifest undeclared difference 0.
2. 6개 task hash exact match.
3. source ledger가 선택 공고의 모든 organizer 문서를 포함하고 순서를 보존.
4. 6개 task 모두 14,848 tokens 이하.
5. selected 6개 실제 rendered system/user/schema를 저장.
6. notice-only와 attachment 메시지를 사람이 읽고 실제 공고 source와 output contract를 확인.
7. mock에서 한-response replacement와 joint replacement가 다른 task를 바꾸지 않음을 확인.
8. output path 격리 및 response 도착별 atomic checkpoint.

이것은 24개 semantic policy를 바꾸는 실험이 아니다. frozen base와 동일한 3개 task를 재생성하는
partial generation diagnostic이며, task의 기존 semantic contract를 그대로 계승한다.

## 측정량과 판정

arm별로 다음을 기록한다.

- raw content exact equality
- finish reason, JSON/fallback/diagnostic 상태
- 원 response 대비 final V/E changed cells
- changed V 중 correct→wrong, wrong→correct, wrong→different-wrong
- 한 task 교체 시 dev200 Macro 변화
- 6 task joint replacement 시 item별 TP/FP/FN 및 Macro 변화
- prompt/completion token, latency, retry count

micro panel이므로 고정 accuracy promotion gate를 두지 않는다. 대신 다음 분기로 원인을 좁힌다.

- final V disagreement 0/6: base generation variance가 큰 public gap의 우선 설명은 아님.
- disagreement가 한 arm에 집중: 해당 arm의 parser/schema/semantic owner를 가장 작은 단위로 감사.
- 여러 arm에서 correct→wrong이 반복: evaluator generation robustness를 주요 원인으로 승격하고,
  typed observation/reducer 또는 low-cost confirmation을 arm별로 설계.
- wrapper/invalid만 발생: S016처럼 serialization을 semantic error와 분리한 0-call replay부터 수행.

6건에서 관측된 변화율은 모집단 정확도나 public 성능 추정치가 아니다. 다음 단계의 표본 크기와
arm 우선순위를 정하는 진단값으로만 사용한다.
