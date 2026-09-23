# S022 — v5 전체 원문 참가자 소재지 역할 probe

상태: **계획; 유료 실행 전 preflight 미완료**. S003의 500자 단일 구절 역할 probe는 4/8만
맞았고, S021의 기존 regex view는 참인 참가자 제한을 제거했다. 따라서 새 가설은
"공고문과 첨부의 원문 전체, 문서 경계와 주변 section 문맥을 주면 Gemma가 v5의 지역 문구가
참가자의 본점/영업소 제한인지 평가·납품처·현장 문맥인지 더 안정적으로 관찰한다"이다.

이 실험은 **source-role 진단 probe**다. v5 법적 최종 판정, 공식 금액 보정, S001 label,
제출 정책을 변경하지 않는다. 성공해도 Macro-F1이나 public 상승으로 부르지 않는다.

- base config: `experiments/manifests/clean_exp_s001_integrated_v3_v19_v1.json`
- allowed policy changes: `v5_full_source_role_probe`와 `output_dir`만. provider/model/decoding,
  S001 owner, 금액 선택기, 다른 v는 불변.
- panel: S001 dev v5 TP 7건, S020의 hash 고정 비라벨 v5 8건, 그리고 S021의 유지/제거
  결과를 선택 기준으로 쓰지 않고 별도 hash 순서로 고정한 비라벨 v5 8건. 총 23개 notice. 마지막 8건의 원문
  역할은 모델 응답을 저장한 뒤에 사람이 판독한다.
  - dev: `PPS-DEV-07`, `PPS-DEV-045`~`PPS-DEV-049`, `PPS-DEV-057`.
  - S020 비라벨: `source_samples.json`의 owner `v5` 순서 그대로.
  - 새 blind 8건: `PPS-D-003512`, `PPS-D-017997`, `PPS-D-021678`,
    `PPS-D-009424`, `PPS-D-016295`, `PPS-D-017534`, `PPS-D-018798`,
    `PPS-D-010082`. S021의 유지/제거 값과 무관하게 `SHA256(id)` 오름차순으로
    S020 8건을 제외한 나머지 후보 중 첫 8건이다.
- 모든 제공 공고문·첨부를 원문 그대로 tokenizer admission한다. 한 메시지에 넘치면
  공고문 anchor를 각 pass에 유지하고, 나머지 원문 문자 범위를 순서대로 빠짐없이 나눈다.
  pass 출력은 source-only 역할·원문 quote다. 각 pass의 유효한 긍정 관측은 OR로 모으되,
  불명확·malformed를 임의 0으로 바꾸지 않는다.
- 1차 성공 gate: dev 7건의 실제 참가자 지역제한을 7/7 찾고, S020의 명백한 평가/납품처
  2건은 해당 hit를 참가제한으로 오인하지 않으며, S020의 실제 참가자 제한 6건은 6/6
  보존한다. malformed 0/23, source quote exact-valid 100%, source coverage 100%.
- 2차 gate: blind 8건의 원문 역할을 응답 후 독립적으로 판독해 recall/precision을 보고한다.
  이 패널로 population precision을 추정하지 않는다.
- 호출수와 전체 prompt/completion token, OpenRouter wall time을 기록한다. public vLLM
  runtime의 근거로 쓰지 않는다.

유료 호출 전 요구: fully resolved manifest, `preflight_experiment.py` undeclared diff 0,
원본 source/doc-id coverage와 SHA-256 provenance, exact tokenizer, mock, isolated output,
short complete·attachment·overflow rendered system/user의 사람 검토, v5 semantic-input
contract 감사. 이 probe가 v5 최종 법률판정에 필요한 금액/예외를 사용하지 않는다면 그 사실을
명시하고 완결 전략이라고 부르지 않는다. 실행 준비가 완료될 때까지 API 호출하지 않는다.

## 2026-09-23 유료 실행 전 입력 감사

- fully resolved manifest:
  `experiments/manifests/clean_exp_s022_v5_full_source_role_probe_v1.json`.
  preflight `PASS`, undeclared difference 0. frozen v5 positive 23/23 확인.
- tokenizer mock: 23 notices, 24 tasks, admitted 198,546 tokens, overflow 1건.
  모든 실제 문서의 doc-id/SHA-256과 원문 문자 구간을 ledger에 기록했고, pass 합계가
  원문 전체와 정확히 일치한다. `source_ledger.json`, `mock_report.json` 참조.
- 실제 rendered system/user를 읽은 경로와 결론:
  - short complete:
    `outputs/clean-exp-s022-v5-full-source-role-probe-v1/rendered/PPS-D-021678__p01.json`
    — 공고문 D0 전체 0:4388, 3,214 tokens. 참가자 본점 조건과 제출처 주소가 구분되어 있음.
  - attachment:
    `outputs/clean-exp-s022-v5-full-source-role-probe-v1/rendered/PPS-D-018798__p01.json`
    — 공고문 D0 0:3742 + 규격서 D1 0:487, 3,159 tokens. 사양서가 누락되지 않음.
  - overflow:
    `outputs/clean-exp-s022-v5-full-source-role-probe-v1/rendered/PPS-D-009424__p01.json`,
    `.../PPS-D-009424__p02.json` — 공고문 D0 0:3870(3,762 tokens), 과업지시서 D1
    0:22104(14,262 tokens). 둘 다 동일 system과 human metadata를 보며, p2에 공고문
    첫 1,200자 anchor가 반복된다. 실제 원문 구간은 겹치지 않고 누락도 없다.
  - 사람 검토 결론: 세 경로에서 system/JSON 역할 계약이 같고, raw metadata JSON·법령
    원문·사례 corpus는 없다. 필요한 source role을 보여주는 원문이 들어 있다.
- source-role semantic-input contract: 적용 대상은 frozen v5 양성 후보이고, 모델 출력은
  v5가 아니라 `BIDDER_LOCATION/NOT_BIDDER_LOCATION/UNCLEAR`다. 참가자 본점·주된
  영업소의 입찰 전 필수 지역조건이라는 1사실, 평가 가점·과거 납품처·현장·납품지·계약 후
  이용·허용 예시라는 주요 반대사실, 원본 공고문과 첨부, human-readable 계약법·업무·방식·
  가격이 위 rendered message의 system/user에 모두 있다. quote 상한 500자와 exact source
  substring 조건은 system/schema/parser가 일치한다.
- **최종 v5 semantic-input contract는 의도적으로 미완료**: 공식 지역별 금액 selector와
  법적 허용 예외를 판단하지 않는다. 따라서 이번 24-call 결과를 v5 label/F1 또는
  완결 전략의 결과로 보고하거나 제출물에 연결하지 않는다. 이후 완결 후보에는 공식
  threshold·적용 기관·예외를 추가한 별도 manifest와 rendered 감사가 필요하다.
