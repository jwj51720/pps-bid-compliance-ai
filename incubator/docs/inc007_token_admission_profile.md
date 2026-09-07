# INC-007: Exact Token-Admission Profile

INC-006 established that the 4,000-character prefix hides too much source
text; it did not establish 12,000 characters as a policy. This no-API study
uses the Gemma chat-template tokenizer, the 32,768-token model limit, and the
2,500-token output reserve to profile the dev-200 notice shape.

It profiles a general policy: send all documents in one pass when admitted;
otherwise pack complete source documents in organizer order, using the bounded
announcement anchor for a non-announcement pack and splitting only a document
that itself cannot fit. The output is a pass-count and token-cost envelope, not
a label result.

The next paid comparison is permitted only if the p95 pack count projects
within the two-hour test constraint. It will compare this adaptive policy with
the 12,000-character diagnostic policy on the already frozen 24-notice cohort,
without adding facts, rules, retrieval, or changing the output contract.

## Result

Using `GemmaTokenizer.apply_chat_template`, all 200 dev notices fit in the
30,268-token prompt budget: median full-notice prompt size was 9,553 tokens,
p95 was 27,582, and the maximum was 29,829. Thus this dev shape needs no
multi-pass inference at all. The complete-document overflow implementation
remains a safety policy for future/test notices: only eight dev notices would
need two packs if the full one-pass condition were not used.

The dev-shape projection is 1.04 calls per notice (about 1,927 calls for
1,853 notices, using the dev mean; p95 projects one call per notice). This is
within the intended batching regime but must be timed on local vLLM before any
submission claim. The next paid pilot compares the diagnostic 12,000-character
prefix with the exact-token-admitted full notice; 12,000 is no longer a final
policy candidate.
