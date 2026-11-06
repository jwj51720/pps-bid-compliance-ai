# EXP-003: Estimated-Overflow Notice Context Split

## Scope

This is a fixed four-notice diagnostic, not a dev benchmark. The notices are
`PPS-DEV-123`, `PPS-DEV-11`, `PPS-DEV-143`, and `PPS-DEV-169`: the four notices
estimated in EXP-001 to exceed the 30,268-token prompt allowance after reserving
2,500 output tokens.

Three conditions use the paid fixed Gemma route, full metadata, the baseline
prompt, temperature 0, seed `20260826`, and a 2,500-token completion allowance:

1. Historical-style single pass with the 4,000-character document cap.
2. Single pass with no document cap. A sequence-limit failure is itself a
   recorded feasibility result, not a missing value to silently replace.
3. Split passes: 36,000 document characters per pass, with a 4,000-character
   공고문 anchor in every pass. Documents remain in official order; a document
   exceeding a pass's remaining space is continued in the next pass.

For split results, each item combines pass labels with OR: `00 -> 0`, `01 -> 1`,
`10 -> 1`, and `11 -> 1`. For `11`, retain the earliest-pass evidence; for a
single positive pass retain that pass's evidence. The checkpoint stores every
per-pass judgment in `pass_judgments` so the combinations can be audited.

The 36,000-character limit is only an experiment-time proxy because this machine
does not contain the supplied Gemma tokenizer. The run records actual OpenRouter
prompt-token usage. Before packaging, replace the proxy with exact
`runner.count_tokens()` admission and packing against the 30,268-token budget.

## Reproduction

```bash
.venv/bin/python scripts/run_experiment.py --config configs/config.exp003-overflow4-4000-paid.yaml --ids-file scripts/overflow_notice_ids.json
.venv/bin/python scripts/run_experiment.py --config configs/config.exp003-overflow4-full-paid.yaml --ids-file scripts/overflow_notice_ids.json
.venv/bin/python scripts/run_experiment.py --config configs/config.exp003-overflow4-split-paid.yaml --ids-file scripts/overflow_notice_ids.json
```

Compare `metrics.json`, `per_item_metrics.csv`, `errors.csv`, and the recorded
pass matrices in `predictions.jsonl`. Record each condition as it completes;
do not infer a failed or pending condition's score.

## Results

### Historical 4,000-character reference

The restored `exp-001-first-submission` checkpoint was reevaluated only on the
four fixed IDs. The generated artifact is
`outputs/exp-003-overflow4-4000-reference/`.

| Condition | Notices | Macro F1 | Gold positives | True positives | False positives | False negatives |
|---|---:|---:|---:|---:|---:|---:|
| Historical 4,000-character single pass | 4 | 0.00000 | 1 (`v8`) | 0 | 5 | 1 |

The false positives are `v3` (one), `v19` (one), `v21` (two), and `v24` (one).
The sole gold positive is `v8`, which the historical baseline predicts as zero.
Evidence validity is 0.8 across five predicted evidence-bearing positives.

### Three-condition comparison

| Condition | Macro F1 | TP / FP / FN / TN | Accuracy | Specificity | Evidence validity | Runtime | Total tokens | Reported cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Historical 4,000-character single pass | 0.00000 | 0 / 5 / 1 / 90 | 93.75% | 94.74% | 80.00% | historical checkpoint | not recomputed | not recomputed |
| Uncapped single pass | 0.00000 | 0 / 10 / 1 / 85 | 88.54% | 89.47% | 100.00% | 29.862s | 113,617 | $0.0067240 |
| Split passes + OR | 0.00000 | 0 / 12 / 1 / 83 | 86.46% | 87.37% | 91.67% | 82.351s | 157,049 | $0.0175526 |

All conditions miss the only gold positive, `PPS-DEV-11` / `v8`; therefore
positive precision, recall, and positive-class F1 are all zero in every row.
The high accuracy numbers are dominated by 95 negative labels and must not be
used as the selection metric.

### Actual token admission result

The earlier context-budget report extrapolated these four notices past the
30,268-token prompt allowance. The actual uncapped OpenRouter measurements
contradict that estimate for this prompt version:

| Notice | Uncapped prompt tokens | Completion tokens | Fits 32,768 with observed completion? |
|---|---:|---:|---|
| `PPS-DEV-123` | 22,774 | 684 | yes |
| `PPS-DEV-11` | 29,867 | 751 | yes |
| `PPS-DEV-143` | 29,099 | 663 | yes |
| `PPS-DEV-169` | 28,904 | 875 | yes |

Thus this four-notice set does not exercise a real sequence overflow. The
original estimate remains useful as a conservative screening tool, but it is
not an admission decision; final packing must use `runner.count_tokens()` with
the supplied evaluation tokenizer.

### Split pass audit

The 36,000-character proxy produces 3, 2, 3, and 3 passes respectively. Its
active per-item pass patterns are below; each digit is one pass in source order.

| Notice | Active item patterns |
|---|---|
| `PPS-DEV-123` | `v3=011`, `v21=010`, `v23=100` |
| `PPS-DEV-11` | `v3=11`, `v5=01`, `v13=01`, `v21=11`, `v24=11` |
| `PPS-DEV-143` | `v21=111` |
| `PPS-DEV-169` | `v3=001`, `v13=010`, `v19=110` |

The OR merger behaves as specified, but here it turns additional pass-level
false positives into final false positives. It adds 43,432 tokens, 52.489
seconds, and $0.0108286 relative to one uncapped pass without recovering `v8`.

## Conclusion

For these four notices, between the two full-context alternatives, select the
uncapped single pass whenever a tokenizer admits it. It is cheaper and yields
fewer false positives than the split+OR alternative, although neither improves
the leaderboard metric over the historical 4,000-character baseline because
both still miss the only positive. Do not conclude
that splitting is ineffective in a genuine overflow case: this sample was an
estimate false positive. A follow-up must choose notices that exact tokenizer
counting proves exceed the final prompt budget; only then compare full packing
against split+OR.

## Follow-up: exact-admission probe

The initial candidate selection scaled 4,000-character prompt tokens by raw
character count, and produced four false-positive overflow candidates. Do not
use a provider call or character proxy for the next cohort. Count the final
system/user messages with the fixed Gemma tokenizer and its native chat template
instead.

```bash
.venv/bin/python scripts/count_context_tokens.py \
  --output outputs/exp-003-token-counts/full_context.json
```

Select a genuine split experiment cohort only from notices whose measured final
prompt is above 30,268 tokens (the 32,768-token sequence limit less the fixed
2,500-token output reserve). On the evaluation server, the supplied
`PPS_MODEL_DIR` takes precedence so the supplied tokenizer files are used. In a
submission run, the final admission decision must call the already-initialized
vLLM runner's `count_tokens()` method (which uses
`self.llm.get_tokenizer()`), exactly as the organizer baseline does.

### Result: no dev overflow

`scripts/count_context_tokens.py` ran on all 200 dev notices with the official
`google/gemma-4-26B-A4B-it` tokenizer and native chat template. Every notice
fits the 30,268-token prompt budget. The largest is `PPS-DEV-11` at 29,866
tokens, leaving 402 tokens before the fixed 2,500-token output reserve. The
next largest notices are `PPS-DEV-197` (29,473), `PPS-DEV-143` (29,098),
`PPS-DEV-145` (28,981), and `PPS-DEV-169` (28,903).

The matching OpenRouter measurement for `PPS-DEV-11` is 29,867 prompt tokens;
the one-token difference is consistent with provider-side framing. This direct
tokenizer count supersedes the earlier character-scaled estimate as a local
preflight check. The submission-time source of truth remains
`runner.count_tokens()` from the vLLM runner initialized with `PPS_MODEL_DIR`.
Consequently, EXP-003 has no genuine dev overflow cohort on which to compare
split+OR. Retain the splitting code for test notices or later prompts that
submission-runner token counting proves do not fit.

The character-length probe runs were exploratory only. The 12-notice run
completed before this correction; the second 10-notice run was intentionally
stopped after five calls once direct tokenizer counting was adopted. Neither
probe is used to select an overflow cohort.

## Adaptive submission behavior

`overflow_split_enabled` now defaults to `true`. For every notice whose document
cap is unset, inference counts the final full system/user chat with the supplied
Gemma tokenizer. If it is at or below `max_model_len - output_reserve_tokens`,
the notice receives one full-context call; otherwise, documents are greedily
packed and counted again per pass. A document that cannot fit in the remaining
pass budget is split at the largest token-admitted prefix. In submission code,
inject the initialized vLLM runner's `count_tokens` callback; local experiments
use `PPS_MODEL_DIR`'s tokenizer as a preflight equivalent.

For pass labels, the final label is the logical OR in source order. Thus `000`
becomes 0 with blank evidence; `001` and `010` become 1 with the third or
second pass's evidence respectively; and `111` becomes 1 with the first pass's
evidence. More generally, when multiple passes are positive, retain the earliest
positive pass exactly, including a blank evidence value when that pass has none.
