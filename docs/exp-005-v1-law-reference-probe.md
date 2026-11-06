# EXP-005: V1 Fixed Official-Law Reference Probe

## Question

Can a complete official-law reference for v1 coexist safely with full notice
context and adaptive token splitting, and does it improve v1 on the full 200
notice dev set?

## Reference data and scope

Only organizer-supplied files were used. `scripts/build_v1_law_reference.py`
extracts complete article boundaries, without character or token truncation,
from `data/raw/open/data/법령패키지/법령/`:

- `국가를 당사자로 하는 계약에 관한 법률 시행령.txt`: 제12조, 제21조
- `지방자치단체를 당사자로 하는 계약에 관한 법률 시행령.txt`: 제13조, 제20조

Those four articles are the v1 mappings in the organizer item table. The
generated 16,620-character derived reference and its source-hash manifest are
ignored local data under `data/derived/`. This is a narrow ablation: it adds
only v1 reference text to the existing **joint 24-item** prompt, not a final
retrieval policy.

## Reproduction

```bash
.venv/bin/python scripts/build_v1_law_reference.py
.venv/bin/python scripts/count_context_tokens.py \
  --reference data/derived/law_reference_v1_v1.json \
  --output outputs/exp-005-v1-law-reference-probe/token_admission.json \
  --dump-inputs outputs/exp-005-v1-law-reference-probe/inputs.jsonl
.venv/bin/python scripts/run_experiment.py \
  --config configs/config.exp005-v1-law-reference-probe.yaml \
  --dump-inputs --fresh
```

`inputs.jsonl` preserves every final chat message sent to the model. It has one
row for each notice/pass, with `id`, `pass_index`, final tokenizer count, and
both system/user messages. The exact derived reference occurs in every system
message.

## Admission results

The direct Gemma chat-template tokenizer counted the complete final messages.
With a 32,768-token sequence length and 2,500-token output reserve, the prompt
budget is 30,268 tokens.

| Measure | Result |
|---|---:|
| Notices | 200 |
| Full-context fit | 179 |
| Full-context overflow | 21 |
| Scheduled passes | 225 |
| Maximum individual pass | 30,268 tokens |
| Reference present in all dumped passes | 225 / 225 |
| Scheduled prompt tokens | 3,686,886 |

The admission path therefore behaves as intended: references are not split or
removed; only notice documents are split, and each resulting pass receives the
same reference.

## Model result

| Metric | EXP-004 no-law full context | EXP-005 v1 fixed law | Delta |
|---|---:|---:|---:|
| Macro positive-class F1 | 0.213825 | 0.167873 | -0.045952 |
| v1 precision | 0.571429 | 0.571429 | 0.000000 |
| v1 recall | 0.571429 | 0.571429 | 0.000000 |
| v1 F1 | 0.571429 | 0.571429 | 0.000000 |
| v1 evidence span F1 | 0.980645 | 0.000000 | -0.980645 |
| Evidence validity | 0.832278 | 0.864407 | +0.032129 |
| Runtime | 441.862 s | 488.575 s | +46.713 s |
| Reported cost | $0.2904333 | $0.3668722 | +$0.0764389 |

The v1 confusion counts are identical (TP=4, FP=3, FN=3). Two negative
notices exchanged errors: `PPS-DEV-079` changed 0→1 and `PPS-DEV-101` changed
1→0. Thus the fixed v1-law text did not improve v1, while it degraded the joint
prompt's overall macro F1 and v1 evidence overlap.

## Decision

Do not promote this fixed four-article insertion to the canonical submission.
Keep the shared fixed-reference admission mechanism, but future Law RAG must
select a small number of complete, source-backed chunks by item, governing
contract law, and notice facts. A reference set that cannot fit with metadata
must be reduced by retrieval before prompting; document splitting cannot solve
fixed-context overflow.

## First-20 cost-control comparison

For subsequent inexpensive iteration, the fixed cohort is `PPS-DEV-01` through
`PPS-DEV-20`. The 4,000-character result is the corresponding subset from the
paid EXP-001 baseline checkpoint; full context is the existing 20-notice paid
run; the law result is a no-cost subset evaluation of this completed 200-notice
checkpoint. All use the same 20 IDs.

| Metric | 4,000 chars | Full context | Full + fixed v1 law |
|---|---:|---:|---:|
| Macro positive-class F1 | 0.090278 | 0.132143 | 0.125926 |
| Evidence validity | 0.774194 | 0.843750 | 0.777778 |
| Evidence span F1 | 0.219076 | 0.256876 | 0.293038 |
| v1 F1 | 1.000000 | 1.000000 | 1.000000 |
| v1 gold positives | 1 | 1 | 1 |

The fixed-law prompt does not improve the 20-notice macro score over full
context. The single v1 positive means its equal v1 F1 is not evidence of a law
benefit. Use this cohort for low-cost prompt mechanics and retrieval smoke
tests, but confirm an item-specific effectiveness claim on a cohort containing
enough positives for that item.

For a fresh low-cost rerun of the same law treatment, use
`configs/config.exp005-v1-law-reference-probe-first20.yaml`; its
`run.local_limit: 20` fixes this cohort without an `--limit` argument.
