# S003 — 지역 문구 역할 source-only micro 진단

상태: 사전 계획. 유료 호출 전 gate가 모두 PASS해야 한다.

## 가설

S002의 숫자 교정만으로 생긴 비라벨 신규 양성 11건은 source predicate가
입찰참가자격, 평가 가점, 현장·운반거리, 낙찰 후 협조를 구분하지 못해서 생겼다.
Gemma에게 **정확히 하나의 원문 발췌**를 주고 법률 위반 여부·금액을 묻지 않은 채
문구 역할과 제한 지역단위만 구조화하게 하면, 새 양성을 만들기 전 필요한 관계형
사실을 1회 저비용 호출로 수집할 수 있을 것이다.

이 micro는 최종 v5/v6 판정 전략이 아니다. 원문 전체·금액·기관유형·예외를
동시에 보는 final message가 없으므로 F1을 계산하거나 S001의 셀을 변경하지
않는다. 의미적 입력 완결성을 주장하지 않는 의도적 진단 probe다.

## 변경 통제·패널

- base config: `experiments/manifests/clean_exp_s002_regional_threshold_audit_v1.json`
- allowed changes: `micro` 추가만. provider·카드·merge·최종 owner 변경 0.
- output: `outputs/clean-exp-s003-region-role-micro-v1/`
- 8건 고정:
  - dev v6 source-view 누락: PPS-DEV-061, PPS-DEV-071
  - 비라벨 source 검토: PPS-D-002806, PPS-D-011172,
    PPS-D-002375, PPS-D-011290, PPS-D-020371, PPS-D-001559
- 비라벨 6건은 S002 review ledger가 가리키는 원문 발췌를 **원문 substring으로
  재검증**해 입력한다. dev 2건은 동일한 label-blind source line selector를 쓴다.
- 사람이 원문에서 본 역할: dev 2건은 참가자격·기초, train 002375/011290/020371은
  참가자격·시도, train 002806/011172는 평가, train 001559는 현장·운반거리.
  이는 micro의 진단 대조표이지 모델 입력이나 제출 정책이 아니다.

## 유료 전 gate

1. 원본 JSONL hash·ID·doc_id·source offset·exact substring coverage 100%.
2. exact Gemma tokenizer로 모든 8개 rendered task `<=14848`. excerpt 밖의 원문
   생략을 ledger에 명시한다.
3. 짧은 완전 공고, full-source라면 overflow인 공고, 첨부 포함 공고의 **실제
   rendered system/user**와 schema를 파일로 export하고 직접 읽는다.
4. source-only task의 입력 계약은 해당 발췌의 참가자 역할, 시·도/기초 단위,
   평가·현장·낙찰 후 문맥이다. v5/v6 적용 계약법·가격·예외를 넣지 않으므로
   active final-v semantic contract가 아니다. 최종 판정 후보를 만들 때는 v5/v6
   organizer source·0/1 조건·metadata·첨부 coverage를 별도로 완결한다.
5. `scripts/preflight_experiment.py` undeclared diff 0, mock 8건 schema parse·
   source quote check PASS, 비용·call budget 재확인.

## 호출·판정 gate

- 초기 호출 8회, model/provider 설정은 base와 동일. response마다 atomic
  checkpoint; 5회마다 malformed·token·elapsed·역할별 현재 혼동표를 기록.
- schema invalid·원문에 없는 quote·빈 response는 각각 별도 오류. micro에서는
  같은 task를 자동 재시도하지 않고 실패율을 그대로 측정한다.
- 8건 중 최소 7건의 역할, 5건의 참가자격 사례 중 최소 4건의 지역단위가
  source review와 맞고, invalid 0건이어야 후속 fixed fast20 입력 설계를 검토한다.
  표본이 작으므로 통과해도 정확도나 public 이득은 주장하지 않는다.
- 기각이면 v5/v6 신규 Gemma call은 넣지 않는다. S002의 금액 fact만 보존하고
  다음 점수 기회 또는 serialization/runtime 실험으로 우선순위를 옮긴다.

## rendered review

사전 gate 2026-09-22:

- preflight: `outputs/clean-exp-s003-region-role-micro-v1/preflight.json` PASS,
  undeclared difference 0. `scripts/run_region_role_micro.py --mock` 8/8 PASS,
  총 admitted prompt 2,913 tokens. 원본 문서 SHA·doc ID·offset·exact substring은
  `source_ledger.json`에 8/8 기록돼 있다.
- short complete source case `PPS-DEV-061` (원문 전체 약 2,006 tokens):
  `outputs/clean-exp-s003-region-role-micro-v1/rendered/PPS-DEV-061.json`,
  실제 source-only message 271 tokens.
- attachment case `PPS-D-002375` (문서 2개, 원문 전체 약 8,466 tokens):
  `outputs/clean-exp-s003-region-role-micro-v1/rendered/PPS-D-002375.json`,
  실제 source-only message 336 tokens.
- overflow+attachment case `PPS-D-011172` (문서 4개, 원문 전체 약 20,884 tokens):
  `outputs/clean-exp-s003-region-role-micro-v1/rendered/PPS-D-011172.json`,
  실제 source-only message 390 tokens.
- system/user/schema 세 파일을 직접 읽었다. 평가 가점인 `PPS-D-011172`는
  참가자격으로 오인하기 쉬운 `지역업체참여도`가 있어 역할 진단에 적합하다.
  단, **세 rendered message 모두 전체 공고가 아니라 1개 발췌만 포함**한다.
  이것은 micro의 의도적 입력 축소이며 final v 의미 입력 완결성 증거가 아니다.
  최종 v5/v6 owner 전에는 모든 원문·metadata·공식 금액·소액수의 예외를 포함한
  별도의 item별 contract audit가 필수다.
