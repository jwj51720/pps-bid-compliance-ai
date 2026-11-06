# S019 — Python 판정 경로의 모집단 과적합 감사 계획

상태: 무호출 진단. 기준은 제출 S001 (`clean_exp_s001_integrated_v3_v19_v1.json`)이며
`allowed_policy_changes=[]`이다. 라벨·제출 정책은 바꾸지 않는다.

## 질문과 식별 한계

dev200 Macro F1 0.815147과 public 0.605353의 차이는 0.209794다. 이는 일반화 실패의
증거지만 Python 규칙만의 인과효과는 아니다. 비라벨 20,000건으로는 `P(Y=1|rule fires)`를
식별할 수 없다. 이 감사는 Python owner의 입력 노출, 발화 조건, source-role 오류 가능성을
측정하고, dev200에서 제거했을 때의 반사실 손익을 별도로 계산한다.

## 전수 범위

1. frozen L41 최종 Python override의 v1/v2/v5/v6/v7/v8을 동일 코드로 dev200과
   organizer 비라벨 20,000건에 실행한다. v5 금액 판단은 제출 당시 frozen selector를 그대로
   측정한다. 공고문/첨부를 모두 포함한 원본 record를 사용한다.
2. 기존 S007의 v10/v11/v12/v13/v14/v16/v17/v18, S010의 v3, S012의 v19,
   S013의 v24 모집단 통계와 S011/S014의 dev 반사실을 통합한다.
3. v4/v9/v15/v20/v21/v22/v23은 frozen base reducer 의존성이 크거나 비라벨에서
   final label을 재현할 수 없다. Python arithmetic/lexical 부분을 정적 조사하되
   `20k final positive`로 잘못 표시하지 않는다.
4. 각 direct owner에 대해 발화율 차이, dev/pop 비율, Wilson 95% 구간을 계산한다.
   hash 고정 발화 ID를 남겨 source-role 검토가 가능하게 한다. dev F1이 1인 작은 item은
   positive 표본 수와 불확실성을 함께 표시한다.

## 판정 원칙

- 발화율 이동은 과적합 **위험**이지 precision/F1이 아니다. 더 자주/덜 자주 발화한다고
  자동으로 삭제하지 않는다.
- Python을 걷어낼 후보는 (a) organizer truth condition과 어긋나는 실제 원문 관계가
  반복 확인되고, (b) dev200 제거 반사실이 계산되고, (c) 독립 검증이 남아 있음을 명시한
  경우에만 제시한다. one-cell lexical patch는 금지한다.
- 하나의 item이 Macro에 줄 수 있는 최대 변화는 1/24=0.041667이다. public 격차는
  단일 item 미세수정으로 설명할 수 없다. 공통 제품·범위·absence 경로를 우선 본다.
- 정책 변경은 별도 manifest의 one-change ablation이며, 중간 fast와 독립성이 남은
  검증을 거쳐야 한다. 이 감사 자체는 API/GPU 호출 0회다.

## 재현과 산출물

- 기준 manifest: `experiments/manifests/clean_exp_s001_integrated_v3_v19_v1.json`
- 입력: `data/raw/open/dev.jsonl.gz`, `data/raw/open/train_unlabeled.jsonl.gz`
- frozen artifact: `dist/reference/submit.zip`의 manifest-pinned SHA-256
- output: `outputs/clean-exp-s019-python-policy-population-audit-v1/`
- 실행: `.venv/bin/python scripts/audit_python_policy_population.py`
- exact-tokenizer admission/mock/rendered prompt 계약: 새 모델 prompt와 유료 호출이 없으므로
  해당 없음. 원본 source record를 frozen predicate에 그대로 전달한다.
