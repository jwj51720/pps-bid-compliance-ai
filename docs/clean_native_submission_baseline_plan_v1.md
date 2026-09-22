# Clean native submission baseline plan v1

작성일: 2026-09-21

## 1. 목표와 정직한 기준선

품질 회귀 기준은 C005D dev200 Macro positive-F1 `0.8151465658238104`다. 이 값은 유효한 로컬
품질 결과지만 아직 제출 후보 점수가 아니다.

- frozen L41의 23개 owner 결과를 저장 상태로 재사용했다.
- v19 owner만 165개 candidate notice에 추가 실행했다.
- 새 평가 데이터에서는 frozen baseline 3-arm과 v3/v19 specialist를 모두 새로 계산해야 한다.
- evaluator vLLM 2시간 제한과 clean submission adapter는 검증되지 않았다.

따라서 `dist/reference/submit.zip`, 그 extracted source, 또는 legacy code를 포함한 ZIP을 C005D
제출물이라고 부르지 않는다. 동료 artifact의 문구·변수명·구조를 표현만 바꿔 유사도를 낮추는
작업도 하지 않는다. 제출 기준선은 organizer 자료와 이 저장소의 versioned decision contract를
바탕으로 독립 작성한다.

독립 작성은 기존 문장의 동의어 치환이 아니다. 먼저 organizer 근거에서 각 항목의
적용 범위·양성 조건·실질적 예외를 표준화하고, 그 관계를 표현하는 자체 입력
섹션과 typed 출력 계약을 설계한다. 검증된 source view와 호출 topology는
성능상 출발점으로 삼되, 문구·변수명·파일 구성을 닮게 만드는 것은 목표가 아니다.
새 prompt의 영향은 한 번에 한 owner 또는 한 계약 요소씩 측정한다. 이를 통해
성능 저하가 발생한 필드를 특정하고, 독립성이 확보되었다는 이유만으로 낮은
성능을 기준선이라고 선언하지 않는다.

## 2. 불변 독립성 계약

새 submission과 그 실행 경로는 다음을 만족해야 한다.

1. import root는 `src.pps_ai`뿐이다.
2. `legacy/`, `dist/reference/`, frozen loader를 import·실행·복사·패키징하지 않는다.
3. prompt는 organizer 항목표, 검증된 decision cards, human-readable metadata/product facts로
   새로 작성한다. reference prompt의 문장별 paraphrase를 하지 않는다.
4. 모든 24개 owner와 merge/evidence 경로를 active native module이 소유한다.
5. `PPS_DATA_DIR`, `PPS_OUTPUT_DIR`, `PPS_MODEL_DIR`, `PPS_EMBED_DIR`만 사용한다.
6. test notice마다 실제 문서를 포함한 성공 Gemma call이 최소 한 번 존재한다.
7. offline/no-network, 49열, evidence substring 500자, 설치 10분, 추론 2시간 규칙을 staged ZIP
   자체로 검증한다.

## 3. 구현 순서

### N1. Native input and fact contract

- strict organizer JSONL ingest와 document-order ledger는 현재 active 구현을 유지한다.
- 필요한 metadata를 item별 human-readable fact로 render한다.
- 경쟁제품 exact-code index와 특이사항을 package asset으로 고정한다.
  metadata 코드뿐 아니라 모든 제공 문서의 10자리 코드 언급을 별도
  `SourceSpan` 사실로 수집한다. 문서 코드의 역할(실제 구매대상·직접생산
  참가요건·예시)은 이 단계에서 Python이 확정하지 않는다.
- raw metadata JSON/internal status/code array를 prompt에 노출하지 않는다.
- 24개 semantic-input contract를 organizer source와 exact rendered span에 연결한다.

Gate: 200/200 records, 모든 제공 문서 hash/순서 보존, active v별 필수 fact 누락 0.

### N2. Native source views and owners

- C004S의 native v3 monetary owner와 C005D의 native v19 requirement owner는 이미 독립 구현된
  자산으로 재사용한다. 단, 둘 다 후보 부재·미해결 시 frozen 판정으로 돌아가는 조건부 hybrid였으므로
  해당 fallback을 제거하고도 필요한 사실·호출·최종 판정이 완결되는지 별도로 검증해야 한다.
- 나머지 22개 owner는 organizer truth condition에서 새로 구현한다.
- Python은 exact 사실, source 연결, 명시적 수치식만 계산한다.
- 역할·예외·필요성 같은 의미 판단은 typed Gemma observation으로 받는다.
- v10–v18에서는 metadata 코드 부재를 비경쟁제품 증명으로 쓰지 않고,
  문서 코드와 실제 조달대상의 관계 및 CSV `특이사항` 적용성을 owner가
  원문과 함께 판단한다.
- selector 미탐지나 malformed response를 0으로 간주하지 않는다.

Gate: item별 unit fixture, label table을 코드 상수/keyword로 사용한 흔적 0, legacy/reference import 0.
현재 owner별 실제 공백과 점수 보존의 산술적 제약은
`docs/clean_native_owner_critical_path_v1.md`를 기준으로 추적한다.

### N3. Runtime topology

품질식과 runtime 식을 분리한다.

```text
Macro = sum(F1_v1 ... F1_v24) / 24
logical calls = sum(notice contexts x active groups) + conditional recovery calls
```

batch size는 logical calls를 줄이지 않으므로, 우선 공고당 native core call 1회와 candidate가 있는
v3/v19 specialist의 조건부 call만 비교한다. 문서 overflow가 있는 공고만 추가 context를 허용하며,
v-group과 document split을 곱하지 않는다.

Gate: exact tokenizer admission, document-context count/type, calls per notice와 전체 calls를 preflight에
기록. evaluator 규모에서 2시간 이내라는 보수적 추정이 없으면 package하지 않는다.

### N4. Quality promotion

독립 prompt는 serialization-only 변경이 아니므로 C005D stored response와 혼합해 점수를 주장하지
않는다.

1. `configs/dev_fast_panel_v1.json`
2. `configs/dev_prompt_holdout_v1.json`
3. dev200

각 단계에서 config, rendered messages, metrics, per-item TP/FP/FN, parse/evidence validity, call count,
runtime을 isolated output에 저장한다. 다른 정책 변경을 섞지 않는다.

dev200 승격 기준:

- 모든 24개 active, 200 rows x 49 columns
- malformed/final missing 0
- evidence validity 100%
- Macro는 C005D `0.8151465658`과 비교
- 목표: `>= 0.805`를 독립 기준선 허용 하한, `>= 0.8151465658`을 완전 대체 목표로 둔다.

허용 하한 `0.805`는 C005D 대비 절대 `-0.010147`이다. 이는 표절 회피를 위한 임의 문구 변경의
허용 오차가 아니라, 독립 prompt 재표본화 비용을 감수하면서도 품질이 유의하게 붕괴하지 않았는지
판단하는 **진단 기준**이다. `0.805` 이상이지만 C005D 미만이면 손실 항목과 runtime을 검토할
수는 있으나 새 최고 성능 기준선으로 고정하지 않는다. 하한 미달이면 제출 ZIP을 만들지 않고
per-item 손실부터 고친다. C005D 이상을 재현하거나, 독립 구조의 명확한 runtime 이득을 포함한
별도 승격 근거가 있어야 최종 제출 후보로 검토한다.

### N5. Submission adapter and exact staged mock

추적 파일:

```text
submission/script.py
submission/runtime_config.json
submission/requirements.txt
scripts/package_clean_submission.py
tests/test_submission_*.py
```

패키지는 `script.py`, active native code, runtime config, 허용 static assets만 포함한다. staged ZIP을
별도 임시 디렉터리에 풀어 10건 mock을 실행하고 49열/ID/evidence/NFC/환경변수 경로를 검사한다.
그 뒤에만 `dist/pps_YYYYMMDD_HHMMSS.zip`을 생성한다.

## 4. 중단 조건

- frozen/reference/legacy 없이는 final owner가 하나라도 비는 경우
- exact rendered input에서 item contract 하나라도 누락된 경우
- fast 또는 holdout에서 손실 원인을 설명하지 못한 채 dev200을 강행하려는 경우
- runtime 계산이 2시간 한계를 넘을 가능성이 높은 경우
- staged ZIP과 로컬 surrogate의 실행 코드가 다른 경우

이 중 하나라도 해당하면 당일 ZIP이라는 일정 때문에 불완전 후보를 제출하지 않는다.
