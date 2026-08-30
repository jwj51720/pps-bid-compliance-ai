맞습니다. 이전 구조는 아직 결정되지 않은 전략까지 폴더로 확정해버린 면이 있었습니다.

이번에는 문서를 전체적으로 다시 정리해서, 초기에 필요한 구조만 남겼습니다. 핵심은 아래처럼 훨씬 단순합니다.

```text
pps-bid-compliance-ai/
│
├── config.yaml
├── data/
├── src/
├── scripts/
├── submission/
├── outputs/
└── docs/
```

`src/`도 처음에는 최대한 평평하게 유지합니다.

```text
src/
├── pipeline.py
├── data.py
├── prompt.py
├── submission.py
├── evaluate.py
└── external/
    ├── openrouter.py
    ├── openai.py
    └── local_gemma.py
```

특히 `rag/`, `rules/`, `wiki/`, `retrieval/` 같은 폴더는 **지금 만들지 않는 방향**으로 바꿨습니다. LLM Wiki가 주력이 되면 그때 `knowledge/`를 만들고, embedding retrieval이 주력이 되면 그때 `retrieval/`을 만들고, rule 코드가 커지면 그때 `rules/`를 만들면 됩니다.

제가 보기에도 이번 방향이 더 적절합니다.

> **폴더 구조가 전략을 결정하면 안 되고, 실험을 통해 결정된 전략이 폴더 구조를 만들게 해야 합니다.**

그리고 `data/`도 `raw/`와 `derived/`만 둬서, `derived/` 안에는 향후 `law_wiki.md`, chunk, embedding, self-label 결과 등 무엇이든 넣을 수 있게 열어뒀습니다.

가장 중요한 **실험과 제출이 같은 pipeline을 실행한다**는 원칙은 그대로 유지했습니다.

* 처음에는 local gemma는 사용하지 않습니다. openrouter(./memo.md) 접근으로 시도합니다.