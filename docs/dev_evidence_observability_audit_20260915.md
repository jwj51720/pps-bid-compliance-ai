# dev gold 근거의 원문 관측 가능성 감사

작성: 2026-09-15, dev / mac

## 질문과 검사 범위

카드 오류와 입력 누락을 구분하기 위해 주최 측 dev200 양성의 gold evidence를 실제 제공된
각 원문 문서에 대조했다. 서로 다른 문서를 concat한 가짜 substring은 인정하지 않으며,
exact match와 NFC 정규화만으로 가능한 match를 분리한다. 법적 판단이나 라벨 override는 없다.

재현:

```bash
.venv/bin/python scripts/audit_dev_evidence_observability.py --output outputs/dev-evidence-observability-20260915/report.json
.venv/bin/python -m pytest -q tests/test_dev_evidence_observability.py
```

## 결과

dev200의 153개 양성 item-instance 중 다음과 같았다.

- 54개: 비어 있지 않은 gold evidence가 제공 원문의 한 문서에 exact substring으로 존재.
- 68개: non-absence 양성이지만 gold evidence가 비어 있음.
- 31개: evidence를 요구하지 않는 absence 항목(v10/v11/v16/v18/v20).
- 비어 있지 않은 gold evidence의 원문 미일치 및 NFC-only 일치는 모두 0개.

이는 **제공된 gold 근거 문자열을 로컬 로더가 누락한 사례는 이 검사에서 없었다**는 뜻이다.
빈 evidence는 원문에 근거가 없다는 뜻이 아니다. v5처럼 금액·기간 관계를 읽어 판단할 수 있는
경우도 있으므로 이를 gold 오류, 입력 불완전 비율 또는 달성 가능한 recall 상한으로 해석하지 않는다.
외부에 존재하지만 organizer 파일에 공급되지 않은 참조 첨부파일의 완결성도 증명하지 않는다.
final rendered prompt로의 전달은 별도의 tokenizer/source 및 semantic-input contract 감사 대상이다.

## 고정 holdout의 검증 한계

`configs/dev_prompt_holdout_v1.json`에는 다음 9개 item의 양성이 없다.

v6, v8, v11, v13, v14, v16, v19, v21, v24.

이 항목의 holdout은 오탐 억제 검증에는 유효하지만 재현율 개선의 독립 확인에는 사용할 수 없다.
예를 들어 v14 EXP260→261은 holdout TP/FP/FN이 `0/12/0`→`0/0/0`이다.
이는 FP 억제의 근거이지 독립 양성 회복의 근거가 아니다. dev200 `5/4/3`의 개선 자체를
취소하는 결과는 아니며, 두 종류의 증거를 구분해서 보고해야 한다.

고정 fast/holdout을 사후 교체하거나 결과를 보고 유리한 cohort를 고르지 않는다.
새 recall 후보는 유료 실행 전에 별도 독립 양성 검증 설계와 한계를 문서화해야 한다.

## 카드 감사에 반영할 결론

카드 asset 선택/렌더링 PASS, 원본 데이터 무결성 PASS, gold 문자열 관측 가능성 PASS는
카드의 법적 의미 완결성이나 모델 적용 성공을 보장하지 않는다. 전수 감사 문서의
v11/v13/v15/v16/v17/v18 예외·적용범위 누락/모호성은 source-grounded 검토를 계속 필요로 한다.
다만 이를 전 항목 카드 일괄 수정의 근거로 쓰지 않는다.

관련 문서: `docs/decision_card_full_audit_20260915.md`,
`docs/prediction_attrition_audit_20260915.md`, `docs/v24_source_concordance_recheck_20260915.md`.
