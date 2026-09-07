# INC-070: Source-Audited Legal-Essence Cards

## Hypothesis

The prior legal-context failures may reflect lengthy raw statutes and a
single-item v20 absence prompt, rather than the value of a compact,
source-grounded explanation of each item's legal test.  A reusable card must
state the applicability precondition, violation condition, and exceptions or
unresolved boundary without introducing any condition not supported by the
organizer material.

## This is a card-quality gate, not a score experiment

For every `v1`–`v24`, the generator sees the organizer item table and each
complete legal unit resolved by INC-023.  It proposes three short Korean
statements.  A separate call sees both the same complete source packet and the
proposal, then either accepts it or returns `accepted=false` and a conservative
correction.  The run retains both raw responses, source hashes, source IDs,
and unresolved citation records.  It does not use development labels.

The 512-token reserve is not a length tuning parameter: it reserves capacity
for the three semantic fields and the source audit response.  The prompt
requires 1–2 sentences per field; it never asks for a character count.

## Preconditions and stop rule

- The only factual inputs are organizer-supplied item table and law files.
- Each cited legal unit is the complete hashed unit from INC-023; no
  retrieval-ranked excerpt or arbitrary prefix is supplied.
- Manual/unmapped citations stay explicitly unresolved.  The generator and
  reviewer may not infer their contents.
- Maximum 48 calls and `$0.50`.  Any transport failure is recorded per item;
  no silent retry with altered wording is allowed.

## Promotion / branches

| Outcome | Next action |
|---|---|
| All 24 cards source-audited | Run INC-071: full ordered notice + identical flat labels, no-card control versus card treatment on a fixed positive-cover cohort, two repeats. |
| Some cards rejected | Do not fill gaps by legal memory. Test only the accepted-card subset as a declared partial mechanism, or repair the source-boundary audit first. |
| Cards accepted but INC-071 loses | Reject global card injection. Preserve cards as an e-prime extraction vocabulary only and test the two-stage route with full-notice fallback. |
| Cards improve in both paired repeats | Confirm once on dev-200 before composing with INC-041 or designing evidence transport. |

The later e-prime route is deliberately distinct: it will first create a
short, non-verbatim source-grounded `e′` only when a potentially relevant
notice fact exists; an e′-only decision is used only for those cells, while an
empty e′ is routed to the full-notice direct decision rather than becoming a
zero.  This prevents extraction omission from silently becoming a false
negative.
