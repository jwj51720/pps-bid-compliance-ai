# S021 — 기존 지역 참가조건 view의 v5 guard 반사실

S020이 확인한 v5 평가·납품처 오독을 이미 구현된
`build_regional_participation_candidates`로 제거할 수 있는지 검사한다. 이는 **무호출
진단**이며 canonical S001과 제출물을 바꾸지 않는다.

- base: `experiments/manifests/clean_exp_s001_integrated_v3_v19_v1.json`
- hypothetical change: v5가 1인 notice 중 기존 source view가 참가자 소재지 후보를 하나도
  찾지 못하면 v5를 0으로 강등한다. 금액 선택기·법적 threshold·다른 v는 불변.
- `allowed_policy_changes`: 진단 결과에는 `[]`; 제출 정책 변경은 없음.
- dev200과 organizer 비라벨 20,000건에 같은 frozen v5 predicate와 같은 clean source view를
  적용한다. dev에서는 S001 제출 셀과 parity를 확인하고 TP/FP/FN 변화를 계산한다.
- 비라벨에서는 발화·제거 건수만 측정한다. S020 hash 고정 8건에서 예상되는 false-removal과
  false-retention을 원문 역할 기준으로 점검한다. 정답률이나 public F1로 부르지 않는다.
- acceptance: dev TP 7/7 보존은 필요조건일 뿐이다. S020에서 명백한 참가제한을 제거하거나
  명백한 평가/납품처를 남기면 guard는 일반화용으로 기각한다.
- 입력: frozen L41 ZIP, 원본 dev/20k, S001 submission, organizer dev labels.
- output: `outputs/clean-exp-s021-v5-existing-role-guard-v1/audit_report.json`.
- LLM/BGE 0회. 새 prompt, tokenizer admission, rendered message, mock은 해당 없음.
