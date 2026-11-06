# S018 — v17 원문 관계와 과적합 위험 감사 계획

작성일: 2026-09-23

## 질문

S001의 v17은 dev200에서 TP 6, FP 7, FN 0이며, S014의 모집단 비율 재가중 F1은
0.6316에서 0.4810으로 떨어졌다. 어떤 **원문 관계**를 놓쳐 FP가 생겼는지 확인한다.
목표는 최종 규칙을 즉시 교체하는 것이 아니라, 제거하거나 별도 모델 판정으로 옮겨야 할
가정을 식별하는 것이다.

## 고정 입력과 변경 범위

- manifest: `experiments/manifests/clean_exp_s018_v17_source_relations_v1.json`.
- 기준: `experiments/manifests/clean_exp_s014_covariate_shift_stress_v1.json`.
- `allowed_policy_changes`: 없음. S001 V/E, frozen L41, 카드, 제품 CSV, merge, provider 및
  tokenizer admission을 변경하지 않는 0-call 진단이다.
- 원본: `data/raw/open/dev.jsonl.gz`, `data/raw/open/dev_labels.csv`,
  `data/derived/competition_products_v1.json`.
- 저장 판정: `outputs/clean-exp-s001-integrated-v3-v19-v1/submission.csv`.
- 재가중: `outputs/clean-exp-s014-covariate-shift-stress-v1/audit_report.json`의 고정
  stratum weight. 이는 public 성능 예측이 아니라 분포 스트레스다.
- frozen reference: `dist/reference/submit.zip`, SHA-256
  `a06feff77ffbc4a6f2a47cd0e2d322f341f652ca865d1b9cf53919012c8ca216`.

## 감사 방법

1. S001 v17 양성 13건의 truth, 계약유형, 입찰추정가격, 첨부 여부를 대조한다.
2. frozen `scope_hits_v2`가 선택한 실제 원문 span을 살피고, 참가자격의 기업범위와
   확인서 이름의 역할을 분리한다.
3. 정확한 10자리 제품코드의 organizer CSV 매칭 여부, 문서의 코드 역할(실제 구매대상인지
   직접생산 참가요건인지), `특이사항` 적용 여부를 분리한다.
4. `제2조의3` 같은 문자열의 등장과 **이번 계약에 실제 적용된 예외**를 구분한다.
5. 어떤 보정의 dev 효과도 TP/FP/FN으로 다시 계산하되, dev 오류를 본 뒤 만든 보정은
   adaptive oracle ceiling으로만 표기한다. 일반화 점수로 사용하지 않는다.
6. 가능하면 비라벨 20,000건에서 같은 source-role 조합의 빈도를 별도로 확인한다. 이
   단계에는 정답을 추정하지 않는다.

## 사전 결정 기준

- 원문에 명시된 소기업 전용 조건 또는 현재 계약의 명시적 예외를 기존 owner가 놓치면
  실제 semantic defect로 기록한다. 단순 키워드 veto로 패치하지 않는다.
- exact CSV 코드가 있어도 실제 구매대상과 연결되지 않으면 경쟁제품 veto 근거로 삼지 않는다.
- v17 한 항목의 이론적 Macro 상승 상한은 `1/24`다. public-local 괴리 약 0.2098의
  단독 해법이라고 주장하지 않는다.
- 새로운 유료 프롬프트 실험을 시작한다면 rendered-input 3종, v17 semantic-input contract,
  source coverage, exact tokenizer admission, mock, preflight와 isolated outputs를 별도
  계획에 기록한다.
