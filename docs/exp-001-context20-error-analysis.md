# EXP-001 Full-Context 20-Notice Error Analysis

## Result

With every supplied document included, the model made 40 binary disagreements against the first 20 dev labels: 25 false positives and 15 false negatives. It correctly found 7 of 22 gold positives. This is not a document-availability-only failure: only 5 disagreements belong to notices with any dropped document, and most positive evidence text is present in the full prompt.

This is a source-grounded audit of disagreements, not an independent relabeling exercise: the dev labels were available while reviewing the cases.

## Teacher Review

The labeled decisions are consistent with the supplied documents and official data in the high-impact error groups.

- **v2–v8:** The model sees performance or region wording but does not apply the price, governing-law, and combined-restriction gates. For example, `PPS-DEV-03` requires a 30-million-won performance record for an approximately 89-million-won local-service procurement: the label is v2, while the model incorrectly calls it v3. `PPS-DEV-06` has a national-agency-specific performance requirement, which belongs to v4 rather than generic v3.
- **v10–v18:** This is the dominant structural failure. `PPS-DEV-02`, `15`, `18`, and `19` contain small-business wording, but their detailed product codes (`5510150601`, `5030990101`, `1511151001`, `4010180602`) do not occur in the organizer's competitive-product CSV. They are therefore not v13 cases. Conversely, v15 requires the product/price regime from the official rules, which the current prompt never supplies.
- **v21:** The model treats every `5%` joint-contract clause as a violation. The applicable joint-contract rule and contract-law distinction are absent from its prompt.
- **v24:** The model makes five false mismatch claims without a defined field-by-field comparison procedure; it needs deterministic comparisons of budget, method, region, and industry fields.

## Conclusion

Gemma can read the documents: full context makes v9 perfect on this cohort and changes 13 decisions. But the 0.13214 score shows it cannot infer the 24 legal decision boundaries from short item names. The limiting missing input is not primarily notice evidence; it is the organizer-supplied legal context and deterministic facts that translate each item into a testable condition.

## Audit Artifact

Run the following to regenerate the 40 disagreement packets, each containing metadata, item-law references, evidence contexts, and document availability:

```bash
.venv/bin/python scripts/build_error_review.py
```

The artifact is `outputs/exp-001-context20-full-paid/error_review.json`.
