# INC-023: Article-Bound Legal Context Protocol

This is a protocol, not a paid model experiment. It replaces all
character-count-selected RAG context policies.

For each item, legal context must be assembled from organizer source text in
this order:

1. Start from the item table's national and local legal citations.
2. Use BGE retrieval only to locate a cited source offset when a citation is
   ambiguous; retrieval rank never decides law applicability.
3. Expand that offset to the complete enclosing `제N조`, enumerated paragraph,
   or named appendix-table boundary. Preserve source file, offsets, and SHA.
4. Keep that complete legal unit as fixed context. Do not truncate it to a
   dev-derived character threshold.
5. Before any Gemma call, admit fixed legal units first and then complete notice
   documents under the submission-defined context/output reserve. If overflow
   remains, use the same complete-document notice-pack policy for every notice;
   do not alter legal-unit length from dev performance or notice length.

The next experiment may proceed only after an offline audit records, for all
24 items, the source citation, extracted unit boundary, unit hash, unit token
count, and whether fixed context alone fits the submission budget. It must use
a predeclared development/confirmation split or a single frozen protocol on
all dev; no iterative metric-driven article selection is allowed.

## Offline audit result (2026-09-05)

`inc023_article_context_audit.py` examined the organizer item table against
the organizer law-text package without a model call. It resolves a citation
only where its named source and full article identifier (including `조의N`)
are unique in the active body of the source; historical supplementary acts
after the first `부칙` are excluded because they are not the current operative
article. The generated, ignored manifest is
`incubator/data/derived/inc023_article_context_audit.json`.

- 76 citation-to-article records are uniquely resolved, with source offsets,
  source/unit SHA-256, and source-unit character counts recorded.
- 14 records require a manual complete-section/table boundary: the cited
  product designation list, administrative guidelines/chapters, a notice
  amount document, or a citation that names a source but no article.
- 3 records are intentionally non-law/unsupported references (v23 national;
  v24 national/local). They must be represented as item-policy exceptions, not
  fabricated legal context.

Exact Gemma token counts remain pending because this workspace cannot access
the gated Gemma tokenizer. They must be produced with the packaged submission
runtime tokenizer; no character count is permitted as a token-admission
substitute. This audit is not a score experiment and authorizes no Gemma API
calls. The immediate next task is a human-readable, reviewed boundary map for
the 14 manual records, followed by a fixed-context admission audit under the
actual submission tokenizer.
