# INC-072 Result: Controlled Legal-Essence Card Injection

## Valid comparison

This replaces invalid INC-071.  Both arms used byte-identical system prompts
that enumerated the same eleven item names, absence policy, and evidence
contract.  Both received metadata and every complete ordered source document.
The card arm alone received the compact source-audited legal-essence block.
All 96 calls parsed and passed source-evidence validation.

| Repeat | Control target Macro F1 | Card target Macro F1 | Delta | Control TP/FP/FN | Card TP/FP/FN |
|---|---:|---:|---:|---:|---:|
| r1 | 0.18680 | 0.18939 | +0.00260 | 6 / 22 / 14 | 5 / 16 / 15 |
| r2 | 0.20195 | 0.14394 | -0.05801 | 6 / 20 / 14 | 4 / 15 / 16 |

Actual cost was `$0.09644`, below the `$0.40` ceiling.

## Decision

Reject global direct injection of the legal-essence cards.  It does reduce
false positives, but it also loses true positives; the direction is not
repeat-safe.  In particular, both card repeats lost v11's recovered positives;
v23 also fell in r1/r2.  Small apparent improvements for v4/v18 do not meet
the per-item or repeat requirements and must not be merged into INC-041.

## Research consequence

The legal summary may still serve as *controlled vocabulary*, but not as a
direct decision prior.  The next distinct branch is the requested e-prime
architecture: source-grounded semantic fact extraction first, e-prime-only
adjudication only for nonempty extraction, and full-notice direct fallback for
empty extraction.  That design tests whether summaries focus attention without
turning absence of extraction into a label zero.  It requires a fresh transport
and coverage audit; INC-064's rationale-to-retrieval result means BGE ranking
cannot be used as a label gate.
