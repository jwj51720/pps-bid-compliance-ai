# 경쟁제품 고시 Exact Lookup과 Prompt 표현 계층

대회 제공 경쟁제품 CSV는 품명 유사도 검색용이 아니라, 공고의 세부품명번호와 정확히
대조하는 정형 reference다.

## 계층

```text
공고 meta / 문서의 명시 세부품명번호
  → competition_product_fact()의 감사용 구조화 fact
  → format_competition_product_context()의 Gemma 친화 한국어
  → final user message
```

`data/derived/competition_products_v1.json`은 CSV의 10자리 `세부품명번호` 615개를 보존한
static index다. raw fact에는 코드와 발견 doc ID를 남긴다. 이는 재현·디버깅용이며 LLM에
그대로 넣지 않는다.

모델에는 다음 세 가지의 자연어 의미만 넣는다.

- 경쟁제품으로 확인: 등재된 세부품명을 나열하고 v10/v11/v13의 적용대상 확인에만 쓰도록 지시
- 경쟁제품으로 확인되지 않음: metadata 세부품명이 고시에 정확 일치하지 않는다는 사실만 전달
- 확인 불가: 정확 대조에 필요한 식별정보가 없으므로 경쟁제품이라고 추측하지 말도록 지시

어느 경우에도 조회 사실은 evidence가 아니다. v10/v11/v13 이외 항목에는 적용대상 fact로
쓰지 않으며, v16/v18의 일반제품 전제에는 `경쟁제품으로 확인`된 품목을 사용하지 않는다.

## 검토용 입력 저장

`scripts/run_experiment.py --dump-inputs --dump-inputs-markdown`은 transport용 `inputs.jsonl`과
함께 `input_examples.md`를 저장한다. Markdown 파일은 system/user message의 **실제 전송
텍스트**만 역할별 fenced block으로 보여 준다.

```bash
.venv/bin/python scripts/run_experiment.py \
  --config configs/config.exp011-friendly-competition-context-first20.yaml \
  --limit 2 --mock --dump-inputs --dump-inputs-markdown --fresh
```

`--mock`은 모델 호출만 대체하며, 실험 config의 exact tokenizer admission과 shared prompt
pipeline은 그대로 사용한다. 따라서 내용을 검토하는 용도에는 API 비용이 들지 않는다.
