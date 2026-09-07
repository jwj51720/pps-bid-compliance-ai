# INC-012: Gemma End-of-Context Decision Contract

This paired test holds the INC-006 frozen cohort, 12,000-character ordered
context, Joint-24 system prompt, model, seed, JSON schema, and output budget
fixed. Treatment adds only a final user-message decision contract after all
metadata and documents. It requests no raw reasoning: the model must emit JSON
only. The contract restates source-only judgment, no keyword-only positives,
exact source evidence for non-absence positives, and independent item decisions.

Success: Macro F1 +0.02, non-decreasing micro recall and evidence validity.

## Result

On the fixed 24-notice cohort, the control scored Macro F1 0.15480 (TP/FP/FN
9/36/28; micro recall 0.24324; evidence validity 0.82222). The end-contract
treatment scored 0.14167 (7/27/30; recall 0.18919; evidence validity 0.88235).
All 48 requests completed; actual estimated cost was $0.06601.

Decision: reject. The contract reduced false positives and improved evidence
validity, but failed its non-decreasing recall and Macro-F1 gate. It must not
be combined with another treatment as a presumed Gemma improvement.
