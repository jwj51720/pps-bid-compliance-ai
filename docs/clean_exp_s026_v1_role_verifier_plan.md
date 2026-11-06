# S026 — v1 Python 양성의 전체 원문 참가자 역할 확인

작성일 2026-09-23. **새 제출 후보의 한 가지 정책 변경**을 시험한다.

## 가설과 근거

S001 v1 최종 양성은 Python의 같은-문장 lexical detector가 단독 소유한다. dev200
TP/FP/FN=7/0/0이라 로컬 점수만으로 보수적 gate를 고를 수 없다. S020의 고정 비라벨
양성 8건 중 `organization_only` 경로의 네 건에서는 허용/일반 등록/다른 주체의
참여를 특정기관 참가제한으로 읽었다. S024의 첨부-only 후보에서도 같은 역할
혼동이 반복됐다. **이 경로**의 실제 truth condition인 특정 기관군만 입찰자로
참가 가능은 단어가 같은 줄에 있다는 사실만으로 표현되지 않는다.

중요한 사전 결함 발견: 첫 설계는 v1의 모든 Python 양성을 역할 gate로 대체하려
했으나, dev TP 7건 중 3건은 `preheld_capacity`/`all_manufacturer_registration`
경로다. 항목표 이름/카드의 기관 제한 문구만 보고 이 3건을 0으로 내리면
organizer dev 정답과 충돌한다. 따라서 **유료 실행 전에** 범위를
`organization_only` 후보로만 축소하고 나머지 v1 경로는 보존했다. 이
선택은 특정 dev ID의 문구 patch가 아니라 frozen owner가 이미 구분한
truth-condition별 경로 분리다.

## 변경 경계

- base config: `experiments/manifests/clean_exp_s001_integrated_v3_v19_v1.json`.
- allowed policy changes: `v1_positive_source_role_verification` 한 가지.
- S001의 v2~v24, F/S/R, r10/C24/v3/v19 프롬프트·schema·reducer·provider·evidence
  및 기존 661 initial call topology는 불변.
- v1 Python의 `organization_only` subtype인 공고에만 별도 source-only Gemma task를
  실행한다. 다른 v1 subtype은 기존 결과를 그대로 보존한다. 실제 원문은 공고문,
  규격서, 과업지시서, 제안요청서, 예외공표서 순으로 모든 제공 문서를 포함한다.
  exact tokenizer 14,848 prompt budget을 넘으면 source coverage를 유지한 ordered
  pass로 나누고 각 pass의 원래 문서/오프셋을 기록한다.
- 출력은 `EXCLUSIVE_BIDDER_ORGANIZATION`, `NOT_EXCLUSIVE`, `UNCLEAR`와 source quote.
  **모든 pass가 정상·명확한 NOT_EXCLUSIVE**일 때만 기존 v1=1을 0으로 강등한다.
  어느 pass라도 EXCLUSIVE 또는 UNCLEAR/invalid라면 기존 v1=1을 보존한다.
  이는 recall 보호 우선이며 새로운 양성을 만들지 않는다. 기존 v1=0은 변경하지 않는다.
- positive quote는 현재 pass의 실제 문서에서 1~500자 변경 없는 substring으로
  검증한다. 생성 quote의 공백 차이는 exact-first·unique-whitespace source
  resolution만 허용하며 다른 글자 변경은 invalid다. evidence는 기존 S001 e1을
  유지하고 label 0일 때만 비운다.
- 실제 문서의 특정 기관 한정과 일반 면허·등록·제조사 등록·시설 선보유,
  참가 허용, 평가위원/관람객/계약 후 수행 인력의 자격을 분리한다. 이 작업은
  최종 법률 위반/허용 예외 판단이 아니라 원문 역할 관측이다.

## 실행 gate

1. 고정 panel: dev v1 `organization_only` 양성 4건, S020의 같은 subtype 역할
   검토 비라벨 4건, 결과를 보지 않고 hash로 고른 같은 subtype 비라벨 8건.
   `S020` 원문 역할 결과를 blind panel의 정답처럼 쓰지 않는다.
2. 유료 전 source hash/provenance, 모든 문서·문자 span coverage, exact tokenizer,
   mock, isolated output, preflight undeclared diff 0. short complete, attachment,
   overflow 공고의 **실제 rendered system/user**를 사람이 읽고 경로·결론을 기록한다.
3. semantic-input contract: v1 적용 범위, 특정기관만의 입찰 참가조건,
   일반등록/허용/다른 주체/예외, 공고문 및 모든 첨부, 필요한 human-readable
   계약법/계약방법 metadata를 organizer 항목표·카드 v6와 rendered span에 대조한다.
   다른 23개 v의 final message는 S001 그대로이며 여기서는 재판정하지 않는다.
4. micro 16건에서 dev 4 TP 역할 보존, 기존 역할 음성 4건 중 최소 3건
   NOT_EXCLUSIVE, blind 8건에서 원문과 모순되는 명백한 역할 false veto 0,
   invalid 0 또는 사전 선언한 exact source quote recovery로 0에 수렴해야 한다.
   어느 하나라도 실패하면 제출 통합하지 않는다.
5. 통과하면 동일 정책을 fixed fast20→기존 dev holdout20→dev200에서 실행하고,
   새 ZIP exact staged mock, 49열/evidence, 추가 logical calls·batch·예상 120분
   runtime을 검사한다. 이 dev 계열은 이미 adaptive라 public 개선 증명이 아니다.

## 유료 실행 전 실제 입력 검토 (2026-09-23)

- exact rendered short complete:
  `outputs/clean-exp-s026-v1-role-verifier-v1/rendered/PPS-DEV-035__p01.json`.
  system의 실제 입찰자 기관 한정/일반 등록 구분과 user의 계약법·방법·원문 D0가
  함께 나타난다. 기관 한정 문구는 현재 pass D0의 원문에 있다.
- exact rendered attachment:
  `outputs/clean-exp-s026-v1-role-verifier-v1/rendered/PPS-D-002539__p01.json`.
  D0와 D1이 문서 ID·원문 문자범위와 함께 들어간다. 첨부의 일반 참여/납품
  문구를 기관 종류만의 입찰자 독점과 혼동해서는 안 된다.
- exact rendered overflow:
  `outputs/clean-exp-s026-v1-role-verifier-v1/rendered/PPS-D-004681__p01.json`,
  `outputs/clean-exp-s026-v1-role-verifier-v1/rendered/PPS-D-004681__p02.json`.
  D0 전체와 D1 연속 span이 모두 실리며, 두 번째 pass의 D0 앞부분은 중복
  anchor라고 명시된다. D1의 산학협력단·의료기관 등은 더 넓은 조항 안의
  참가 허용 문맥이므로 배타적 기관 제한으로 판정해서는 안 된다.
- 위 세 유형 모두 system/user 전문을 확인했다. 각 문서의 span 합집합과
  SHA-256은 `source_ledger.json`에 있고, tokenizer-admitted 22 tasks 모두
  14,848 budget 이하이다. mock은 16 notices·22 tasks·0 API calls로 PASS.

Semantic-input contract: organizer `data/raw/open/data/항목표.json` v1은
「참가자격 특정기관 제한」이며, `data/derived/decision_cards_v6.json` v1은
특정 기관군만 실제 참가할 수 있는 1조건과 일반 면허·등록·보안 적합성 등의
0조건을 명시한다. 이 probe는 그 중 **실제 입찰자 역할 사실만** system에 옮긴
것으로 법률 허용 사유를 결론 내리지 않는다. 해당 source-only 단계에서 필요한
공고문 및 첨부 전체, human-readable 적용계약법·업무구분·계약방법·낙찰방법·
추정가격은 위 rendered user의 정확한 span에 존재한다. 최종 v1의 기관 이외
`preheld_capacity`·`all_manufacturer_registration` 경로와 v2~v24 판정
입력은 base S001 그대로 보존한다. 따라서 24개 v의 final semantic-input
contract를 변경하는 제안이 아니다.

비라벨 20k는 역할 오류의 *노출*을 재는 데만 쓰며, precision/F1로 환산하지 않는다.
한 v item의 Macro 개선 상한은 1/24이므로 S026이 public-local 전체 괴리를
해결한다고 주장하지 않는다. 유료 실험 단계별 결과는 새 output에 checkpoint한다.

## 실행 결과 — 제출 통합 기각 (2026-09-23)

`outputs/clean-exp-s026-v1-role-verifier-v1/report.json`: 16 notices, 22 calls,
32.43초 remote 경과, prompt admitted 202,749 tokens, 응답 invalid 9.
8건은 모델이 JSON을 Markdown fence로 감싸서 현재 strict parser가 거부했고,
1건은 원문에서 회수할 수 없는 quote였다. 이는 사전 선언한 `invalid 0` gate 실패다.
fence만 기계적으로 제거해 살펴도 S020 기존 역할 음성 4건 중
`PPS-D-004681`만 NOT_EXCLUSIVE가 되고, `PPS-D-008859`는 지역 제한,
`PPS-D-016235`와 `PPS-D-021891`는 일반 등록/소기업 조건을
EXCLUSIVE_BIDDER_ORGANIZATION으로 오인했다. 요구한 최소 3/4와 거리가 멀다.
dev 기관경로 양성 중 `PPS-DEV-01`은 fence 제거 시 EXCLUSIVE이며 나머지
3건도 EXCLUSIVE였다. 그러나 이는 adaptive dev TP 보존 진단에 불과하다.

**결론: S026은 실패한 진단 실험이며 ZIP/최종 정책에 통합하지 않는다.**
새 parser나 프롬프트 수정을 이 결과에 이어 덧붙이는 것은 별도 가설·manifest·
사전 입력 검토를 요구한다. S025의 동일-content ZIP 역시 제출 금지다.
