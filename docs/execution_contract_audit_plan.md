# Execution-contract audit 계획 — 다음 대형 가설

## 문제 정의

현재 local experiment와 public 관측이 맞지 않는다.

- 우리 EXP123: local dev200 `0.317797` → public `0.260446`.
- 동료가 전달한 거의-vanilla 단일-call prompt: public 약 `0.32734`.
- WSL EXP120 card-v6 4k 단일-call: public `0.244317`.

동료의 source/zip은 아직 없으므로 점수 자체를 재현하거나 특정 문구를 원인으로 단정할 수 없다.
그러나 이번 branch에서 실제 결함 하나를 확인했다. historical EXP109은 metadata를 JSON block으로
넣었고 submission entrypoint도 `metadata_style`을 전달하지 않아, organizer baseline과 다르게
동작했다. 현재 source는 이를 고쳤지만 staged `submission/build/final_exp109...`은 여전히 이전
runtime config를 보유한다.

따라서 다음 대형 가설은 “새 법령/사례 지식”이 아니라 다음이다.

> **prompt source, shared pipeline, staged zip, organizer baseline, offline vLLM runtime 사이의
> 실행 계약 차이가 local/public gap과 제출 재현 불가의 일부를 만든다.**

이는 feature를 더 넣는 실험이 아니다. 어떤 생성 실험도 하기 전에 실제 제출 artifact가
무슨 message/schema/admission/runtime으로 작동하는지를 확정하는 재현성 작업이다.

## A0 — 무호출 source-to-zip audit

1. canonical `config.yaml`, `submission/runtime_config.json`, `submission/script.py`가 모든
   prompt policy field를 같은 shared `BaselinePipeline` constructor에 전달하는지 확인한다.
2. `scripts/make_submission.py`로 fresh staged tree와 timestamped zip을 만들고, stale staged tree와
   구별한다. zip 내부 파일 hash와 runtime policy를 manifest로 기록한다.
3. organizer baseline `data/raw/open/baseline/script.py`와 current canonical policy의 system/user
   message를 fixed dev record에서 byte-level compare한다. 차이가 있다면 policy 의도인지,
   실수로 빠진 forwarding/default인지 분류한다.
4. fresh staged entrypoint를 `--mock`으로 실제 PPS path contract에서 실행한다. 49-column CSV,
   row count, evidence validation을 확인한다.
5. historical submission zips/stages는 audit-only로 구분한다. 현재 source와 다른 runtime config를
   가진 archive를 새 canonical candidate로 오인하지 않는다.

## A0 산출물과 판단

- tracked: 이 계획과 결과 문서, source-level regression test, policy forwarding code
- ignored: staged zip, mock CSV, file-hash/runtime manifest

발견된 mismatch는 **수정 후 mock/staged validation까지** 완료한다. 하지만 exact-contract repair는
성능 개선 주장이나 dev200 실행의 근거가 아니다.

## A1 — 생성 호출 전 독립 입력 실험의 조건

A0에서 current prompt contract가 확정된 뒤에만, prompt content 하나만 바꾼 label-blind fast panel
experiment를 설계한다. control과 treatment는 document admission, V/E schema, decoder, evidence
resolution, merge, cards, metadata renderer를 동일하게 둔다. fast-panel이 방향을 보이면 독립 cohort,
그 뒤 dev200으로 간다. 단일-call runtime 예산을 넘기는 topology는 승격하지 않는다.

## 명시적 제외

- S0C가 반증한 self-label fact/case retrieval 확장
- raw law bundle/RAG 재주입
- dev error를 겨냥한 item-level threshold/override
- full-split × item grouping처럼 호출 수를 곱하는 구조
- exact runtime evidence 없이 local F1만으로 submission policy를 바꾸는 일
