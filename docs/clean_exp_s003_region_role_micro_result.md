# S003 — 지역 문구 역할 micro 결과

실행일: 2026-09-22. 기준 manifest:
`experiments/manifests/clean_exp_s003_region_role_micro_v1.json`.

## 결론

**사전 gate PASS, 8-call 역할 진단 gate FAIL.** 최종 v5/v6 owner나 제출 정책에는
반영하지 않는다. source-only 발췌 1개만 읽힌 의도적 부분 probe이므로
Macro-F1·public 개선이나 전체 공고 판정 성능을 주장할 수 없다.

| 검증 | 사전 기준 | 관측 |
|---|---:|---:|
| 유효한 응답 | 8/8 | 7/8 |
| source review와 역할 일치 | 7/8 이상 | 4/8 |
| 참가자격 5건의 지역단위 일치 | 4/5 이상 | 2/5 |
| logical model calls | 최대 8 | 8 |
| OpenRouter elapsed | 기록 | 27.127초 |
| 사용량 prompt/completion | 기록 | 2,921/940 tokens |
| provider cost | 기록 | $0.00100215 |

`PPS-DEV-061`은 참가자격 역할은 맞췄지만 원문 placeholder에 기초 단위가
있는데 시·도라고 답했다. `PPS-D-002375`도 경상남도만 요구하는 조항을 기초
단위로 답했다. `PPS-D-002806`의 가점 미반영 문구는 참가자격으로,
`PPS-D-011172`의 지역업체참여도 평가 문구는 OTHER로 답했다.
`PPS-D-001559`의 현장·운반거리 설명도 OTHER로 답했다. 반면
`PPS-D-011290`, `PPS-D-020371`의 시·도 참가자격은 두 필드 모두 맞았다.

`PPS-DEV-071`의 JSON은 role=참가자격, unit=기초였으나 quote가 300자를
넘어서 parser가 invalid 처리했다. **프롬프트와 JSON schema에는 300자 상한을
명시하지 않았고 parser에만 있었다.** 이 1건은 모델 품질 실패가 아니라
실험 계약 불일치다. 이후 유료 prompt 실험은 schema·message·parser의
길이 계약을 먼저 동기화해야 한다. 300자 규칙을 사후 완화해 S003을 성공으로
재채점하지 않는다.

또한 `BASIC`/`PROVINCE`의 뜻과 익명 지역 placeholder의 읽는 법이
실제 system/user message에 명시되지 않았다. 이 8건만으로 모델의 일반적
역할 분류 능력을 기각할 수는 없지만, **현재 prompt는 신규 양성 guard로
사용하기에 불충분**하다는 결론은 확실하다. 경계 사례의 source-only 역할과
최종 v truth condition을 혼동하지 않는다.

## 재현·산출물

- manifest preflight undeclared diff 0, exact tokenizer mock 8/8,
  `python -m pytest -q` 194 passed.
- `outputs/clean-exp-s003-region-role-micro-v1/`: manifest snapshot,
  `source_ledger.json`, 8개 rendered task, `mock_report.json`, 각 raw response,
  `checkpoint_05.json`, `checkpoint_08.json`, `report.json`.
- rendered human review는 `docs/clean_exp_s003_region_role_micro_plan.md`의
  short/attachment/overflow 세 경로와 결론을 따른다.

## 다음 결정

1. S003 prompt/schema/parser를 제자리에서 변경해 결과를 덮어쓰지 않는다.
2. 필요하다면 새 S004 manifest에서 `BASIC=시·군·구 등 기초지역`,
   `PROVINCE=시·도`와 원문 placeholder 해석, 역할 정의, quote 상한을
   **한 가지 표현 계약 수정**으로 선언한다. 별도의 신규 source-only panel에서
   micro gate를 먼저 보며, S003 8건은 오류 분석용으로만 남긴다.
3. 신규 양성의 법률 최종 판정은 역할 결과만으로 내리지 않는다. 공식 금액,
   발주기관·용역 유형, 동일 참가자격 조항의 지역범위, 소액수의 예외,
   모든 첨부문서를 갖춘 final-v semantic contract가 필요하다.
4. 대회 시간이 촉박하므로 S004가 즉시 성공하더라도 fixed fast20 →
   independent holdout20을 건너뛰어 dev200/제출로 올리지 않는다.
