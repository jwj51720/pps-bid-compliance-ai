# INC-050: Competition-Product Applicability Fact-Sheet Pilot

## Why this branch

The best reproducible global composition (INC-041) is only 0.26750 Macro F1.
Its product family has the largest concentrated residual loss: v10--v18
contains six zero-F1 items and v13 has 115 false positives.  INC-019 already
rejects treating all nine product/procurement items as one card: product-code
coverage differs sharply by item and generic small-business words are nearly
ubiquitous in negatives.  This pilot therefore tests only the coherent
competition-product applicability subset `v10`--`v13`, without changing a
prediction outside it.

## Hypothesis

For these four items, Gemma's false positives stem partly from conflating a
generic small-business restriction with the joint applicability of product
status, amount, contract regime, and source restriction.  A deterministic,
organizer-source fact sheet may improve that distinction when the model still
receives the complete notice and the same item table.

The fact sheet is not a label, score, exception decision, or evidence.  It
contains only:

- metadata's raw estimated-price/budget values and contract-law value;
- an exact organizer competition-product lookup rendered in Korean as
  `confirmed matching product`, `codes present but no confirmed match`, or
  `no observable exact code`;
- unchanged source-line IDs/text for product-restriction vocabulary, available
  solely for `v12`/`v13` evidence selection.

It deliberately does not claim that a match, no match, unknown code, or any
word proves a violation.

## Fixed paired design

Both arms receive identical model, temperature, seed, JSON schema, full
ordered notice documents, metadata, and v10--v13 item-table definitions.

| Arm | Difference |
|---|---|
| `control` | No derived applicability fact sheet. |
| `facts` | Adds only the fact sheet defined above. |

Every non-absence positive (`v12`, `v13`) must select an unchanged source-line
ID.  `v10` and `v11` are absence items and return no evidence.  Missing or
invalid non-absence IDs downgrade that item to zero.  A lack of candidate ID
never mandates zero because the final judge has the entire notice.

The cohort is frozen before calls: every dev notice positive in at least one of
v10--v13, plus a deterministically hash-ordered set of source-fact strata
among remaining notices.  Strata use only product lookup state and cue burden,
not labels.  The manifest preserves the exact cohort and prompt hashes.

Each arm is executed twice under the same recorded settings.  Repeats measure
provider/model non-determinism; neither best repeat nor post-hoc ensemble can
be promoted.

### Structured-output recovery amendment (before scoring)

The first 144 calls produced 25 responses consisting only of whitespace until
the provider's 8,192-token ceiling, despite the requested JSON schema and
500-token cap.  These are transport/format failures, not negative judgments.
Before metrics were calculated, the protocol adds one and only one recovery
call for each such failed record/arm under the identical prompt, schema,
model, temperature, and seed.  The original raw response and usage remain in
the record artifact.  A second failure leaves that arm invalid; a recovery
output is neither selected by score nor combined with the first output.

The initial actual spend was $0.20290.  The observed maximum failed-call cost
was $0.006013, so one recovery for all 25 failures has a conservative upper
bound of $0.15033 and remains below the predeclared $0.40 ceiling.

## Admission gates before spend

1. The evidence candidate manifest must contain an unchanged selectable source
   line for every dev nonempty gold `e12`/`e13`.  Otherwise candidate-ID
   transport is not admissible and no calls run.
2. Prompts must retain all complete notice documents; no character limit,
   fragment truncation, or candidate-only context is allowed.
3. A preflight cost ceiling of $0.40 covers four arms across the frozen cohort.

## Decision gates

Promotion requires both repeats to improve target Macro F1 over their paired
control by at least 0.05, with non-decreasing target recall, no more than two
new false positives in either repeat, and 100% valid positive evidence after
the candidate-ID gate.  The 0.05 is a practical minimum for four labels in a
small pilot, not a future decision threshold.

Partial success means the direction is concordant but one repeat has lower
magnitude; it may receive one independently selected all-dev confirmation,
never a wording tune.  Failure rejects the product fact-sheet topology, not
the organizer product lookup itself.
