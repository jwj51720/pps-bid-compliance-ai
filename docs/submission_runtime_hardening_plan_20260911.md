# Submission runtime hardening plan

작성: 2026-09-11, dev / mac

## 목적

EXP171 ZIP은 120분 제한을 넘겼지만 현재 로그만으로 loading, admission, stage-1,
final, retry 중 어느 구간이 병목인지 알 수 없다. 또 shared loader는 organizer README와
공식 baseline이 요구하는 최소 `id/docs/meta`보다 조립 부가필드까지 필수로 요구하고,
`PPS_QUANT=none`을 vLLM에 문자열 그대로 넘긴다. 이들은 모델 품질과 무관한 실행 취약점이다.

이번 변경은 prompt, source scope, label, merge, evidence, card를 바꾸지 않는 submission runtime
hardening이다.

## 변경

1. shared loader의 필수 record key를 공식 최소 계약인 `id/docs/meta`로 맞춘다. 알려진 optional
   assembly field가 존재하면 타입을 검증하되, hidden input에 부가필드가 없다는 이유로 중단하지
   않는다. 데이터 품질 전수 감사는 organizer 공개 파일의 완전 schema를 계속 별도로 요구한다.
2. `PPS_QUANT=none` 또는 빈 문자열을 baseline과 동일하게 Python `None`으로 정규화하고,
   quantization이 없을 때 vLLM keyword를 생략한다.
3. submission stderr에 model load, input load, pipeline preparation, stage-1 generation,
   final generation, CSV validation의 phase별 wall time과 request/output 개수를 기록한다.
4. 문서화된 submission 기본 batch size를 baseline과 같은 128로 복원한다. 이는 call 수를
   바꾸지 않으며 GPU throughput 개선을 보장한다고 주장하지 않는다. GPU에서 64/128을 직접
   비교할 수 없으므로 제한으로 기록한다.

## 검증

- 최소/완전 record schema, malformed optional field unit tests
- quantization `none`/empty/default unit tests without importing vLLM
- batch cardinality와 phase counter tests using mock client
- canonical/runtime packaging parity
- exact staged ZIP mock 10건, 49열/ID/evidence
- full pytest

GPU/vLLM이 없는 현재 환경에서는 실제 throughput과 120분 이내 완료를 검증했다고 주장하지
않는다. 다음 GPU 실행은 phase log가 남는 archive로만 수행한다.
