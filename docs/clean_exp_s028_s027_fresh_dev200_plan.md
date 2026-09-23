# S028 — S027 제출 ZIP의 신규 Gemma 응답 dev200 평가

2026-09-23. 사용자가 요구한 로컬 성능은 S005/S027의 **저장응답 replay**
0.7910823947과 구별한다. 정확히 `dist/pps_20260923_163852.zip`의
`script.run`을 실행하되, offline vLLM 호출을 같은 model/temperature/seed/schema의
OpenRouter Gemma로 전송해 **새 응답**을 받는다. BGE ranking은 입력·embedding
정책이 불변이므로 S001의 저장 ranking을 그대로 재사용하며 이 제한을 결과에 명시한다.

- base config: `experiments/manifests/clean_exp_s005_v3_revert_ablation_v1.json`.
- allowed policy changes: S005에서 선언한 v3 specialist 제거 한 가지뿐.
- 출력: `outputs/clean-exp-s028-s027-fresh-dev200-v1/`; response는 exact message+schema
  fingerprint로 checkpoint하며 재실행 시 같은 task만 resume한다.
- 사전 gate: S005 preflight PASS, S027 staged ZIP mock 10건 PASS,
  ZIP 저장응답 replay 200건/49열·S005 counterfactual difference 0.
- semantic-input: S027의 r10/B/C24/v19 모든 prompt bytes는 S001과 동일하다.
  따라서 24개 final v의 cards/metadata/product/source 입력 계약은 S001과
  동일하고, v3 final owner만 r10으로 되돌린다. prompt의 새 수정은 없다.
  exact rendered short/attachment/overflow는 S001 base 및 v19 실험 산출물에
  보존된 동일 task hash에 대응한다. 금번 신규 호출 전에 archive task hash
  audit가 base 600/600, v19 165/165를 확인했다.
- 결과: dev200·fast20·holdout20 Macro 및 per-item TP/FP/FN,
  invalid/retry/호출수/시간, 49열/evidence를 저장한다. 이미 adaptive한 dev200이므로
  public 성능 추정으로 부르지 않는다.
- 실제 evaluator vLLM 시간은 OpenRouter 시간으로 추정하지 않는다.

## 완료 결과

`scripts/run_s028_s027_fresh_dev200.py`를 완주했다. 신규 OpenRouter Gemma
639 calls, 954.80초, 전송 오류 0. dev200 Macro positive-F1 0.7894287115,
fast20 0.7325126263, holdout20 0.4305555556. ZIP의 49열 출력과
비어 있지 않은 evidence의 해당 공고 원문 부분문자열 조건 모두 통과했다.
initial 600, invalid retry 37, v19 fallback B 2였고, C24 14개 task는
2회 재시도 후에도 unresolved로 남았으나 제출 코드는 유효한 fallback CSV를
썼다. 완전한 per-item TP/FP/FN은
`outputs/clean-exp-s028-s027-fresh-dev200-v1/run_report.json`에 있다.
저장응답 replay 점수 0.7910823947은 별개이며 이 실행의 점수로 대체하지
않는다. 이 실험은 신규 Gemma 생성의 로컬 dev200 점수지만 BGE는 저장
ranking을 재사용했으며 evaluator vLLM과 public 결과는 미검증이다.
