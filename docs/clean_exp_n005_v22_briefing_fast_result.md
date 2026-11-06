# N005/N005R native v22 fast20 result

작성일: 2026-09-22

N005 raw observation은 TP/FP/FN 1/0/0, positive F1 1.0, invalid 0을
기록했다. 다만 음성 5건이 raw U여서 최초 gate는 통과하지 못했다.
네 건은 설명회 사실이 없었고, 한 건은 설명회는 있으나 참가배제 여부가
불명했다.

원인은 source나 모델 오류가 아니라 reducer 구현 불일치였다. v31 card와
사전 계획은 세 축이 모두 Y일 때만 1이고, 계약방식·자격제한이 불명이면
0이라고 정한다. 그러나 N005 runner는 U를 binary 0으로 투영하지 않았다.

이를 별도 N005R manifest에서 저장된 20 responses를 그대로 replay했다.
prompt/source/schema/provider/response는 바꾸지 않았고 card-defined binary
projection만 선언했다.

| 결과 | 값 |
| --- | ---: |
| TP / FP / FN / TN | 1 / 0 / 0 / 19 |
| v22 positive F1 | 1.0 |
| raw U | 5 |
| invalid | 0 |
| positive evidence validity | 100% |
| 새 model calls | 0 |

N005R fast binary gate는 통과했다. 다음은 별도 holdout20 20회이며, 같은
prompt/source/schema/provider와 binary projection을 고정한다.

근거:

- `outputs/clean-exp-n005-v22-briefing-fast-v1/fast20/run_report.json`
- `outputs/clean-exp-n005r-v22-binary-projection-replay-v1/fast20/run_report.json`
