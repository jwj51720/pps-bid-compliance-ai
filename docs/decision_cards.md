# 항목별 Decision Card 파생 데이터

`data/derived/decision_cards_v*.json`은 `data/항목표.json`의 v1~v24 키에 정확히
연결되는 판정정책 파생 데이터다. 생성 명령은 다음과 같다.

```bash
.venv/bin/python scripts/build_decision_cards.py --version v1
```

각 card는 다음을 포함한다.

- `item_name`: 항목표와 동일해야 하는 항목명
- `absence_detection`: 항목표의 부재탐지 여부
- `official_references`: 국가·지방 참조와 비고의 보존본
- `prompt_text`: 적용 확인, 1 필수조건, 명시적 0 조건, evidence/부재 결합 지시

이는 법령 RAG가 아니다. card는 Gemma가 “문구가 있다”를 곧바로 “위반”으로
단정하지 않도록 판정 절차를 고정한다. 정확한 고시금액, 제품 지정, 금액 구간,
예외처럼 공고별로 달라지는 사실은 사람이 읽을 수 있는 metadata/organizer CSV fact로
제공한다. 법령 원문·조문 bundle을 런타임에 넣지 않는다. 법령은 오프라인에서 검토해
card의 적용 전제·필수 조건·예외 경계로 압축하며, 근거와 변경 이유는 별도 문서에 남긴다.

## 사용

실험 config의 `prompt.decision_cards_path`에 파생 파일을 지정하면 shared pipeline이
24개 card를 system prompt에 넣는다. EXP-009가 이 최초 ablation이다. 실행 전후
config·파생 파일 SHA-256·입력 chat은 output에 저장한다.

제출에서 채택할 때는 canonical `config.yaml`의 `decision_cards_path`와
`submission/runtime_config.json`의 `decision_cards_file`을 함께 지정한다.
`scripts/make_submission.py`는 두 값의 유무와 파일명을 검증하고, 해당 derived JSON을
제출 zip 최상위에 포함한다. 따라서 실험과 제출이 동일한 카드를 읽는다.

## 관리 원칙

카드는 모든 v를 한 파일에 둬 항목표와 일대일 검증한다. 항목별 수정은 생성 script의
versioned card text에서 하고 새 버전 파일로 생성한다. v1은 EXP-009 재현을 위해 보존하며,
v2는 경쟁제품/일반제품 적용성 원칙을 제품분류 관련 항목 카드에 추가한다. 실제 `data/derived/`는 Git ignore 대상이므로,
다른 환경 공유에는 `scripts/export_artifacts.py`가 포함하는 derived artifact archive를
사용한다. 카드에 새 법적 숫자나 예외를 추가할 때는 대회 제공 법령/고시 원문 출처와
추출 근거를 함께 기록한다. 현재 `v6`가 이 원칙을 적용한 카드이며,
`docs/decision_card_v6.md`가 항목별 근거와 변경 범위를 기록한다.

`legal_micro_v1`은 과거 raw-law-RAG 대조에서 만든 보조 artifact이며, 현재 후보가 아니다.
법령 원문·별도 요약 bundle을 런타임에 넣지 않는 정책으로 전환했으므로, 이후의 법령
해석 변경은 `v6`처럼 출처가 남은 정식 card 버전으로만 관리한다.
