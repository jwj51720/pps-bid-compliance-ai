# 명령
1. 커밋하라: 커밋을 할 때는 현재 변경사항을 확인하고 책임 분리에 맞게 순차적으로 나눠서 커밋한다.
* 이때 memo.md가 업데이트 되었거나 docs 내부의 어떤 것이 업데이트 되었다면, 우리가 합의한 내용 혹은 합의할 내용이 신규되었거나 변경된 것일 수 있으므로 그 변경사항에 맞게 AGENTS.md에도 반영할 내용은 반영한다.
2. 실험하라: 내가 지시한 내용대로 or 어떤 문서 경로를 주고 그 문서에 적힌대로 실험하라고 지시하면 그 내용을 온전히 이해하고, 최대한 가능성을 열어둔 채 실험한다. 결과 역시 어떤 실험의 결과인지 잘 알 수 있도록 분리하여 저장하고, 평가를 해야한다면 그 평가 결과도 문서로 제대로 남겨둔다.
방법론과 trial 간의 정량 비교를 위함이다. 재현성은 아주 중요하므로 재현 방식도 적자.
3. 제출 파일을 만들어라: dacon에 바로 제출할 수 있도록 규정에 맞게 제출할 수 있는 파일을 만든다. 필수요소가 빠지면 절대 안되며,
대회의 룰을 위반하지 않도록, 대회의 규정과 가이드를 준수할 수 있도록 만들어야 한다.
가령, llm의 호출이나 환경변수를 쓰는 것, RAG 파일을 런타임으로 만들지, 미리 만든 걸 들고 들어갈지도 세밀하게 관리해야 한다.
4. 데이터 export: data/는 ignore지만, 다른 환경에서 바로 이어갈 수 있도록 export에는 `data/raw/`와 `data/derived/`, outputs, submission 및 `dist/`의 제출 zip을 포함한다. `.env`, Git metadata, 가상환경·캐시·기기 메타데이터와 `dist/archives/`의 기존 archive는 제외한다. export 압축을 다운로드해 다른 환경에 직접 공유한다.
5. 핸드오프 남기기: 명시적으로 요청되면 `docs/handoff/YYYYMMDD_HHMMSS_<mac-or-linux>_HANDOFF.md`를 작성한다. 이 환경의 당일 변경·커밋·실험/결과·사고 흐름·실패/주의사항·다음 단계와 관련 산출물 링크를 기록한다. 다른 환경이 같은 실수를 반복하지 않고 이어갈 수 있을 정도로 작성하되, API 키·raw 데이터는 넣지 않는다.

# 설계 절제 원칙
- 관찰값·후처리·추가 호출은 실제 항목의 진리조건이 기존 pipeline으로 표현되지 않는 것이 확인된 경우에만 추가한다. 판정이 어렵거나 dev에서 오류가 보인다는 이유만으로 여러 항목의 출력 schema·merge를 한꺼번에 바꾸지 않는다.
- 기본값은 non-absence OR, 부재탐지 5개 AND다. 문서 간 결합이 필요한 것으로 확인된 v8만 별도 상태를 추가하며, 나머지는 명시적 반례와 재현 가능한 실험 전까지 기본 결합을 유지한다.
- 새 구조는 먼저 최소 출력·최소 호출로 구현하고 mock과 작은 dev 평가로 효과·형식오류·runtime을 확인한다. 성능 또는 안정성 이득이 확인되기 전에는 canonical 제출 정책을 바꾸지 않는다.
- 실험을 실행하기 전에는 실험 가설의 필수 구성요소가 모두 코드와 configuration에 구현되었는지, 입력 artifact의 coverage와 provenance가 완결됐는지, tokenizer admission·mock·평가 산출물 경로가 준비됐는지를 점검한다. 일부만 구현된 probe는 명확히 별도 진단으로 이름 붙이며, 완결 전략의 성과로 보고하지 않는다.
- 파일 순서 first-20은 fast gate로 사용하지 않는다. 기본 fast 평가에는 `configs/dev_fast_panel_v1.json`을 사용하며, 이 패널은 고정·버전관리한다. 패널 점수는 dev-200 확인을 대체하거나 canonical 정책 변경의 근거가 될 수 없다.
- **변경 통제:** 기존 세팅의 일부만 바꾸는 실험은 `experiment.base_config`와 `allowed_policy_changes`를 config에 기록하고 `scripts/preflight_experiment.py`로 effective prompt·LLM·group execution policy의 차이를 확인한다. 선언하지 않은 차이가 있으면 유료 실행하지 않는다. prompt, output schema, merge, RAG, card를 한 실험에서 함께 바꾸지 않는다.
- **재실행 안전성:** 실행 구조(v grouping, reference mode/navigation)는 runner CLI 관례가 아니라 `grouped_run` 등 versioned config에 기록한다. 결함이 확인된 실험은 `lifecycle: invalidated`로 보존하되 loader가 재실행을 거부하게 하고, 결과를 후보 비교·제출 근거로 쓰지 않는다.
- **프롬프트 사전 검토:** 유료 prompt 실험 전에는 exact rendered system/user message를 Markdown으로 내보내고 직접 읽는다. 최소한 짧은 완전 공고·절단/overflow 공고·첨부 포함 공고를 확인하고, 검토 파일 경로와 결론을 실험 계획에 남긴다. config 값이나 prompt source만으로 input 검토를 대체하지 않는다.
- **의미 완결성 gate:** 형식·토큰 검토와 별개로, 활성 v마다 적용 전제·1 조건·중요 0 조건/예외·필요 문서 유형·필요 metadata/CSV 사실을 organizer source와 연결한 `semantic input contract`를 먼저 만든다. 유료 실행 전 그 각각이 exact rendered input의 어느 문장에 들어가는지 대조한다. 항목명·비고만 있거나 출처 없는 추상 조건이면 실행하지 않는다.

# 현재 법령·판단카드 정책

- 모델 prompt에 법령 원문, 조문 발췌, 법령 요약 reference bundle을 별도 문서로 주입하지 않는다. 원문 RAG와 reference-only probe는 audit/과거 실험으로 보존하되 canonical 후보로 승격하지 않는다.
- 대회 제공 법령·고시·예외는 사람이 source provenance와 함께 검토한 뒤, 각 v의 `decision_cards_v*.json`에 **압축적인 판단 기준**으로만 반영한다. 카드는 적용 전제, 1 조건, 0 조건, 주요 예외·수치·기간을 사람이 읽기 쉬운 문장으로 제공하되 notice-specific 사실이나 dev label을 넣지 않는다.
- 모델은 법령 전문가로서 카드·공고 자료 원문·나라장터 metadata를 함께 읽고 자율적으로 판단한다. 카드가 제공하는 기준을 정확히 적용하지 않으면 정부계약 컴플라이언스 리스크와 피해가 생길 수 있음을 prompt에서 명확히 알린다. 다만 이 문구는 불확실한 사실을 자동으로 1로 단정하게 해서는 안 된다.
- 제품의 경쟁제품 여부처럼 organizer CSV의 정확 코드 사실이 필요한 경우에는 versioned friendly product context만 사용한다. 조건-aware 후보는 매칭 행의 `특이사항`과 코드가 확인된 human-readable 출처를 함께 전달하고, 실제 구매대상·금액·규격과의 적용 관계는 Gemma가 판단한다. Python이 조건을 계산해 제품 상태나 라벨을 확정하지 않는다. 역사적 `names_only_v1` renderer는 과거 실험 재현용으로 유지한다. 법령 reference text로 대체하거나 제품 상태를 추정하지 않는다.

## Canonical 모델 입력 형태

card를 사용하는 후보 prompt는 아래 순서를 기본 형태로 쓴다. 이는 RAG가 아니다. 법령·고시·예외의 offline 검토 결과를 card에 압축해 둔 **카드 중심 판정 작업지시**다. 현재 제출 후보는 EXP171 source-first/full-final로 card v6·친화적 metadata/경쟁제품 사실·원문을 final Gemma에 함께 제공한다. `config.yaml`과 `submission/runtime_config.json`은 이 정책과 같은 staged mode를 함께 정한다. organizer-format single-call baseline과 EXP135 2-way partition은 historical control로 보존한다.

```text
1. 기본 역할·판정 원칙
2. 출력 계약: v만 출력할지, v와 e를 함께 출력할지에 따른 정확한 형식·근거 규칙
3. 이번 호출에서 판정할 v의 항목별 판단 카드
4. 그 v 판단에 필요한 나라장터 metadata와 organizer CSV의 친화적 사실
5. 이번 공고의 실제 문서 원문
```

- **기본 역할·판정 원칙:** 모델은 공공계약 법령 전문가다. 카드 기준을 공고 원문과 metadata에 정확히 적용하지 않으면 컴플라이언스 리스크와 피해가 생길 수 있음을 알리되, 불확실한 사실을 자동 1로 처리하라고 지시하지 않는다.
- **출력 계약:** v-only는 0/1만, v+e는 1인 non-absence 항목에 공고 자료 원문의 변경 없는 evidence substring을 요구한다. evidence 규칙은 label 판단 기준을 바꾸지 않는다.
- **판단 카드:** 각 v의 적용 전제, 1 조건, 0 조건, 주요 예외·수치·기간을 압축해 제공한다. 법령 원문과 별도 요약 reference는 넣지 않는다.
- **판정 필요 metadata:** 전체 raw JSON을 기계적으로 던지지 않는다. 적용계약법, 업무구분, 계약·낙찰방법, 예산·추정가격, 지역·업종·공동계약, 날짜, 세부품명처럼 해당 v의 진리조건에 필요한 사실만 사람 친화적 문장 또는 소형 표로 제공한다. 코드·내부 status·구현 변수명은 prompt에 넣지 않는다.
- **공고 원문:** 공고문과 첨부문서는 실제 제한·요구·불일치 및 evidence를 찾는 유일한 원문 근거다. 문서 순서·token admission·overflow 처리 정책은 shared pipeline이 관리한다.

20,000건 비라벨 공고나 법령 RAG는 이 canonical prompt의 구성요소가 아니다. 이들은 향후 offline 사례 검토·card 작성 품질 점검 용도로만 검토할 수 있으며, 모델 context에 그대로 주입하지 않는다.

# openrouter에서 사용할 모델
openrouter gemma4 model (free)
https://openrouter.ai/google/gemma-4-26b-a4b-it:free
openrouter gemma4 model
https://openrouter.ai/google/gemma-4-26b-a4b-it

# 의존성 이슈
하나의 파이썬 가상환경을 만들어서 진행할 것. requirements.txt는 필수

# 커밋과 ignore에 대해
data/ 안의 실제 데이터는 ignore하도록 한다. 대신, 구조는 지켜지도록 할 것이다.

# 데이터 가공에 대한 아이디어 메모
- 한 문제의 5개 docs가 모두 안 들어갈 수도 있음
1. 공고문 → 규격서 → 과업지시서 → 제안요청서 → 예외공표서 순서로 넣는데, 만약 다 안들어간다면 들어가는 것까지만 넣는다.
2. 예를 들어, 제안요청서와 예외공표서가 못 들어갔다면 첫 시행에서는 공고문/규격서/과업지시서가 들어갔을테니, 두 번째 시행에서는 공고문(이것은 항상 포함)/제안요청서/예외공표서를 넣는다.
3. 첫 번째 시행에서는 위반 사항 없음이 나올 수도 있다. 하지만 두 번째에서는 위반사항 있음이 나올 수 있다. 그렇다면 두 번째 넣은 공고문(이것은 항상 포함)/제안요청서/예외공표서가 위반 단서일테다.
4. 즉, token 수를 미리 재서 들어가는 것까지만 온전히 넣고, 안 들어가면 두 번 이상 시행하는 것이다.
5. 결과를 종합한다. 첫 번째 시행에서 v24, e24가 나올 거고, 두 번째 시행에서도 v24, e24가 나올 거다.
6. 만약 1 1이면 공고문에서 위반되었을 가능성이 높아 그냥 첫 번째 시행의 v와 e를 따른다. 1 0이거나 0 1이라면 위반된 것의 결과를 따른다. 둘 다 위반이 아니라고 나올 때만 최종 위반 아님 판단이다.
