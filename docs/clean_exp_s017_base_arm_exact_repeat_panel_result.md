# S017 — base r10/B/C24 hash-fixed exact-repeat micro panel 결과

실행일: 2026-09-23

상태: **PASS — 6개 task final 변화 0, JSON fence 한 건은 S017R로 분리**

## 무결성

- selected notices: label/response blind 2건
- repeated tasks: 2 notices × r10/B/C24 = 6
- task hash: frozen baseline과 6/6 exact match
- tokens: 3,761~7,512 / 14,848
- source ledger: notice-only 1/1문서, attachment 3/3문서
- transport: stop 6/6, invalid=false 6/6
- prompt tokens: 34,574
- completion tokens: 587
- output:
  `outputs/clean-exp-s017-base-arm-exact-repeat-panel-v1/run_report.json`

## raw와 final 전파

| task | raw content | strict parse | S001 V change | evidence change |
|---|---|---|---:|---:|
| r10/PPS-DEV-21 | different | fallback — JSON fence | 0 | 0 |
| B/PPS-DEV-21 | exact equal | valid | 0 | 0 |
| C24/PPS-DEV-21 | exact equal | valid | 0 | 0 |
| r10/PPS-DEV-04 | different | valid | 0 | 0 |
| B/PPS-DEV-04 | exact equal | valid | 0 | 0 |
| C24/PPS-DEV-04 | exact equal | valid | 0 | 0 |

joint replacement도 S001 V/E changed cell 0, Macro delta 0이었다. 그러나 r10/PPS-DEV-21은
fallback 때문에 semantic stability를 직접 평가하지 못했으므로 S017 자체만으로 base generation이
안정적이라고 결론내리지 않았다.

## S017R 필요성

r10/PPS-DEV-21 raw content는 완전한 schema object를 단일 `json` fence로 감싼 형태였다. 내부는
v3/v4/v23에 일부 `U`를 출력해 원 response의 `N`과 의미가 달랐다. 따라서 fallback이 변화 전파를
숨겼는지 별도 0-call replay에서 확인한다.
