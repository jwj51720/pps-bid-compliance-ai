# EXP228/229 — v5 attention versus numeric-operand completion

## Audited gap

The organizer-provided item table maps v5 to National Contract Act Enforcement
Decree article 21, the finance-minister threshold notice, Local Contract Act
Enforcement Decree article 20, and its Enforcement Rule article 24. Its note
also explicitly warns that the local threshold varies by local-government
class. The organizer-provided 2026 finance notice states the WTO threshold for
national goods/services as KRW 230 million and separately states KRW 710
million for public enterprises and quasi-government institutions. The supplied
local execution standard's chapter 4 table states that ordinary goods/services
use the MOIS-notified amount for provinces/metropolitan cities other than
Sejong, KRW 500 million for Sejong/cities/counties/districts, KRW 330 million
for listed technical services, and KRW 150 million for safety inspection.

The current v5 card says only `고시금액 이상` and the rendered metadata supplies
an `입찰추정가격`, but no numeric threshold or branch-selection instruction. The
model is therefore asked to perform a comparison without one operand.

This may be distinct from attention dilution. EXP205 misses the sole fast v5
positive and EXP206 misses the sole holdout positive; EXP208 dev200 has v5
TP/FP/FN `1/1/6`. We isolate the causes sequentially.

## EXP228: existing-card v5-only attention control

- base: EXP205 fast20;
- changes: active item v5, subset profile, removal of the relation-checklist
  mode because that checklist contains no v5-specific instruction;
- current `decision_cards_v10_v6_v7_scope.json` remains unchanged;
- output remains model-owned v5/e5;
- cards, readable metadata, organizer semantics, all admitted documents,
  tokenizer admission, provider/model, evidence validation, and postprocess are
  unchanged.

Merge only v5/e5 onto the frozen EXP205 output. This measures whether item
attention alone recovers v5.

### EXP228 result

- 20 calls, 248,735 prompt tokens, 880 completion tokens, 20.347 seconds;
- no parse failure or source-admission failure;
- v5 changed from TP/FP/FN `0/0/1` to `1/4/0`, F1 `0` to `0.333333`;
- merged macro positive-F1 changed from `0.325000` to `0.338889`;
- the sole positive `PPS-DEV-049` was recovered, but `PPS-DEV-072`,
  `PPS-DEV-036`, `PPS-DEV-039`, and `PPS-DEV-32` became false positives;
- the observed false positives include estimates far below the relevant
  thresholds. Attention recovers the region clause but cannot reliably apply
  the missing amount operand.

This is sufficient to activate EXP229. It also rules out “v5 only” as the full
fix: attention improved recall but precision collapsed to 0.2.

## Conditional EXP229: v5-only numeric card

Only if EXP228 still misses positives or shows that the threshold is
indeterminate, create a new card version changing v5 alone. Its compact card
must state:

- compare `입찰추정가격`, not budget or bid price;
- 2026 national-contract ordinary goods/services threshold: KRW 230 million;
- public-enterprise/quasi-government contract-rule threshold: KRW 710 million;
- apply 710 million only when the organizer `소관구분` explicitly identifies
  `공기업` or `준정부기관`; do not guess an institution class from its name;
- for local contracts, preserve the organizer-law branches: KRW 500 million for
  Sejong/cities/counties/districts, the MOIS-notified amount for other
  provinces/metropolitan cities, and separate technical-service thresholds;
- do not guess a local-government class or collapse special technical services
  into the ordinary-goods/services branch;
- retain actual participation-region role and all existing exceptions/0
  conditions.

This is a card-completeness correction sourced from organizer law material, not
a Python label rule. EXP229's base is EXP228 and its sole allowed policy change
is the decision-card path. No other item text changes.

## Shared gates and sequence

Each paid arm needs its own plan/config, preflight, exact full-source audit,
actual short/attachment/largest rendered review, active v5 semantic contract,
mock, merge audit, and tests. Run fast20 first. A candidate advances unchanged
to independent holdout only if v5 F1 and merged macro improve without malformed
or source failures; dev200 requires matching holdout direction.

Record source citation, structural card diff, calls/tokens/runtime, TP/FP/FN,
evidence validity, and changed-cell ledger. Do not add numeric facts to other
cards until v5 establishes whether completing the operand is useful.

## Source provenance for EXP229

- organizer item table, v5 record, lines 40–45: truth-condition mapping and the
  warning that local thresholds differ;
- organizer 2026 finance-minister threshold notice, lines 8–12: national WTO
  goods/services KRW 230 million;
- the same notice, lines 60–64: public-enterprise/quasi-government WTO
  goods/services KRW 710 million;
- organizer local execution standard, chapter 4 table around lines 2441–2457:
  regional-restriction branches and the KRW 500/330/150 million values.

Raw law text is used only to audit and compress this card. It is not injected
into the model prompt.

## EXP229 pre-provider gate — 2026-09-14

- The generated v12 artifact differs from v10 in `v5.prompt_text` only; v1–v4
  and v6–v24 are byte-equivalent at the card-text level.
- Preflight reports exactly one declared effective change:
  `prompt.decision_cards_path`.
- Exact dev200 admission retains all 374/374 documents across 200 records, with
  zero source, metadata, active-card, organizer-semantics, or budget omissions;
  all 200 records remain one pass in this v5-only topology.
- Exact fast20 mock completed 20/20. Rendered messages were read at
  `PPS-DEV-062` (short), `PPS-DEV-194` (attachments), and `PPS-DEV-169`
  (largest). Each contains the numeric v5 card, readable comparison metadata,
  and every admitted original document.
- The active-item semantic contract passes for all three rendered reviews. The
  positive `PPS-DEV-049` additionally shows the 지방계약법, 일반용역,
  KRW 600 million estimate, 교육기관 fact, and the actual Gyeongsangnam-do
  participation restriction together in the exact message.
- Exact mock output and 212 tests pass.

Immediately before the paid call, all elements required by the hypothesis are
implemented and selected: v5 alone is active, v12 is selected, full source and
readable metadata are retained, and no merge, provider, schema, or Python-label
policy changed. The fast provider call is approved.

## EXP229 fast20 result

- provider call: 20 calls, 253,295 prompt tokens, 690 completion tokens,
  20.4 seconds, parse error 0, specialist evidence validation warning 0;
- frozen EXP205 base macro `0.325000` -> merged EXP229 `0.352778`;
- v5 TP/FP/FN `0/0/1 -> 1/1/0`, precision `0.5`, recall `1.0`, F1
  `0 -> 0.666667`;
- changed non-v5 cells: 0; both predicted-positive v5 evidence spans validate;
- versus the existing-card EXP228, the numeric card preserved the true positive
  while removing three of four false positives.

The remaining false positive is `PPS-DEV-039`. Its exact rendered message
contains `국가계약법`, `일반용역`, `소관구분: 준정부기관`, estimate KRW
63,636,364, and the KRW 710 million card threshold, yet Gemma returned v5=1.
This is not an input-availability failure; it is a failure to execute an
explicit numeric comparison. No post-hoc wording is tuned from this case.

The fast gate passes. EXP230 repeats the identical specialist policy on the
independent holdout and composes v5/e5 only onto frozen EXP206.

## EXP230 holdout pre-provider gate

- Preflight finds no policy difference from EXP229; only the declared cohort
  and isolated output location change.
- Exact admission again reports 374/374 dev200 source documents, zero semantic
  or metadata omissions, zero over-budget packs, and 200/200 one-pass records.
- Exact holdout mock completed 20/20. Rendered messages were read at
  `PPS-DEV-094` (short), `PPS-DEV-046` (positive with attachments), and
  `PPS-DEV-27` (largest); the active v5 contract passes all three.
- `PPS-DEV-046` contains the organizer-preserved
  `[수요기관(기초자치단체)]` type, 지방계약법, 물품, estimate KRW
  555,308,000, and the actual Gyeonggi-do headquarters restriction. Thus both
  operands and the applicable KRW 500 million branch are present without
  guessing the hidden institution name.

The identical frozen holdout call is approved.

## EXP230 independent holdout result

- provider call: 20 calls, 249,039 prompt tokens, 658 completion tokens,
  21.076 seconds, parse error 0, specialist evidence warning 0;
- frozen EXP206 base macro `0.208333` -> merged EXP230 `0.250000`;
- v5 TP/FP/FN `0/0/1 -> 1/0/0`, precision/recall/F1 all `1.0`;
- changed non-v5 cells: 0 and the positive evidence span validates.

The improvement direction agrees with fast20 and precision improves rather than
collapsing. EXP231 therefore extends the unchanged v5 specialist to dev200. It
will be evaluated both on frozen EXP208 and after the independently validated
EXP221 v4 specialist composition. No prompt or card wording changes are allowed.

## EXP231 dev200 result

- provider call: 200 calls, 2,408,396 prompt tokens, 5,505 completion tokens,
  201.815 seconds, parse error 0, specialist evidence warning 0;
- v5 TP/FP/FN improves from EXP208 `1/1/6` (F1 `0.222222`) to `7/4/0`
  (precision `0.636364`, recall `1.0`, F1 `0.777778`);
- EXP208 macro `0.292959` -> v5-composed `0.316107`;
- independently composed EXP221(v4) macro `0.306117` -> v4+v5 composition
  `0.329265`, the best local dev200 result so far;
- all 7 v5 positives are recovered; 11 predicted positives have valid evidence;
  changed non-v5 cells 0.

The four false positives are `PPS-DEV-09` (national goods, KRW 112.064m),
`PPS-DEV-10` (quasi-government service, KRW 122.727m), `PPS-DEV-039`
(quasi-government service, KRW 63.636m), and `PPS-DEV-071` (local service,
KRW 427.273m). They again show that Gemma sometimes ignores an explicit
less-than comparison even in a one-item message. Nevertheless, the fast,
holdout, and dev200 directions agree and the recall/precision trade is strongly
positive. The numeric operand correction is validated; remaining arithmetic
execution is a separate future hypothesis.
