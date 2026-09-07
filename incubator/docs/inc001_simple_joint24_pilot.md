# INC-001: Simple Joint-24 Baseline Pilot

## Hypothesis

An independent, minimal implementation can make a successful, schema-valid
Gemma call for each notice and establish a reproducible behavioral baseline
before any retrieval, rule, or prompt-complexity experiment.

## Frozen policy

- One Gemma call per notice; all 24 items and evidence are generated together.
- Ordered document prefixes share a transparent 4,000-character total budget.
- Metadata and official item names/notes are included.
- No law chunks, decision cards, product facts, retrieval, rules, self-labels,
  splitting, or post-hoc label corrections are used.

The cohort is deterministic: greedy dev-positive item coverage followed by
historically difficult all-negative notices. It has 24 notices and covers every
item with at least one gold positive; it is deliberately a stress cohort, not a
prevalence estimate.

## Result

| Metric | Result |
|---|---:|
| Successful model requests | 24 / 24 |
| Macro positive-class F1 | 0.13036 |
| TP / FP / FN | 7 / 30 / 30 |
| Validity of generated non-absence evidence | 0.81081 (37 positive cases) |
| Invalid-evidence warnings | 5, all for v13 |
| Reported OpenRouter cost | $0.01657 |
| Sum of model latencies | 350.662 s |

Only v1 (0.800), v3 (0.500), v13 (0.095), v19 (0.400), v21 (0.333), and
v22 (1.000) had nonzero F1. The largest concrete failure is v13: 20 positives
for one gold positive, yielding 19 false positives. This supports the earlier
diagnosis that generic small-business wording is being mistaken for the
competition-product-specific violation.

The historical EXP-001 prediction stored locally scores 0.14605 on this same
cohort, with 95.14% label-cell agreement. The two implementations are not exact
prompt replicas; INC-001 is an operational baseline rather than a performance
comparison or a regression claim.

An initial pre-checkpoint transport attempt returned two successful responses
($0.00116 reported cost) before a later provider socket stalled and the process
was stopped. It is excluded from the result above; checkpoint/resume and a
30-second no-retry transport fallback were then added before the completed run.

## Decision

**Operational status: success. Performance-policy status: no promotion.** The
transport, JSON parsing, exact evidence check, checkpoint/resume behavior, and
cost ceilings all worked. The 81.1% evidence-validity rate confirms that
evidence generation needs separate ablation rather than being treated as a
solved detail.

The next experiment is not law RAG or BGE-M3. It will first isolate whether
joint-output interference causes v13's false positives: the same v13-focused
cohort will compare a joint-24 control against a v13-only output with no product
facts, no legal chunk, and otherwise matched notice context. If that does not
materially lower false positives, the following single-variable treatment will
add only the organizer CSV's exact product applicability fact.
