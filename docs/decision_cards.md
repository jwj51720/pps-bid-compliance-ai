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
예외처럼 card 안에서 추정하면 안 되는 사실은 이후 official-law RAG 또는 결정적
metadata lookup이 제공해야 한다.

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
추출 근거를 함께 기록한다.

`legal_micro_v1`은 raw-law RAG의 대조 실험용 카드다. `v2`의 제품 적용성 원칙을
유지하되, `docs/legal_reference_mapping.md`에 검증된 organizer 법령 조문의
**판정 순서만** 짧게 재서술한다. 법령 원문·새 금액 임계값·새 품목 사실은 넣지 않는다.
따라서 이 카드는 “법령 원문을 더 넣으면 좋아지는가”가 아니라 “짧은 법령상 적용
조건을 카드로 명시하면 Gemma가 더 일관되게 적용하는가”를 검증한다. EXP030은
EXP027과 같은 12-group/full-split 조건에서 이 카드 파일만 바꾼 비교다.
