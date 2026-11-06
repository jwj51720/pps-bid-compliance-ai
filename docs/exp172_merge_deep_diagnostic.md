# EXP172 direct complete-source: merge/error deep diagnostic

## Question and fixed policy

This is an offline analysis of the completed `exp-172-complete-source-2500-dev200-c4`
checkpoint, not a new prompt experiment.  It answers whether its dev-200 macro
positive-F1 `0.259281` is principally caused by tokenizer-overflow merge, or by
the individual full-source model calls.  The checkpoint's policy is unchanged:
all source documents, complete-fact cards/metadata/product fact, `single` with
exact-token overflow packs, OR for non-absence items, AND for the five absence
items, and the pre-existing EXP123 frozen replacements for v2/v3/v21.

The reproducible analysis command is:

```bash
PYTHONPATH=. python3 scripts/analyze_exp172_merge_diagnostics.py \
  --predictions outputs/exp-172-complete-source-2500-dev200-c4/predictions.jsonl \
  --labels data/raw/open/dev_labels.csv \
  --records data/raw/open/dev.jsonl.gz \
  --output-dir outputs/exp172-merge-diagnostics-v1
```

The ignored output contains `report.json` (all per-item counts and overflow
notice IDs) and `report.md` (readable table).  The counterfactual `first with
frozen fixed` keeps v2/v3/v21's submitted frozen replacement identical and
changes only the model-pass selector.  It is therefore the valid merge-effect
comparison; `first`, raw OR, and raw AND are audit-only diagnostics.

## Result: merge is not the main cause

- There are 200 notices and 216 individual calls: 186 notices have one pack,
  12 have two, and two have three.  Thus 93% of notices and 91.6% of label
  cells cannot possibly be affected by cross-pack merge.
- Actual final labels have 45 TP, 78 FP, and 108 FN across 153 gold positives
  (precision 0.366, recall 0.294).  The problem is not simply an always-1
  model or an always-0 model: it has both a substantial recall failure and a
  concentrated false-positive failure.
- Of all final errors, 70 FP and 105 FN occur in one-pack notices; overflow
  notices contain only 8 FP and 3 FN.  The seven first-to-policy-raw merge
  changes are v22=1, v23=2, v3=3, v21=1.  v3/v21 are then overridden by the
  frozen replacement, leaving only v22 and v23 as material ordinary-model
  merge changes.
- Macro positive-F1 is `0.261069` with frozen replacements fixed and first
  pack selected, versus actual merged `0.259281`: a -0.001788 delta.  This
  rejects "the 0.26 is mainly OR/AND merge damage" for EXP172.

The raw-pass macro values are deliberately much lower (`first 0.182500`,
`policy_raw 0.177321`) because the frozen v2/v3/v21 replacement contributes
three perfect items.  They must not be cited as a direct full-source model
score.

## Error tendencies that are actually visible

1. **Systematic all-zero blind spots.** v6, v7, v10, v11, v14, v16, v18 and
   v20 each emit zero for every one of the 200 notices despite 5--8 gold
   positives per item.  v10/v11/v16/v18/v20 are absence items, but the same
   all-zero failure also appears in non-absence v6/v7/v14.  This is an
   individual-call/card-fact integration failure, not an AND merge effect:
   their pass patterns are uniformly `0`, `00`, or `000`.
2. **v23 is an over-broad date detector, not a valid relationship decision.**
   It produces 26 positives for five gold positives (1 TP, 25 FP, 4 FN;
   precision 0.038).  Twenty-five of its FP have date/e-bid/price-bid/opening
   snippets such as `가격입찰서 제출` or `전자입찰서접수`; those are explicitly
   insufficient under the card, which requires local negotiated procurement,
   amount tier, and the role relationship among notice, briefing/proposal due
   date.  Nineteen of these FPs are single-pack.  Two overflow-related merge
   changes cannot explain the pattern.
3. **The product/SME and metadata-counterpart items are not being composed.**
   v13, v17, and v24 have no TP (respectively 8 FP/6 FN, 4 FP/6 FN, and
   6 FP/8 FN).  The positive v13/v17 snippets frequently identify a small
   business restriction but do not demonstrate that the model combined it
   with the exact competition-product/amount/exception preconditions.  v24
   often emits a source restriction or an empty evidence instead of an
   incompatible source-vs-metadata field pair.  All of these errors are in
   one-pack notices.
4. **Evidence is an early warning, not the cause of label score.** Several
   final positives for v13/v17/v23/v24 have empty evidence (the full counts
   are in the generated report), so weak source grounding accompanies the
   bad labels.  The current non-strict EXP172 policy retains those labels;
   changing that gate would be a separate, declared experiment, not a
   conclusion of this diagnosis.

## Consequence for next design

Do not spend the next experiment on replacing OR with AND, or on an
announcement-only split: the observed maximum merge effect is negligible and
the announcement-only controls already lost to complete source.  The smallest
justified structural probe is instead one relationship fact whose failure is
proven above (v23's date roles/contract-type/amount conjunction, or v24's
explicit source--metadata field-pair comparison), with source-only extraction
and final full-source recheck retained.  It needs its own plan, rendered-input
review, 24-item semantic contract audit, fast20 then independent holdout20;
this diagnostic does not authorize a prompt or rule change.
