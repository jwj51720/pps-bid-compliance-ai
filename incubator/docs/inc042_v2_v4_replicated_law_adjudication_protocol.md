# INC-042: Replicated v2/v4 Law-Adjudication Pilot

## Cohort, fixed before calls

The cohort contains every dev notice positive for v2 or v4 (10 notices) plus
every notice negative for both that has a source-line `실적` + Korean-won
amount fact (26 notices): 36 notices total. This is a hard-negative mechanism
cohort, not a performance estimate for all dev.

## Four-arm design

Each notice receives four otherwise identical active two-item requests:

1. `control_r1`: no law context;
2. `law_r1`: complete item-linked organizer legal units;
3. `control_r2`: exact repeat of control_r1; and
4. `law_r2`: exact repeat of law_r1.

The legal arm includes the complete organizer 2026 notice-amount text; national
guideline Article 5 and implementing-rule Article 25; or local guideline
contract-officer caution section and implementing-rule Article 25. It never
uses a character excerpt or a development-derived threshold. Each prompt holds
all notice documents in source order and raw metadata.

## Structured-output and decision gates

JSON-schema output is source-evidence validated. A malformed, missing, or
invalid-evidence response is recorded as a transport/format failure, **not** as
a zero prediction; an arm with any failure has no promotable metric. Raw
responses, usage, request hashes, and per-notice records are checkpointed.

This pilot may advance to dev-200 only if both law repeats complete without
format failure, each improves the two-item macro F1 over its matched control,
and their law-minus-control deltas have the same non-negative direction. A
single favorable arm, or an apparent gain accompanied by response instability,
is rejection/diagnostic evidence rather than a policy.
