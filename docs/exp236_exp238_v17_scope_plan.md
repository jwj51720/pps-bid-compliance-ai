# EXP236–238 — v17 enterprise-class inversion correction

## Audited card defect

Organizer law, SME Product Purchase Promotion Act Enforcement Decree article
2-2(1)(1), requires below-KRW-100-million goods or services to be procured from
small enterprises or small businesses, subject to explicit exceptions. It may
allow the broader SME class only under stated conditions such as a clearly
small eligible pool or failed tender. Article 2-3 contains additional explicit
exceptions.

The current v17 card incorrectly treats `중소기업·소기업·소상공인 한정` alike
as the violation condition. That erases the central class distinction: a
small-enterprise/small-business-only restriction is the normal rule, while an
unjustified `중소기업`/`중·소기업` restriction admits medium enterprises and is
the suspect v17 condition.

This is visible without extrapolating a broad schema. EXP205 misses the fast
positive `PPS-DEV-042`; EXP206 misses the holdout positive `PPS-DEV-053` and has
two false positives. Both positives are below KRW 100 million and their source
text explicitly says `중·소기업`, which includes medium enterprises.

## Experiments

- EXP236: v17-only attention control with unchanged v10 card on fast20.
- EXP237: same v17-only topology, but a new card changing v17 alone to preserve
  the broad-SME versus small-only distinction.
- EXP238: policy-identical corrected-card independent holdout, only if EXP237
  improves v17 F1/precision over EXP236 without losing the positive.

All arms retain card/metadata/product facts, every admitted source document,
exact tokenizer admission, V/E ownership by Gemma, evidence validation, merge,
and provider parameters. Only v17/e17 is composed onto frozen EXP205/206.
Python performs no enterprise-class or label rule.

The corrected card also states that product lookup unknown is not itself a
label and that explicit statutory exceptions must be checked. It does not
modify product lookup code, v15, v18, or any absence logic.

## Gates

Declare base/allowed changes; preflight; confirm the generated card differs
only at v17; exact admission and semantic contract; read short, attachment, and
largest rendered messages; exact mock; tests; then fast. Holdout is required
before any dev200 extension. Record runtime, tokens, parse errors, TP/FP/FN,
evidence validity, and changed cells.

## Pre-provider gate and fast results

- The generated v14 artifact differs from v10 at v17 only. Preflight reports
  exactly the declared subset changes for EXP236 and only the card path for
  EXP237.
- Exact admission retains 374/374 documents, all required metadata/product
  renderers, zero over-budget packs, and 200/200 one-pass topology. Exact mocks,
  short/attachment/largest plus positive semantic reviews, and 212 tests pass.
- EXP236 existing-card control: 20 calls, 20.6 seconds; v17 `0/1/1`, F1 `0`;
  merged macro remains `0.325000`.
- EXP237 corrected card: 20 calls, 21.7 seconds; v17 `0/0/1`, F1 `0`;
  merged macro remains `0.325000`.

The corrected card removes the control's false positive but still misses the
fast positive, so EXP238 is not run. Inspection identifies an input-semantic
limit rather than another prose defect: `PPS-DEV-042` is a general service with
no detailed product code. Its exact-code competition-product fact is therefore
unknown. The message contains the amount and broad `중·소기업` restriction but
does not contain a definitive negative fact that the service is not an
applicable competition product. The card correctly refuses to turn unknown
lookup into a negative-product assertion, and Gemma returns 0.

Do not tune v17 further from this panel. A future candidate must establish a
source-grounded, reproducible applicability representation for no-code services
without treating lookup failure as proof. That is a separate input-completeness
hypothesis, not a prompt-emphasis change.
