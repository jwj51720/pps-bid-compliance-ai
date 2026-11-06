# EXP232–235 — v15 attention, product scope, and exception scope

## Audited failure

EXP208 dev200 v15 is TP/FP/FN `0/2/6`; EXP205 fast and EXP206 holdout each
contain one v15 positive and both are missed. In both panel positives the exact
rendered source already contains the estimate and the small-enterprise or
small-business participation clause.

The item table maps v15 to the SME Product Purchase Promotion Act Enforcement
Decree articles 2-2 and 2-3. Organizer law says:

- article 2-2(1)(2): procurement of goods **or services** from KRW 100 million
  to below the applicable notice threshold ordinarily uses an SME restriction;
- article 2-3: specified exceptions permit the public institution not to use
  the priority-procurement method;
- the nonprofit-service exception does not state that an actually retained
  small-enterprise restriction ceases to exist. Adding eligible nonprofits can
  coexist with a restriction that still excludes ordinary larger for-profit
  firms.

The current v15 card has two possible suppression mechanisms: all-24 attention
dilution, and an over-broad instruction to return 0 whenever a
`판로지원 예외` exists. Its `일반제품` wording may also be misread as goods-only,
although the organizer statute explicitly covers goods or services.

## EXP232/233: existing-card attention control

Run v15 alone with the unchanged v10 card, first on the versioned fast20 and
then, only if useful diagnostically, on the independent holdout20. Preserve
readable metadata/product facts, all admitted original documents, tokenizer
admission, V/E schema, evidence validation, model/provider parameters, and
postprocessing. Merge only v15/e15 onto frozen EXP205 or EXP206.

The allowed fast policy changes are only `prompt.active_items`,
`prompt.profile`, and removal of the all-item relation checklist via
`prompt.mode=baseline`. The holdout is policy-identical.

## Conditional EXP234/235: corrected v15 scope card

Only if the controls show the predicted pattern, generate a new card version
changing v15 alone. It must:

- retain the KRW 100 million lower bound and applicable notice-threshold upper
  bound, using `입찰추정가격`;
- say `물품 또는 용역`, consistent with organizer law;
- exclude a confirmed applicable competition product, but not turn an unknown
  product lookup into either an automatic positive or negative;
- distinguish an exception that actually removes the small-enterprise
  restriction from a notice that admits a specified nonprofit class while
  still restricting ordinary for-profit participants to small enterprises;
- keep the final label model-owned and make no Python legal rule.

EXP234 would change only the decision-card path versus EXP232. If fast succeeds,
EXP235 repeats the wording unchanged on holdout. Dev200 is allowed only if the
independent direction agrees.

## Required gates

For every paid arm: declare base and allowed changes, preflight, exact admission,
read short/attachment/largest rendered messages, audit the active v15 semantic
contract, mock, tests, and isolated outputs. Record calls, runtime, tokens,
TP/FP/FN, evidence validity, and the changed-cell ledger. Do not modify v14,
v16, product lookup code, merge logic, schema, or provider settings in this
experiment family.

## Existing-card control results

Both controls passed preflight, retained 374/374 dev200 source documents with
zero semantic/metadata/budget omissions and 200/200 one-pass topology, passed
exact panel mocks, and passed the active v15 rendered semantic reviews.

- EXP232 fast: 20 calls, 21.8 seconds; v15 `0/0/1 -> 1/5/0`, F1
  `0 -> 0.285714`; merged macro `0.325000 -> 0.336905`.
- EXP233 holdout: 20 calls, 21.9 seconds; v15 `0/0/1 -> 0/4/1`, F1 remains
  `0`; merged macro remains `0.208333`.

The pattern confirms that item attention finds enterprise clauses but does not
execute the class/scope distinction. Every listed holdout false positive uses
the broader `중소기업` or `중·소기업` class. The holdout true positive
`PPS-DEV-080` instead says `소기업·소상공인`, but also admits eligible
nonprofits under article 2-3 and is suppressed. The corrected-card arm is
therefore activated; this is not a generic prompt rewrite.

## Corrected-card pre-provider gate

- The generated v13 artifact differs from v10 in v15 prompt text only.
- EXP234 preflight reports only the declared card-path difference; EXP235 has
  no policy difference from EXP234.
- Both configs retain 374/374 source documents, all required metadata/product
  semantics, zero over-budget packs, and 200/200 one-pass dev topology.
- Exact fast and holdout mocks complete 20/20; short, attachment/positive, and
  largest rendered reviews pass the active v15 semantic contract.
- 212 tests pass. No schema, product lookup, merge, provider, or Python label
  behavior changed.

All elements required by the corrected scope hypothesis are implemented and
selected. EXP234 fast is approved; EXP235 is paid only if fast precision/F1 is
better than the existing-card control without losing its positive.

## Corrected-card results and decision

- EXP234 fast: 20 calls, 24.9 seconds; v15 `1/2/0`, precision `0.333333`,
  recall `1.0`, F1 `0.5`; merged macro `0.345833`. Compared with the existing
  card, false positives fall from five to two while the positive is retained.
- EXP235 independent holdout: 20 calls, 21.8 seconds; v15 `0/2/1`, F1 `0`;
  merged macro remains `0.208333`. The true positive `PPS-DEV-080` is still
  missed, while broader-SME records `PPS-DEV-050` and `PPS-DEV-132` are false
  positives; one of those lacks valid evidence.

The independent direction does not agree, so this path stops before dev200.
The card correction is legally better scoped but Gemma does not reliably bind
the `소기업` versus `중소기업` distinction or the nonprofit exception to its
label. Do not tune again from these panel IDs and do not promote v13 to a
canonical card. A future retry would require a genuinely different factual
relation representation, not stronger prose around the same card.
