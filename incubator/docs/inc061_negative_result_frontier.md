# INC-061: Negative-Result Frontier and Remaining Hypotheses

## Verified baseline and gap

INC-041 is the best reproducible dev-200 composition at 0.26750 Macro F1.
The requested 0.50 target requires +0.23250; none of the tested global
architectures has produced a repeat-safe positive delta.

## Hard constraints learned

- Full ordered source documents are necessary; fixed character truncation and
  document splitting lose coverage or create speculative OR errors.
- Law RAG is a precision signal but is too insensitive for simple AND/OR or
  verifier merge.
- BGE source ranking cannot gate or replace source reading (40.7% Recall@20).
- A full-notice legal/factual Gemma memo improves BGE ranks on average but not
  monotonically; its long rank tail and a paired regression reject it as a
  source-candidate or label gate (INC-064).
- Generic unlabeled-neighbor/self-label transfer has no template basis.
- Nested schema is transport-unsafe; flat schemas are transport-safe.
- Flat labels without evidence lose decision signal; forcing all-item line IDs
  yields many positive-without-evidence semantic-contract failures.
- Equal global consensus over three grounded runs lowers Macro F1 below the
  mean raw run and can lose source-valid evidence.
- An unconditional all-item source-line locator has valid schema transport but
  vacuous semantic output (960/960 `-1`), so an evidence-first attention
  topology cannot precede a decision (INC-066).
- Gemma-4's documented thinking trigger has no observable effect through this
  OpenRouter strict-JSON route, so it cannot be treated as a controlled legal
  decision variable (INC-067).
- The only proven automatic rules are v2/v3/v21, each linked to organizer law
  and complete source facts.  Broader source cues have failed coverage gates.
- An all-item necessary-observability map finds no untested high-loss item that
  can support a new broad law-to-fact program; only already-proven v2/v3 and
  near-saturated v22 pass (INC-065).

## Explicitly closed hypotheses

Do not repeat: generic prompt wording, output family decomposition, global
extract-then-adjudicate, product fact cards, generic case RAG, full-notice
label-only output, direct all-item evidence-ID output, simple law-RAG AND/OR,
or role-cue expansion for v4/v7.

## Remaining hypotheses worth distinct evaluation

1. **Bounded per-positive evidence location:** retain a grounded joint primary
   judgment, then make a separate source-location call only for its positives.
   This is evidence transport research, not expected label gain; it may permit
   a reliable final policy only if it preserves labels and finds source IDs.
2. **Official-law program discovery beyond lexical facts:** requires a complete
   manual law-unit/exception representation, then an all-positive/hard-negative
   source observability audit.  It is the only remaining path to deterministic
   label gains, but must not be rushed from dev error wording.
3. **Reasoning topology with auditable intermediate states:** any new LLM
   approach must isolate one cognitive variable beyond already rejected global
   extraction, retain complete context, use flat transport where applicable,
   and have two repeat arms before dev-200 spend.

No claim that 0.50 is currently attainable is warranted.  Further spend should
advance one of these three hypotheses or stop; it should not generate another
near-duplicate prompt comparison.
