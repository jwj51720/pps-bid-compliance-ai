# S025 — 철회: 전날 제출물과 동일한 재포장

**제출 금지.** 이 ZIP은 이미 제출한 S001과 내부 14개 파일이 모두 동일하다.
새 정책이나 성능 개선이 없는데 새 제출 후보로 제시한 판단은 잘못이었다.
아래 기록은 재현성 확인용으로만 보존하며, 오늘의 제출 후보로 사용하지 않는다.

2026-09-23. 철회한 ZIP:

`dist/pps_20260923_155819.zip`

SHA-256: `8a4601ff39c1a1cdbc20f48122a4f6e7163ce3885f315e811be948e47e68c072`

## 정책 선택

현재 public에서 성공적으로 완주하고 실제 점수가 확인된 최선 정책은 S001
`integrated-v3-v19-retry2-v1`이다. 지난 제출
`dist/pps_20260922_153225.zip`의 public Macro positive-F1은
`0.6053527995`, evaluator 실행시간은 95분 27초였다. S002~S024의 진단은
일반화 위험과 원문 역할 결함을 확인했지만, 이를 수정한 제출 정책은 아직
독립 성능·runtime을 통과하지 않았다. 따라서 오늘 ZIP에는 미승격 지역금액 보정,
v5 역할 gate, 첨부 hit OR, 제품/부재 owner 교체를 넣지 않았다. 이는 보수적
재제출이며 public 성능 향상 실험으로 부르지 않는다.

새 ZIP의 내부 14개 멤버 SHA-256은 전날 실제 제출 ZIP의 같은 14개 멤버와 **모두
일치**했다. ZIP 파일 해시만 달라진 것은 ZIP 컨테이너 metadata/시간 차이다.
내부 정책·프롬프트·코드·batch 128·invalid 2회 재시도·INT8 설정은 같다.
추출 크기 956,961 bytes, 압축 크기 153,080 bytes로 각각 8 GB/2 GB 제한보다 작고,
ZIP 이름 길이는 30자 이하다. 패키지에는 `script.py`, `requirements.txt`, runtime
config 및 필요한 `pps_ai` 코드만 있다. organizer raw data와 비밀키는 없다.

## 오늘 실행한 검증

1. S001/S006 manifest preflight: undeclared differences 0, PASS.
2. 새 ZIP exact staged mock: 10건/49열, 상태 PASS.
3. S006의 **실제 전날 제출 archive**를 dev200 원문·저장된 OpenRouter 응답·저장 BGE
   ranking으로 다시 실행: 200건, base task hash 600/600, v3 61/61,
   v19 165/165 일치, S001 기준 submission과 49열 cell difference 0.
   출력 `outputs/clean-exp-s006-archive-stored-response-parity-v1/`.
   새 ZIP 내부 멤버가 전날 archive와 모두 같으므로 같은 저장 입력·응답에서 새 ZIP의
   실행 결과도 byte-identical한 코드에 의해 동일하다.
4. 재실행 dev200 Macro positive-F1 `0.8151465658238104`.
   fast20 `0.7277777777777777`, dev200 일부인 holdout20
   `0.4305555555555556`. 세 값 모두 adaptive dev 회귀값이지 test 성능 추정치가 아니다.
5. 재실행 CSV 200개 고유·완전 ID, 정확한 49열 순서, 24개 v의 정수형 0/1 출력,
   NFC/500자 근거 조건 확인. 비어 있지 않은 evidence 171개는 모두 해당 공고의
   변경 없는 제공 문서 부분문자열이며, absence 항목의 evidence는 비어 있다.
   non-absence 양성 중 빈 evidence 6개는 기존과 동일하다:
   `PPS-DEV-034/v24`, `036/v15`, `041/v24`, `055/v15`, `094/v24`, `170/v24`.
   근거만 기계적으로 추가하거나 라벨을 바꾸는 사후 수정은 하지 않았다.
6. 전체 `.venv/bin/python -m pytest -q`: 239 passed.

## 실행/일반화 한계

- 오늘 dev200은 **새로운 Gemma 661회 생성이 아닌 저장응답 replay**다. 제출 코드와
  데이터 조립의 결정적 동등성은 검증하지만, 새 OpenRouter 샘플이나 evaluator vLLM
  변동성은 측정하지 않는다. 과거 public 95분 27초가 이 동일 내부 코드의 실제
  evaluator 완주 증거다.
- 이전 public `0.60535`와 local `0.81515`의 괴리는 해결되지 않았다. 오늘 ZIP은
  검증되지 않은 과적합 제거를 마지막 순간에 섞지 않은 안전한 기준 후보이며,
  점수 상승을 기대하는 신규 후보가 아니다.
- organizer의 2026-09-22 지역제한 금액 공지는 이 ZIP의 v5~v7 Python selector에
  반영되지 않았다. S002에서는 dev200 라벨 변화 0, 비라벨 신규 후보 11건의
  역할 검토 실패가 확인되어 threshold-only 보정의 즉시 통합을 보류했다.
- evaluator GPU를 이 환경에서 새로 실행하지 않았고 설치시간도 실제 evaluator에서
  다시 측정하지 않았다. 직전 동일 멤버 ZIP의 완주가 현재 가장 강한 실행시간 근거다.

결론(정정): **오늘의 신규 제출안은 아직 없다.** 동일 정책의 재포장은
제출 가치가 없으며, 일반화 성능 개선 목표도 미완료다. S023/S024에서
확인된 Python source-role 결함의 대체 owner를 별도 실험으로 검증해야 한다.
