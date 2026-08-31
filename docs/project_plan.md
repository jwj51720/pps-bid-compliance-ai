맞습니다. 이전 구조는 아직 결정되지 않은 전략까지 폴더로 확정해버린 면이 있었습니다.

이번에는 문서를 전체적으로 다시 정리해서, 초기에 필요한 구조만 남겼습니다. 핵심은 아래처럼 훨씬 단순합니다.

```text
pps-bid-compliance-ai/
│
├── config.yaml
├── configs/              # versioned/historical experiment configs
├── data/
├── src/
├── scripts/
├── submission/
├── outputs/
├── dist/                 # ignored submission zips and shared archives
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

## 문서 입력 전략 옵션

최종 정책은 `config.yaml`의 `prompt.context_strategy`와 제출용
`submission/runtime_config.json`이 함께 정한다. 기본 `single`은 전체 문서가
Gemma의 정확한 tokenizer 예산에 맞으면 한 번에 넣고, 초과할 때에만 순서대로
문서를 묶어 여러 pass로 나눈다. `full_split_merge`는 비교 실험을 위한 별도
옵션으로, 각 실제 source document를 독립 pass로 넣고 결과를 OR-merge한다.
비공고문 pass에는 동일 공고임을 유지하기 위한 짧은 공고문 앵커와 메타데이터가
함께 들어간다. 어느 모드든 한 source document 자체가 예산을 넘을 때에만 해당
문서를 exact tokenizer 기준으로 잘라 연속 pass로 보낸다.

`full_split_merge`의 strict ablation은 `strict_document_evidence: true`를 함께
설정한다. 이때 Gemma에는 대상 문서·공고문 앵커·metadata의 역할과 정부계약
컴플라이언스 판정 절차를 명확히 설명하고, Python은 non-absence positive의 evidence가
대상 문서 조각 안에 없으면 OR 병합 전 0으로 강등한다. 부재탐지 5개 항목은 문서마다
“필요 조건이 없음”을 판단한 뒤 모든 pass가 1일 때만 최종 1이 되는 AND 결합을 쓴다.

이 선택은 실험 전용 로직이 아니다. `src.pipeline.BaselinePipeline`이 두 환경의
공통 구현이며, 패키징은 두 config의 관련 필드가 일치하지 않으면 실패한다.

제가 보기에도 이번 방향이 더 적절합니다.

> **폴더 구조가 전략을 결정하면 안 되고, 실험을 통해 결정된 전략이 폴더 구조를 만들게 해야 합니다.**

그리고 `data/`도 `raw/`와 `derived/`만 둬서, `derived/` 안에는 향후 `law_wiki.md`, chunk, embedding, self-label 결과 등 무엇이든 넣을 수 있게 열어뒀습니다.

가장 중요한 **실험과 제출이 같은 pipeline을 실행한다**는 원칙은 그대로 유지했습니다.

* 처음에는 local gemma는 사용하지 않습니다. openrouter(./memo.md) 접근으로 시도합니다.
