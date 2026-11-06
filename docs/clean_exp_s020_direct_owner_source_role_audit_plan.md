# S020 — direct Python owner 원문 역할 감사 계획

상태: 무호출·무정책변경 진단. S001 frozen 제출 정책을 기준으로 하고
`allowed_policy_changes=[]`이다. 목적은 S019의 발화율 이동이 실제로 어떤 source-role
오독과 연결되는지 owner군 전반에서 확인하는 것이다.

S019의 SHA-256 ID 정렬로 미리 고정된 비라벨 발화 사례를 v1/v2/v5/v6/v7/v8 각각 최대 8건,
v6 소액수의 예외가 raw hit를 제거한 사례 8건 추출한다. 원문 전체에서 frozen predicate가
인용한 span, 문서 유형, 주변 문맥, human-readable 계약 메타를 함께 보존한다. dev 정답이나
S001 FP ID를 보고 사례를 고르지 않는다.

검토 기준은 법적 정답 추측이 아닌 관측 역할이다: 입찰 참가조건, 평가/서식/안내, 적용 예외,
계약 후 의무, 다른 계약/제품/주체, 불명확. 한 사례에 여러 역할이 있으면 동시에 기록한다.
해당 role이 진짜 1/0인지 판단하기에는 공고 전체와 organizer 기준 검토가 추가로 필요하다.

단일 owner의 작은 표본을 전체 모집단 오류율로 외삽하지 않는다. 공통적인 역할 오독이 여러
owner군에 나타나면 shared source-view 변경의 후보가 되지만, item truth condition을 먼저
확인하고 한 item씩 ablation한다. 비라벨 검토만으로 제출 label을 변경하지 않는다.

입력: `data/raw/open/train_unlabeled.jsonl.gz`, S019 `audit_report.json`, hash-pinned
`dist/reference/submit.zip`. 산출물:
`outputs/clean-exp-s020-direct-owner-source-role-audit-v1/source_samples.json`.
LLM/BGE 0회, exact-tokenizer/prompt/mock은 새 모델 호출이 없어 해당 없음.
