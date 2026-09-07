# E0 결과 — 원문 증거 관측성 audit

실행일: 2026-09-07

계획: [evidence_first_research_plan.md](evidence_first_research_plan.md)

## 실행 범위

`scripts/audit_evidence_first.py`를 dev200 전체에 실행했다. 이 작업은 API/모델
호출이 없으며, gold label과 evidence는 context 생성·query 생성에 사용하지 않고
관측 지표 계산에만 사용했다. 상세 machine-readable 결과는 ignored
`outputs/evidence-first-e0/report.json` 및 `report.md`에 있다.

## 결과

| 지표 | 값 |
|---|---:|
| gold positive cells | 153 |
| nonempty gold evidence | 54 |
| blank gold evidence | 99 |
| source-unresolved nonempty evidence | 0 |
| EXP120 4,000자 context 내 nonempty evidence | 47 / 54 (87.04%) |
| paragraph 단위 원문 도달 가능 | 54 / 54 (100%) |
| oracle paragraph pack chars (44 relevant notices) median / p90 / max | 123 / 6,742 / 12,101 |

4,000자 context 밖의 nonempty evidence는 일곱 개뿐이었다.

- v9: `PPS-DEV-09`, `PPS-DEV-12`, `PPS-DEV-23`의 규격서
- v2/v3: `PPS-DEV-042`의 공고문 뒷부분
- v22: `PPS-DEV-135`의 제안요청서
- v23: `PPS-DEV-139`의 공고문 뒷부분

## 해석

E0는 source canonicalization과 paragraph-preserving context가 기술적으로
가능함을 보였다. 그러나 전체 nonempty evidence의 87%가 이미 4,000자 control에
들어간다. 더구나 positive 153개 중 99개는 gold evidence가 비어 있어, nonempty
evidence retrieval의 oracle 개선 범위에도 직접 포함되지 않는다.

따라서 **global evidence-first retrieval을 E1/Gemma pilot로 승격하지 않는다.**
완벽한 retrieval이라도 관측된 누락 근거 일곱 건만 직접 복구할 수 있으므로, 0.7대를
목표로 하는 대형 아키텍처 가설이 될 수 없다. v9 규격서처럼 provenance가 완전한
특정 항목의 source attention은 장래의 좁은 진단으로 남길 수 있지만, global selector나
full split/OR merge의 근거는 아니다.

## 함께 닫는 재시도

WSL incubator의 독립 결과도 함께 반영했다.

- generic unlabeled casebook RAG는 작은 pilot 신호가 fresh holdout에서 0으로
  사라졌다. [INC-112](../incubator/docs/inc112_gemma_case_rag_confirmation16_result.md)
- source-grounded Gemma second audit은 positive recovery 없이 false positive 하나만
  추가했다. [INC-129](../incubator/docs/inc129_gemma_source_grounded_self_audit_result.md)
- full-document split/OR merge와 법령 원문·요약 주입도 기존 dev200 실험에서 이미
  성능·runtime을 악화시켰다.

다음 대형 가설은 “누락된 원문을 더 넣기”가 아니라, 이 대회에서 24개 label이 실제로
어떤 **관측 가능한 문서·metadata 사실의 조합**으로 만들어졌는지와, 그 사실을 Gemma가
손실 없이 읽을 수 있는 표현이 무엇인지에 초점을 맞춘다. 이는 별도 계획을 작성하고
offline observability audit를 통과한 뒤에만 유료 호출로 진행한다.
