# INC-043: Whitespace-Only Evidence Resolution Audit

## Question

INC-042 treated an LLM positive whose quoted string was not an exact source
substring as a hard format failure. Many raw responses visibly reflow source
tables and line breaks. This offline audit tests whether a quote can be
resolved to a **unique unchanged source substring** by normalizing whitespace
only.

## Frozen resolver

For an LLM quote and each full source document, map every maximal whitespace
run to one ASCII space for matching. If the normalized quote occurs exactly
once across all documents, return the corresponding original source slice;
otherwise return no evidence. It does not alter non-whitespace characters,
correct typos, drop tokens, use similarity, choose among multiple matches, or
change a binary judgment.

## Interpretation

This audit cannot retroactively validate INC-042 or produce its score: its
protocol predeclared invalid evidence as a failure. It only determines whether
the resolver is precise enough to be predeclared in a future replicated call.
Any quote whose non-whitespace content differs from source remains unresolved.
