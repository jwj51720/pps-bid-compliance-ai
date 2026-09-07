# Bounded multi-call verifier strategy v1

## Why this is now admissible to investigate

The observed organizer-format submission took about 34 minutes. The measured
EXP139 two-call token ratio was 1.76×, so two and potentially three complete
notice-level calls can be investigated within the two-hour envelope. This does
not re-open full-document split × grouping: that multiplicative design already
timed out.

This document is a design/audit plan only. No prompt, merge policy, or paid
experiment is authorized by it until every active item's semantic-input
contract is rendered and reviewed.

## Error-shape evidence

EXP109 exact organizer baseline on dev-200 had `TP=49`, `FP=232`, `FN=104`.

- Large false-positive items: `v13=73`, `v17=52`, `v24=36`, `v21=22`,
  `v19=12`, `v5=11`.
- Large false-negative items: `v14=8`, `v10=7`, `v18=7`, `v6=6`, `v7=6`,
  `v11=6`, `v16=6`, `v2=5`, `v8=5`, `v9=5`, `v12=6`, `v20=5`.

A loop that only asks a second model call to reject first-pass positives can
reduce some FP, but it cannot recover these first-pass FN. It is therefore a
precision-only ablation, not the primary quality hypothesis.

## Rejected draft: one base call plus two specialists

All calls receive the same tokenizer-admitted 4,000-character notice context
and actual organizer metadata. There is no document split, no raw-law/RAG
context, and no hidden Python label rule.

| Call | Active output items | Role | Why its input differs |
| --- | --- | --- | --- |
| A | v1–v24 | organizer-format broad first reading | Maintains the simple whole-notice context that has produced the best public baseline signal. |
| B | v1–v9, v19, v21–v24 | qualification/document/procedure verifier | Renders only the profile-specific conditions, metadata facts, and source-document scopes required by the semantic contract for these items. |
| C | v10–v18, v20 | product/absence verifier | Renders exact friendly organizer-CSV applicability, price band, absence scope, and the required product/SW conditions. |

The final policy would use B for its declared keys and C for its declared keys;
A supplies no overlapping final key. This makes the draft invalid as a final
policy: the entire A call is discarded, so it is neither a verifier nor a
source of a final value. It may be retained only as a separately evaluated
control, never bundled into a submission candidate merely for reassurance.

The correct question is therefore whether B+C alone form a valid two-call
policy. The input audit below answers **no** for the current 4,000-character
context: B contains `v9`, whose required evidence scope is attachments, and C
contains the five absence items, whose truth condition is absence across all
documents. A prompt showing `[미수록 문서]` cannot establish either condition.
This is a semantic failure, not a model-quality result.

## Runtime envelope

The base prompt is roughly 3.8k input tokens and 0.76k completion tokens per
fast-panel notice. In EXP139 the focused five-item extra call added about 3.3k
prompt and 0.16k completion tokens. Two specialist calls should be profiled
after rendering, but a conservative planning range is 2.4–3.0× baseline work:
about 82–108 minutes from the observed 34-minute submission. This is viable
only if exact admission and a staged offline runtime smoke test later confirm
it; four calls have no safe margin.

The exact Gemma chat-template count on dev-200 for the rendered EXP142
specialist prompts, with every source document included, was measured on
2026-09-07 with a 14,848-token admission budget (16,384 model length minus
1,536 output reserve):

| Specialist | Full-prompt median | p95 | maximum | Fits in one 16k pass |
| --- | ---: | ---: | ---: | ---: |
| B: qualification/document/procedure | 11,009 | 29,170 | 31,410 | 134 / 200 |
| C: product/absence | 10,590 | 28,741 | 30,990 | 136 / 200 |

So a full-document B+C design requires overflow handling for roughly one
third of dev notices. Combining that overflow splitting with both specialists
would recreate the context × group runtime multiplication that previously
timed out. Conversely, retaining 4,000 characters violates v9 and the
absence-item document scope. **EXP142 remains preview-only and is rejected as
a paid candidate.**

## Mandatory gates before any remote call

1. Build profile-specific concise cards from
   `docs/semantic_input_contract_v1.md` and retain per-card organizer-ledger
   source keys. Do not reuse a prior card merely because it has a similar name.
2. Render actual A/B/C messages for a complete, overflow, and attachment
   notice in **each applicable metadata profile**. Read them.
3. For every active item, record the exact system/user span that carries its
   applicability condition, 1-condition, material 0-condition, document scope,
   and needed metadata/CSV fact. Missing one makes the config invalid.
4. Verify A is byte-identical to the organizer control except for its declared
   output contract. Verify B/C have no unrelated-item instructions or internal
   routing names.
5. Run preflight, full-cohort tokenizer admission, mock parsing/evidence test,
   and a call-count/runtime projection. Only then run a small frozen cohort.
6. Fast panel, independent holdout, then dev-200 are separate gates. No
   item-specific label rule or merge change may be added between them.

## Rejected alternatives

- Full split with any grouping: already exceeds runtime through the context ×
  group product.
- Voting/majority across calls: no legal interpretation; it can erase a single
  real violation found by the only relevant specialist.
- Positive-only verifier as the main strategy: cannot repair first-pass FN.
- Raw-law/reference bundles: repeatedly harmed quality and violate the current
  card-only prompt policy.
