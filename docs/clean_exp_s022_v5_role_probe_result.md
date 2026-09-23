# S022/S022R v5 원문 역할 탐침 결과

2026-09-23. 이 실험은 **source-only 역할 관측**이며 v5의 금액·예외를 포함한 최종 법률
판정이나 public 점수 실험이 아니다. 기준 제출 정책·최종 라벨은 바꾸지 않았다.

S022는 고정 23공고를 전체 제공 원문으로 24회 호출했다. dev 양성 7건, 앞서 검토한 비라벨
8건, 결과를 보지 않고 고정한 비라벨 8건이다. 원문 coverage·task hash·token admission·
short/attachment/overflow rendered input은
`docs/clean_exp_s022_v5_full_source_role_probe_plan.md`와
`outputs/clean-exp-s022-v5-full-source-role-probe-v1/`에 기록했다. 실제 유료 실행은
26.27초, prompt usage 198,571 tokens, completion 1,498 tokens이었다.

엄격한 exact-substring parser의 최초 결과는 **21/24 valid, 3/24 invalid**로 사전 설정한
malformed=0 gate를 통과하지 못했다. 세 건은 역할 필드는 정상적으로 출력했지만 원문의
줄바꿈·공백을 바꾼 인용이었다. 따라서 S022를 소급하여 통과 실험으로 부르지 않는다.

별도 S022R은 저장된 응답만 0회 호출로 replay했다. 원문 byte-exact 우선, 그렇지 않으면
현재 pass의 실제 source fragment에 대해 유일한 공백 정규화 대응을 찾아 **변경 없는 원문
부분문자열** 1~500자로 복원한다. task/response/source ledger hash를 확인했고 세 인용은
모두 복원됐다. 기존 valid 21건의 역할·인용은 불변이며 남은 invalid 0, 최종 v5 label
변경 0이다. 한 사례는 두 문서에 공백 복원 후보가 있어 첫 원문 문서가 선택됐고 후보 수 2를
기록했다. 산출물은 `outputs/clean-exp-s022r-v5-quote-replay-v1/report.json`이다.

복원 후 23공고의 source-role 출력은 참가자 소재지 제한 21, 다른 역할 2였다. dev 양성
7건은 모두 전자였고, 앞서 원문 검토한 평가 가점·과거 납품처 2건은 후자였다. blind 비라벨
8건은 모두 전자였으며 이 panel에는 명확한 역할 음성이 없다. 이 수치로 v5 precision,
public F1, 또는 Python guard 효과를 추정할 수 없다. 특히 20,000건은 정답이 없고 모집단
발화율 차이만으로 과적합 규칙을 특정할 수 없다.

다음 단계는 v5 prompt를 반복 수정하는 것이 아니다. 먼저 전체 Python owner군의 기존
source-role 표본을 같은 기준으로 묶어 오류 유형·모집단 노출·대체 owner의 존재를 비교한다.
v5는 독립적인 음성/경계 strata의 고정 panel에서 역할·malformed·호출시간을 검증하기
전까지 final gate로 통합하지 않는다. 공식 지역금액 selector는 이 역할 탐침과 별도 변경이다.
