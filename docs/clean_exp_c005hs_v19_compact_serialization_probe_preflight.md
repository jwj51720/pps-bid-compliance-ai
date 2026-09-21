# EXP-C005HS v19 compact serialization target probe preflight

작성일: 2026-09-21

상태: 유료 1-call probe 실행 승인

## 목적과 통제

C005H holdout20에서 두 번 동일하게 completion-length/whitespace loop를 낸
`PPS-DEV-192__p01`만 compact JSON으로 다시 직렬화한다. v19 의미 field 9개, 후보 원문,
법률·역할 지시, provider parameter, 기존 reducer와 quote resolver는 바꾸지 않는다. 정상 17개
응답은 저장본만 사용하며 재호출하지 않는다.

- base manifest: `clean_exp_c005h_v19_requirement_holdout_v2.json`
- resolved manifest: `clean_exp_c005hs_v19_compact_serialization_probe_v1.json`
- 허용 변경: `layers.decisions`, `v19_compact_probe`, `v19_quote_replay`,
  `runtime.expected_calls_per_record`
- 최대 신규 호출: 1
- 출력 위치: `outputs/clean-exp-c005hs-v19-compact-serialization-probe-v1/`

## 입력 및 provenance 검증

- 기존 C005H verbose task hash: `73f45511372b5d0d815ee32ac955f6299a240afeb9821b9bdeea7a0941b3461e`
- 재구성 verbose task hash: 동일
- user message: byte-identical, SHA-256
  `f303a4a85fd8ef4c3ad874a02b912a22589a61dcb7ef8f4bf24b10b076505ae9`
- semantic system prefix: byte-identical, SHA-256
  `61910aee1b443b3eb23b92b632093693a26b2cc1e4b38e65138fa089fc74a0b1`
- 후보: `R01`, `공고문 D0`, 위치 `1671~3073`
- 후보 원문 SHA-256:
  `b0a3861c7c2090c982e5a54e3e8f8ddaa61af8a7f6a83d84e9a9173672bdcae3`
- compact tokenizer count: 1,995 / 14,848
- 전체 C005H holdout task: 18; 무호출 저장 응답: 17

실제 rendered message는
`outputs/clean-exp-c005hs-v19-compact-serialization-probe-v1/rendered_inputs/probe_PPS-DEV-192__p01.json`
에 있다. 이 probe는 고정된 실패 target 한 건만 다루므로 short/attachment/overflow 세 표본을 새로
선택하는 실험이 아니다. C005H가 이미 holdout 전체 source coverage와 task hash를 고정했고,
C005HS는 그중 한 task의 user와 semantic system prefix가 동일함을 직접 검증한다.

## 사람 검토 결론

rendered system/user/schema를 직접 읽었다.

- user에는 organizer v19 적용범위, 1 조건 두 가지, 중요한 0 조건·예외가 모두 있다.
- 실제 `R01` 원문에는 입찰보증금 전자양식 납부확약이 있으며, 외부 제조사·공급사의
  물품공급·기술지원 이행보장과 구별할 수 있는 문맥이 충분하다.
- 모든 9개 semantic field가 compact schema에서 required다.
- 추가 system suffix는 key/enum code의 1:1 대응만 설명하며 새 판단기준이나 default를 넣지 않는다.
- raw metadata, 법령 원문, legacy prompt/code는 없다.
- 이 target은 공고문 1개에서 나온 후보이므로 attachment 누락이나 overflow split이 없다.

결론: semantic-input contract와 exact tokenizer admission은 PASS다.

## 기계 검증

- `scripts/preflight_experiment.py`: PASS, undeclared/unused change 0
- target probe preflight: PASS
- mock compact parse → verbose adapter: PASS
- 전체 pytest: 61 passed
- legacy import/실행/생성: 없음

## 실행 후 gate

compact response가 `finish_reason=stop`, exact candidate keys, 9 required fields를 만족하고 verbose
adapter까지 통과해야 한다. 이후 정상 17개 저장 응답과 합쳐 invalid 0, non-v19 changed cells 0,
holdout v19 FP 1 이하일 때만 C005HS를 성공으로 기록한다. 실패하면 추가 동일 retry 없이 C005
family를 종료하고 dev200으로 확장하지 않는다.
