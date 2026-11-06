# EXP136 — G02 decision-card isolation

## Hypothesis

EXP135 shows a reproducible output-scope gain for `v6`, `v7`, `v8`, `v9`, and
`v19`. Their organizer item names omit legally material distinctions: contract
type/amount and locality for v6–v8, actual requirement versus example/equivalent
product for v9, and pre-bid versus contract-stage timing for v19. The five
versioned `decision_cards_v6` entries state only these compact conditions from
organizer-provided references. No law text, retrieval context, thresholds
invented from labels, product index, rule, merge logic, document selection, or
decoding setting is added.

## Controlled difference

The base is EXP133. The sole effective change is
`prompt.decision_cards_path: data/derived/decision_cards_v6.json`. The shared
renderer must include cards only for the active items: G02 receives exactly the
five cited cards; G01 receives only its own 19 cards. This latter consequence
means the experiment evaluates the whole two-way policy, not an artificial
post-hoc splice.

## Rendered-input invalidation

This configuration was **not run remotely**. The first required rendered-input
review (`PPS-DEV-062`) found that root-level `decision_cards_path` injects all
active G01 cards as well as the five G02 cards. G01 grew from 3,378 to 5,680
tokens. That changes both the 19-item prompt and its context budget, so it
cannot answer the stated G02-only card question. The config is marked
`lifecycle: invalidated` and `load_config()` refuses to run it.

## Gates that would have been required

Before the paid fast-20 call, export and read G01/G02 actual messages for a
complete, an announcement-overflow, and an attachment-overflow notice. Verify
that cards are absent from the user message; that no law prose/reference,
internal status, or inactive item card leaks into either system message; and
that document context is otherwise byte-identical to EXP133. Then run
preflight, exact tokenizer admission, and grouped mock execution.

## Decision

Compare with EXP133, not historical card runs with different context/grouping.
Promote only if fast-20 macro and G02 mean F1 both do not decline, parsing is
clean, and the rendered prompt retains the stated scope. Otherwise reject the
card variant and preserve EXP135 as the output-scope result.
