# S022R — v5 역할 관측의 인용문 직렬화 복구

S022의 24개 저장 응답을 **재호출 없이** replay한다. S022의 strict parser 기준 3건은
role=참가자 소재지 제한이지만, quote에 원문의 줄바꿈·띄어쓰기 차이가 있어 invalid다.
이는 역할 판단의 정확성과 문자열 직렬화를 분리하기 위한 실험이다. S022의 원래 결과를
덮어쓰거나 사후에 성공으로 재명명하지 않는다.

- base config: `experiments/manifests/clean_exp_s022_v5_full_source_role_probe_v1.json`
- allowed policy changes: `v5_role_quote_recovery` 한 가지. prompt/system/user/schema/provider,
  23 notice/24 task, source packs, S001 v5 label은 불변.
- exact-first, 그다음 각 **현재 pass의 실제 원문 document fragment**에서 공백만 제거한
  quote와 일치하는 연속 원문을 찾는다. 복구한 원문은 1~500자여야 한다.
- 여러 document fragment에 후보가 있으면 byte-exact 일치를 우선하고, 그 안에서
  원래 문서 순서의 첫 번째를 선택한다. byte-exact가 없으면 공백 복구 후보 중 문서
  순서의 첫 번째를 선택하고 다중 후보 수를 감사에 남긴다. 이미 strict-valid한
  원문 인용을 바꾸지 않기 위한 우선순위다. 생성 quote를 증거로 출력하지 않는다.
- JSON shape/role/finish_reason/quote 길이는 S022와 동일하게 엄격 검사한다. 실패한
  음성 quote나 semantic role은 바꾸지 않는다.
- 0-call 산출물: `outputs/clean-exp-s022r-v5-quote-replay-v1/report.json`.
- gate: 세 건 모두 변경 없는 실제 원문 substring으로 복구, 다른 21개 role 불변,
  source path/hash·task/response checkpoint 일치. 이는 source-role 진단의 직렬화
  복구이지 v5 법적 최종 판정이나 public 개선 증명이 아니다.
