# N005R: v22 card-defined binary projection replay

작성일: 2026-09-22

N005 fast20은 raw axes에서 TP/FP/FN 1/0/0을 얻었지만 음성 5건을
`U`로 남겼다. 이는 새 semantic hypothesis가 아니라 구현과 사전 계약의
불일치다.

- v31 card의 1 조건은 `negotiated=Y AND briefing=Y AND exclusion=Y`다.
- card의 0 조건은 계약방식 또는 자격제한이 불명인 경우도 포함한다.
- N005 계획은 Python이 `Y/Y/Y`만 v22=1로 투영한다고 선언했다.
- 실제 N005 runner는 어느 축도 N이 아니고 U가 있으면 final state를 U로
  남겨, binary owner 계약을 구현하지 못했다.

N005R은 저장된 N005 response와 exact parser를 고정하고 다음 projection만
적용한다.

```text
v22 = 1 iff negotiated=Y and briefing=Y and exclusion=Y
v22 = 0 otherwise
```

base는 `clean_exp_n005_v22_briefing_fast_v1.json`이다. 허용 변경은
`decision`, `data.responses_path`, `run.mode`뿐이다. prompt, source view,
schema, provider, response, evidence validation은 바꾸지 않는다. invalid
response는 projection하지 않고 replay 자체를 실패시킨다.

fast replay gate는 TP=1, FP=0, FN=0, evidence validity 100%다. 통과하면
별도 holdout manifest를 만들고, 저장 응답이 없으므로 preflight 후 20회만
실행한다. holdout TP=1, FP=0, FN=0, invalid=0일 때만 dev200으로 간다.
