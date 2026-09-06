# INC-021: Retrieved-Law Family Passes

This is the first global treatment built from INC-020's permitted BGE-M3
organizer-law index. It preserves every notice's full document context, but
replaces the undifferentiated joint-24 decision with four disjoint legal-family
calls: qualification/geography (v1--v9), products (v10--v18), procedure
(v19/v21--v23), and SW/meta (v20/v24). Each receives the item-specific top
retrieved organizer-law excerpts as fixed context. Law text can inform a
decision but cannot serve as notice evidence.

This is not document-level OR merging: each item belongs to exactly one family
pass. Non-absence evidence is validated against the complete notice source;
absence evidence remains blank. The preserved INC-018 `single_full` dev-200
baseline is the comparator. Promotion requires Macro F1 above 0.24361,
evidence validity at least 0.70, and at least 95% transport/schema success.

## Result

798/800 requests succeeded at $1.39503. Macro F1 improved from INC-018's
single-full 0.19361 to 0.21074, while false positives fell 241 to 111 and
evidence validity rose 0.70690 to 0.96528. The promotion gate failed because
true positives fell 49 to 33 and macro improvement was only +0.01713.

The treatment is therefore not a final policy, but it changes the research
direction: retrieved law plus family attention is a high-precision verifier,
not yet a sufficiently sensitive detector. The fixed 165-character excerpts
were chosen only because a fixed 600-character-per-item card overflowed the
longest full notices. The next architecture should use longer law excerpts by
adaptive token admission (complete notice where it fits; an additional
notice-level pack only on overflow) rather than compressing every notice to
the longest-case budget. Do not OR single-full and RAG predictions: a
post-hoc union reaches only 0.2456 Macro F1 while increasing FP to 309.
