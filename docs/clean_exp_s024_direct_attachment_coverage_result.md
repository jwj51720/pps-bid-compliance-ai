# S024 — direct Python owner의 첨부문서 후보 누락 감사 결과

2026-09-23. 상태: **PASS — 원본 frozen 계수 완전 일치, 첨부-only 후보 240 notice-item pair;
원문 역할 혼합 때문에 일괄 문서범위 확대 기각**. 정책·최종 라벨 변경 없음.

`scripts/audit_direct_attachment_coverage.py`가 hash-pinned L41의 같은 direct-owner
predicate를 원래 record와 첨부 한 건을 진단용 공고문으로 치환한 record에 적용했다.
dev200 200건/374문서, organizer 비라벨 20,000건/38,862문서를 모두 읽었고,
원본 여섯 item의 final 발화 수와 원본 파일 SHA-256이 S019와 정확히 일치했다.
LLM/BGE 호출 0, 약 185.18초. 원본 provenance·고정 hash 표본은
`outputs/clean-exp-s024-direct-attachment-coverage-v1/audit_report.json` 및
`source_samples.json`에 있다. 후자는 ignored raw source라 Git에 넣지 않는다.

| item | 20k 원본 공고문 final 1 | 원본 0인데 첨부 단독 predicate 1 | 주된 첨부 |
|---|---:|---:|---|
| v1 | 118 | 30 | 제안요청서 18, 과업지시서 9 |
| v2 | 255 | 164 | 제안요청서 147 |
| v5 | 42 | 9 | 제안요청서 7 |
| v6 | 197 | 17 | 규격서 8, 과업지시서 5 |
| v7 | 349 | 11 | 규격서/과업지시서/제안요청서 혼합 |
| v8 | 34 | 9 | 제안요청서 8 |

합계 240은 **notice-item pair**다. 한 공고가 여러 item에 등장할 수 있으며
실제 추가 위반 건수가 아니다. v8은 한 문서씩 치환한 하한이므로 서로 다른 문서의
실적·지역 조건 결합을 측정하지 못한다. dev200에서는 v1 한 건
`PPS-DEV-145`만 첨부-only였고 organizer 정답 v1=0이었다. 따라서 dev를 기준으로
첨부 hit를 그대로 OR하는 정책은 적어도 이 한 건에서 FP를 만든다.

hash 고정 비라벨 source 표본을 원래 문서 역할로 검토했다.

- v1 첨부-only 첫 8건의 hit 대부분은 **참가 허용**, 수요자·참관객의 참여,
  평가위원 자격, 과업 수행 인력의 참여를 `특정기관만의 입찰 참가제한`으로 혼동했다.
  한 건은 공식 유통대행사 조건이 포함돼 있으나 소기업 참가범위 확대 예외 문맥도 있어
  이 표본만으로 최종 v1 위반을 단정하지 않는다.
- v2 첫 8건은 제안서의 **수행실적 평가표·제출 서식**이 다수였다. 일부는
  계약상대자의 이행실적 요구이며, 한 건은 입찰자격으로 보이는 실적 문구가 있었다.
  따라서 공고문만 보는 현재 owner는 실제 제한을 놓칠 수 있지만, 전 첨부에 같은
  regex를 OR하면 평가·서식 FP가 대량으로 생길 위험도 있다.
- v5/v6 표본에는 지역기업 **평가 가점**과 납품거리 계산 같은 비참가조건이 있었고,
  별도로 첨부 안의 실제 업체 소재지 참가조건처럼 보이는 사례도 있었다.

이는 S020의 공고문 내 역할 오독과 같은 구조가 **첨부에서도 반복**됨을 보여 준다.
단순 문서범위 확대와 단순 Python 삭제는 서로 반대 방향의 오류를 만든다. 다음
후보의 핵심은 어떤 문서에 있든 `실제 입찰참가 조건/평가/서식/계약이행/예외`의
역할을 원문 문맥으로 분리한 뒤 item별 법적 판단을 하는 것이다. 하나의 공통
schema가 모든 v에 맞는다고 가정하지 않으며, 먼저 v1 또는 v2의 가장 작은
truth condition에서 완전 원문·metadata를 갖춘 대체 관측을 검증한다.

이 결과는 첨부를 제출 판단에서 빼라는 뜻이 아니다. 제공 문서 전체를 판정 범위에
유지하되, source role 없는 hit를 자동 양성으로 승격하지 말라는 뜻이다. 정답 없는
20k와 dev 한 건만으로 public F1 개선을 주장하지 않는다.

재현: `.venv/bin/python scripts/audit_direct_attachment_coverage.py` 실행 후
`audit_report.json`의 `checks` 세 값과 각 cohort의 `attachment_only_notice_pairs`를
확인한다. 단위·전체 검증은 `.venv/bin/python -m pytest -q`에서 239 passed였다.
