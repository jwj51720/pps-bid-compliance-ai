# INC-040 Result: v2 Below-Notice Performance Restriction

The organizer's 2026 notice fixes the goods/services threshold at 230,000,000
won. Combining that law value, raw estimated price/work type, and an explicit
bidder-eligibility performance condition yielded dev TP/FP/FN **7/0/0**, F1
1.00000, with all evidence source-contained.

The initial implementation had three false positives because it equated proof
submission with entry restriction. Those notices used performance as proposal
evaluation or supporting-document material. The final predicate requires a
holder/eligibility construction, which is the legal distinction under the
item—not a price or source-length adjustment. No further phrase tuning is
authorized from dev.

The unlabeled-format scan in INC-041 found 170 source-evidenced v2 candidates
among 20,000 notices. This verifies parser provenance only; it neither labels
the corpus nor estimates hidden-test prevalence or F1.
