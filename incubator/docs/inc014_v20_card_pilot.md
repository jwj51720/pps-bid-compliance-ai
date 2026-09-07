# INC-014: v20 Law-Card Paired Pilot

This is the paid follow-up to INC-013. It compares two v20-only Gemma calls:
the same full notice, metadata, model, seed, JSON schema, and output limit;
the treatment alone receives the organizer-law fact card. The card is fixed
context, never evidence. Both arms use a source-only contract and must return
one binary decision.

Cohort: all five dev v20 positives plus ten deterministic negatives selected
from records with both unknown `정보화사업여부` and an SW source cue. Negatives
are first matched by raw estimated-price distance, then filled in stable price
and ID order. This preserves the failure mode that a metadata-only gate would
miss, without selecting on model outcomes.

Success requires treatment TP at least 3/5, treatment F1 strictly above the
control, and treatment FP no more than control + 1. A failure rejects this
card as a v20 policy; it does not change the root pipeline.

## Result

All 30 paired requests completed with valid schema output. The source-only
control achieved TP/FP/FN 3/1/2 (precision 0.75, recall 0.60, F1 0.66667).
The fact-card treatment achieved 4/0/1 (1.00, 0.80, 0.88889), a +0.22222 F1
change at $0.05085 total cost. It passes every preregistered gate.

Only two paired decisions changed: one matched negative changed 1 to 0, and
one positive changed 0 to 1. The other 13 pairs were stable. This is a strong
small-cohort signal, not sufficient evidence to promote a final policy: all
five dev positives are already in this pilot and the ten negatives were
selected. The next test must use all 200 dev notices as a paired control/card
confirmation, preserving the same full-document admission and then measuring
the 195-negative false-positive rate. Do not tune card wording or the cohort
before that confirmation.
