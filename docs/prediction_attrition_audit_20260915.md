# Prediction attrition versus model error

Offline saved-output audit; no legal inference, paid calls, merge or submission changes.

```bash
.venv/bin/python scripts/analyze_prediction_attrition.py \
  --run-dir outputs/exp-208-relation-checklist-after-source-dev200-c4 \
  --run-dir outputs/exp-209-corrected-input-direct-dev200-c4 \
  --output outputs/prediction-attrition-audit-20260915/report.json
```

| run | parse-error records | final errors on those records | clean-record FP/FN | raw comparable |
| --- | --- | --- | --- | --- |
|208|5|0FP/1FN|78/101|179/200|
|209|0|0/0|100/107|185/200|

Raw comparison uses only a single-pass, non-staged, valid full24 JSON response, including the
known `판정` wrapper. Multi-pass concatenations, incomplete/malformed JSON and staged outputs
are excluded, not defaulted to all0. On all comparable records there are **zero raw→model
label changes**. This is scoped evidence against parsing/evidence normalization being the
main label-loss source, not proof every excluded response has lossless handling.

Recorded pre-postprocess→final changes are33 in208 and28 in209, all v2/v3/v21 and all improve
the saved dev labels. These historical frozen Python rules are not authorization to create
more label rules. No postprocess changes occur for other21items. Current model-owned numbers
must remain separate from historical final score; all current-card hypotheses preserve this
incumbent behavior instead of hiding it in a V-only serialization claim.

The only final error on208 parse-error records is v17/PPS-DEV-21 FN. These data cannot establish
that fixing malformed outputs would recover all clean-record101FN. They also cannot establish
counterfactual behavior if the same requests were rerun; do not select favorable repeats.

## Direction change supported by this audit

Do not prioritize an E-only extraction algorithm or generic JSON recovery as a solution to
V-label quality: directly comparable V/E raw labels are already wrong, not lost during decoding.
Completion reduction may help runtime, but V-only still requires independent label improvement.
The remaining main work is model-owned applicability/semantic-role/condition execution under
complete original sources. New schema or repeated verifier must have a source-proven unmet
truth-condition requirement, not just these error counts. v24/v9 source uncertainties are
separate from clean parse failures; retain them rather than forcing gold-derived card corrections.

Audit tests cover multipass/staged exclusion, malformed/partial/wrapper behavior, error counts,
and separation of raw-normalization versus postprocess stages.
