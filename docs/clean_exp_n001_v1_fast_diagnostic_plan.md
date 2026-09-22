# N001: native v1 fast20 observation diagnostic

작성일: 2026-09-22

목적은 첫 frozen-only 항목을 옮기며 **자주 점수를 재는 루프**를 여는
것이다. C005D의 v1은 dev200 TP=7/FP=0/FN=0, F1=1.0이지만 frozen
결과다. N001은 v1 source view v2와 자체 판정 계약의 20개 관측을
받아, native v1의 TP/FP/FN 및 unknown 비율을 먼저 측정한다.
24-item 독립 baseline 점수 또는 제출 후보라고 부르지 않는다.

- base config: `experiments/manifests/clean_native_v1_source_audit_v2.json`
- candidate: `experiments/manifests/clean_exp_n001_v1_fast_diagnostic_v1.json`
- `allowed_policy_changes`: `run.mode`만. prompt/schema/view/provider/
  tokenizer/data/panel은 base와 동일하다.
- cohort: `configs/dev_fast_panel_v1.json`의 고정 20건(금양성 v1 3건).
- input: v31 카드 v1, metadata/CSV facts 없음(v1에 불필요), 모든 제공
  문서를 scan한 참가자격 연결 원문 span, doc id/offset/hash.
- output: `Y/N/U` observation와 exact 1~500자 quote. `Y` quote가
  원문에 없으면 invalid. `U`를 Python에서 0으로 확정하거나 frozen
  결과로 대체하지 않는다.
- 14,848-token gate: dev200 200/200 fit, max 13,370; fast20 task
  hash가 감사된 동일 task와 일치해야 한다.
- 호출: fast20 정확히 20 logical calls, 추가 v-group/document 곱셈 없음.

보고는 v1 TP/FP/FN, U 건수(양성/음성별), invalid/quote validity,
prompt/completion tokens, 실제 벽시계와 결과별 source id를 분리한다.
U가 있으면 U→0 F1은 단지 보수적 진단 값이고 완성 owner 점수가
아니다. 다른 23개 v는 재판정하지 않는다. fast20 방향이 좋더라도
holdout20 전에 dev200으로 확장하지 않는다.

유료 호출 직전 gate: manifest diff/preflight, source audit task hashes,
mock 20/20, short/attachment/largest 실제 rendered system/user
전문 검토, v1 적용전제·1·0 조건·문서 provenance trace를 기록한다.
v1에 필요한 metadata field는 없지만 이 사실도 organizer card와
fact contract에서 확인한다. 한 조건이라도 source view로 답할 수
없으면 U로 관측하도록 지시했고, N을 진정한 부재 증명으로 보지
않는다는 제한을 결과에 명시한다.
