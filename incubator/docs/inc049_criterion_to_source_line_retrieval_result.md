# INC-049: Criterion-to-Source-Line Retrieval Result

## Valid execution

The source universe was all 93,748 nonempty dev source lines.  The evaluation
set was the 54 positive item/notice pairs for which organizers supplied a
nonempty evidence string.  Every source line and every criterion/metadata
query was embedded with `BAAI/bge-m3`; reported usage was 4,640,033 tokens and
$0.04640033.  All 200 notice checkpoints completed with no transport failure.

An initial 512-input transport request stalled after three batches before any
rank was calculated.  It was stopped and rerun from a clean result state using
the preregistered amended 128-input transport setting and per-notice
checkpoints.  This changes neither source text, query text, labels, nor a
retrieval rank.

## Retrieval result

| Query representation | MRR | Recall@1 | Recall@5 | Recall@10 | Recall@20 | Median rank | P90 rank |
|---|---:|---:|---:|---:|---:|---:|---:|
| Lexical criterion reference | 0.08045 | 3.7% | 9.3% | 20.4% | 27.8% | 53 | 197 |
| BGE criterion | 0.10802 | 3.7% | 18.5% | 27.8% | 40.7% | 33 | 221 |
| BGE criterion + notice metadata | **0.12710** | **5.6%** | 16.7% | **35.2%** | **40.7%** | **31** | 222 |

The BGE representation improved MRR by 0.04665 over the lexical reference,
and metadata moved the median evidence rank from 53 to 31.  That is a real
retrieval signal, but it is not a safe evidence-selection signal: only 22 of
54 eligible grounds appeared in the top 20.  Two provided evidence strings
were not contained in any single source line (`v1` one case and `v23` one
case), a structural limitation consistent with evidence crossing source-line
layout; neither was silently split or manufactured.

The apparent strong individual cases are too sparse to promote: v13 and v19
each have one eligible pair, while v3 (8 pairs) reaches 62.5% Recall@20 and
v7 (7 pairs) 42.9%.  No broad family reaches the prerequisite preservation
rate.  This is therefore not evidence for a per-item retrieval cutoff.

## Decision

**Reject as a candidate-gating or context-replacement policy.**  The protocol
required BGE metadata MRR above lexical *and* at least 90% Recall@20.  The
first condition passed; the second failed by 49.3 percentage points.  A final
judge may not be deprived of the full notice based on these ranks, and a
missing retrieved source line may never imply a negative label.

This does not refute the narrower engineering use of BGE after an LLM produces
a notice-specific fact query.  It does establish a necessary constraint for
that future idea: the fact ledger must be tested as a retrieval-query quality
improvement against this frozen baseline, and all final decisions must retain
full-document access.  It is not justified to spend on that extra Gemma stage
until a different broad branch identifies a plausible scoring bottleneck.

## Reproduction

```bash
python incubator/src/inc049_criterion_to_source_line_retrieval_audit.py --mode preflight
python incubator/src/inc049_criterion_to_source_line_retrieval_audit.py --mode run --workers 8
```

Artifacts: `incubator/runs/inc049_criterion_to_source_line_retrieval_audit/`.
