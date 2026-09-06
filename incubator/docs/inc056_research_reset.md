# INC-056: Research Reset After Independent-Branch Rejections

## Current evidence

The highest reproducible composition is INC-041 at dev-200 Macro F1 0.26750,
made of the global joint baseline plus three source/law-linked deterministic
components: v2, v3, and v21.  Reaching 0.50 requires +0.23250 Macro F1, far
more than a small prompt or one-label correction can plausibly deliver.

The following independent branches are now closed:

| Branch | Evidence | Reusable result | Closed conclusion |
|---|---|---|---|
| Fixed/adaptive input amount | INC-006/008/018 | complete ordered notice context | fixed character budgets are not generalizable |
| Output family / document splitting | INC-018/024 | none | splitting raises speculative errors |
| Global fact extraction then judgment | INC-027 | source-valid fact ledger possible | loses recall and does not improve decisions |
| Law RAG / simple verifier merge | INC-021 and offline AND/OR | high-precision legal signal | too insensitive as a global detector/verifier |
| Source BGE retrieval | INC-049 | intact source line unit | 40.7% Recall@20 cannot gate decisions |
| Product fact sheet | INC-053 | product facts remain audit-only | repeatably loses v13 positives |
| Label-only output | INC-054 | flat transport | removing evidence task loses decision signal |
| Generic dev/unlabeled cases | INC-025/055 | none | no exact templates; line overlap is boilerplate |

## Feasibility classes

This classification is based on source/law audits and repeated experimental
behavior, not a dev-derived decision threshold.

1. **Formal predicate candidates:** a necessary legal condition can be read
   from official organizer sources and a corresponding source fact has complete
   dev-positive coverage with low negative activation.  Only v2, v3, v21 have
   cleared this gate so far.  Future work may add an item only by the same
   independent evidence standard; it may not tune wording around residual
   errors.
2. **Semantic legal decisions:** evidence exists but needs legal role,
   exception, temporal relation, or cross-document interpretation.  Current
   examples include regional/qualification restrictions, products, v19, v23,
   and metadata reconciliation.  A source cue alone is inadequate.  A new
   architecture here must preserve full notice context and establish a
   repeat-safe improvement before dev-200 confirmation.
3. **Insufficiently observable under current facts:** source candidate coverage
   or meta mapping fails.  These are not candidates for automatic correction,
   self-label transfer, or retrieved-candidate gating until organizer-source
   observability changes.

## Next admissible direction

The only high-value path remaining is a **systematic official-law predicate
discovery audit across the semantic classes**, conducted offline first.  It must
map each item to: complete organizer-law unit, required notice facts, possible
exceptions, fact provenance, and whether every fact is extractable without a
learned model.  It must then gate candidate predicates on all dev positives and
hard negatives before any LLM call.  This is not a request to hand-tune each
label: it is one common legal-program representation evaluated uniformly.

No new generic prompt, RAG ranker, product card, output schema, or case-RAG
experiment is admissible until this mapping identifies a predicate class that
passes source observability.  A target is promoted only if its legal basis is
organizer-provided, its extraction rule has no score-selected numeric or text
cutoff, and its change can be composed immutably into INC-041.
