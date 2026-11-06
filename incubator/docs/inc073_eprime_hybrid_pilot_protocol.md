# INC-073: e-prime Hybrid Pilot

This tests the user-proposed decomposition without treating absent extraction
as a negative label.  The eleven source-audited legal cards are vocabulary for
extraction, not direct decision context.

For every notice, repeat, and item:

1. **Direct control:** full notice and metadata produce `v/e`.
2. **e-prime extractor:** the same full notice plus cards produces a 1–2
   sentence non-verbatim relevant-fact summary or `null`. It emits no labels.
3. **e-prime adjudicator:** cards plus e-prime, without notice, produces flat
   labels. The final hybrid uses this label only where e-prime is nonempty;
   otherwise it uses the direct control's full-notice label and evidence.

The twenty-notice cohort has one deterministic positive anchor per target and
nine independent comparison notices. Two repeats use 120 calls, capped at
`$0.45`. This is an extraction/decision mechanism pilot, not submission
evidence policy: e-prime text is never emitted as evidence.

Advance only if positive e-prime coverage is at least the direct-control
positive coverage and both hybrid-minus-direct Macro-F1 deltas are positive.
Otherwise reject e-prime as a decision replacement; its source retrieval value
may still be separately audited, but no blank extraction may be merged as 0.
