# N008D v2 participation-axis dev200 result

실행일: 2026-09-22

상태: **REJECT — native v2 owner로 승격하지 않음**

## 결과

N008의 동일 정책을 fast20, 독립 holdout20에 이어 dev200 전체에 적용했다.
dev200에서는 200개 notice를 각각 한 번 호출했으며 frozen 판정을 읽거나
fallback하지 않았다.

| cohort | TP | FP | FN | F1 | invalid |
| --- | ---: | ---: | ---: | ---: | ---: |
| fast20 | 3 | 0 | 0 | 1.000000 | 0 |
| holdout20 | 1 | 0 | 0 | 1.000000 | 1 |
| dev200 | 7 | 3 | 0 | 0.823529 | 20 |

dev200 precision은 0.7, recall은 1.0이다. 200 logical/new calls에
407.11초, prompt 1,112,527 tokens, completion 150,858 tokens가
사용됐고 response usage의 cost 합은 `$0.14212563`이다. 유효 양성
10건의 evidence는 모두 원문 substring으로 검증됐다.

frozen L41의 v2 dev200은 TP/FP/FN=7/0/0, F1=1.0이다. 따라서 N008은
양성 recall을 보존했지만 FP 3건과 invalid 20건 때문에 더 낮으며
대체 owner가 될 수 없다. fast/holdout 합계 양성 4건의 완전일치는
dev200 일반화를 보장하지 않았다.

## 세 semantic false positives

1. `PPS-DEV-059`: 참가자격에 최근 3년 공공기관 통근버스 운행실적
   2억원 이상이 명시돼 있다. 그러나 metadata상 지방계약·소액수의
   공고이며 organizer v2 기준의 허용 범위다. 모델은 card와 계약방법을
   받았음에도 `explicit_allowance=N`으로 관측했다.
2. `PPS-DEV-127`: `건설폐기물처리용역 적격업체 평가기준` 안의
   이행실적 평가 규모를 참가자격 하한으로 오독했다. 즉 평가 단계와
   참가 단계의 관계 오류다.
3. `PPS-DEV-137`: 제안서 평가 양식의 최근 5년·단일계약·5천만원
   수행실적 주석을 참가자격으로 오독했다. 참가자격 본문에는 해당
   실적 하한이 없다.

첫 오류는 허용조건 적용 실패, 뒤의 두 오류는 문서 내 절차 역할
분류 실패다. Python threshold projection이나 source coverage 누락의
오류는 아니다. 세 근거문 모두 bounded all-document view에 존재했다.

## invalid 20건의 분해

- 17건: `finish_reason=length`. 응답은 필요한 네 축을 거의 완성한 뒤
  JSON을 닫지 않고 공백을 반복했다. 각 usage는 정확히 8,192 completion
  tokens였으며 manifest 설정 1,024와 불일치한다.
- 3건: `finish_reason=stop`이지만 quote가 원문 substring이 아니어서
  `quote_not_in_source`로 안전하게 0 처리됐다
  (`PPS-DEV-145`, `PPS-DEV-169`, `PPS-DEV-178`).
- invalid 20건은 모두 gold=0이어서 이번 F1의 세 FP에는 포함되지
  않았다. 그렇더라도 10% structured-output 실패율은 제출 가능한
  runtime 계약이 아니다.

Active transport는 이미 `max_completion_tokens`를 사용한다. C001B에서는
동일 필드가 1,536 한도를 실제 강제했지만 N008H/N008D 일부 응답은
각각 설정 1,024를 무시하고 8,192까지 생성됐다. 그러므로 현재 증거만으로
deprecated field 재발이라고 결론내릴 수 없다. provider route별 parameter
준수 또는 structured-output 구현 차이를 별도 transport 실험으로 격리해야
한다. 의미 prompt·schema 변경과 섞지 않는다.

## 결정과 다음 gate

- N008 v2는 rejected diagnostic으로 보존하고 frozen v2를 교체하지 않는다.
- 다음 v2 semantic 후보가 있다면 먼저 고정 fast20에서 점수를 기록하고,
  통과할 때만 독립 holdout20, 이후 dev200으로 확장한다.
- 다만 현재 fast20에는 이번 dev200 FP 세 유형이 충분히 포함되지 않았다.
  fast score는 저비용 탈락 기준이지 승격 근거가 아니다.
- 8,192-token runaway는 별도 transport/serialization 계획에서 재현성과
  provider route를 먼저 확인한다. 기존 정상 응답이나 v2 의미정책을
  동시에 바꾸지 않는다.

산출물:

- `outputs/clean-exp-n008d-v2-participation-dev200-v1/dev200/run_report.json`
- `outputs/clean-exp-n008d-v2-participation-dev200-v1/dev200/responses/`
- `outputs/clean-native-v2-performance-task-v2/dev200-fp-review/`

