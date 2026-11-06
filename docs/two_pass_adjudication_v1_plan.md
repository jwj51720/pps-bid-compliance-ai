# Two-pass adjudication v1 — prompt-review plan

## Status

This is a design and rendered-input review plan. It does not authorize a
provider call, change `config.yaml`, or create a submission candidate.

The 2026-09-07 organizer-format submission observation (about 34 minutes)
makes two whole-notice calls plausibly admissible within the two-hour limit.
Unlike item grouping or document splitting, this plan keeps a single 4,000
character notice context in both calls and changes only the reasoning
operation: the second call audits the first call's draft against the same
organizer input.

## Hypothesis

The exact organizer 4,000-character input already contains most observable
positive source evidence: the prompt-observability audit found 47 source-visible
positive cases, only 7 source-outside cases, and 10 positive absence cases
whose full-document scope is incomplete. Therefore the main unexplained error
is often applying an item boundary to visible information, rather than a lack
of raw-law or attachment context.

A second independent adjudication may reject a first-pass keyword-driven false
positive or recover a missed visible condition. This is not voting and must not
be implemented as a Python label rule.

## Fixed input contract

### Pass A — exact organizer control

- The current exact organizer `official_baseline_v1` system and user messages.
- All 24 V/E outputs; 4,000-character ordered context; `official_lines`
  metadata; no cards, product CSV, RAG, document split, or item grouping.
- The parsed A output is an untrusted draft, not evidence or a legal fact.

### Pass B — final independent adjudication

- Receives the exact same organizer system/user content as A.
- Receives a separately headed `1차 검토 초안` section after the actual notice.
  It contains only every item's A label and, for non-absence A positives, the
  unchanged A evidence substring.
- The section must state plainly that it is another reviewer's fallible draft;
  it cannot be used as a source quotation and must not be followed merely
  because it is present.
- B must reassess every one of the 24 items from actual metadata and notice
  text, then emit the ordinary V/E JSON schema. It is the sole final judgment.
- A non-absence B positive still needs an unchanged substring from the notice;
  B cannot cite the draft. The normal source-substring validator remains in
  force. Absence outputs stay null evidence as in the organizer contract.

The only transport fallback allowed is an unrecoverable B parsing failure:
record it and retain A for that record. This is failure recovery, not a
per-item merge or a quality policy.

## Explicitly excluded changes

- No raw-law, legal-summary, decision-card, product-CSV, precedent, or
  retrieval text.
- No item-specific reweighting, OR/AND/majority merge, or Python predicate.
- No full-context, adaptive split, document-level split, or v-item grouping.
- No decoding parameter, model, template, metadata renderer, evidence
  validation, or output schema change.

## Required preview gates

1. Build a preview-only config whose runner rejects non-mock calls.
2. Render A and B for a short complete notice, an overflow notice, and an
   attachment notice. Read the exact messages, including the draft separator.
3. Verify byte equality of A with the organizer control and verify that B's
   only additional model-visible material is the clearly untrusted draft plus
   the adjudication instruction.
4. Mock all 24-key parsing, a malformed A result (B without a draft), and a
   malformed B result (A recovery); validate evidence and CSV shape.
5. Use the actual Gemma tokenizer to measure B's extra draft tokens and
   project two-pass call count/runtime. The draft must fit without reducing the
   4,000-character notice context.
6. Only after all preview artifacts are reviewed, create a separate paid
   fast-panel config. It must declare `base_config`, `allowed_policy_changes`,
   and the complete two-pass operation in versioned config.

## 2026-09-07 preview result

All preview work was no-network. The implementation is shared-pipeline
`BaselinePipeline.predict_with_untrusted_label_review`; it has no per-item
Python merge. A malformed B response falls back to the whole A judgment only
as a transport recovery and records the source explicitly.

- Preview config: `configs/config.exp143-two-pass-adjudication-preview.yaml`
  has `lifecycle: preview`; `scripts/run_experiment.py` rejects it unless
  `--mock` is supplied.
- Rendered A/B input examples are under
  `outputs/exp-143-two-pass-adjudication-preview/prompt_review/` for
  `PPS-DEV-062` (short), `PPS-DEV-042` (overflow), and `PPS-DEV-049`
  (attachment). The draft labels use already-recorded EXP125A output only to
  make the dynamic section inspectable; no such historical result is used by a
  future run.
- For all three reviewed notices, B's system message and JSON schema equal A's
  exactly, and B's user message is A's complete user message followed by the
  two explicitly marked review sections. No card, product, law, evidence, or
  internal routing text is added.
- Exact Gemma chat-template counting over all dev-200 records: A prompt
  min/median/p95/max = 3,062/3,851/4,008/4,206 tokens; B =
  3,386/4,175/4,332/4,530. The fixed label-only draft adds 324 tokens and all
  200 B prompts fit the 14,848-token input budget without removing notice
  text.
- `python scripts/run_experiment.py --config ... --mock --fresh` completed
  20 two-pass rows. Every row records A, B, and `final_source`; CSV validation
  passed with no warnings. Focused pipeline/submission/config/inspection tests
  passed (63 tests).

These gates establish execution and input fidelity only. They do not establish
that the review improves labels. A new non-preview config and a fast-20 paid
comparison remain required.

## Fast and holdout result

The paid runs used the exact A/B operation above; their output directories
preserve both pass responses for every record.

| Cohort | A macro positive-F1 | B macro positive-F1 | Delta | A → B changed cells |
| --- | ---: | ---: | ---: | ---: |
| frozen fast-20, EXP144 | 0.15853 | 0.18168 | +0.02315 | 8 |
| independent holdout-20, EXP145 | 0.12500 | 0.16667 | +0.04167 | 9 |

On fast-20, B removed seven false positives and recovered one true positive.
On holdout, B removed six false positives, introduced two false positives, and
recovered one true positive. The principal repeated changes were product/Sme
boundary cases (`v13`, `v17`), but no item-specific prompt, rule, or merge was
added: this is a model-level adjudication result, not a targeted correction.

| Cohort | A non-absence evidence validity | B validity | A/B parse errors |
| --- | ---: | ---: | ---: |
| fast-20 | 0.854 (41) | 0.857 (35) | 0 / 0 |
| holdout-20 | 0.706 (34) | 0.710 (31) | 0 / 0 |

The planned independent-cohort gate is satisfied. The next allowed action is
one dev-200 confirmation using the identical A/B policy; no prompt, cards,
documents, metadata, decoder, or merge behavior may change before it.

## Promotion rule

Compare pass A and final B on the same frozen fast-20, then a label-blind
holdout-20. Report macro positive-F1 plus per-item TP/FP/FN and A-to-B changed
cells. B must improve both cohorts without a parse/evidence regression before
dev-200. A fast-panel improvement alone is not a submission policy.

## 2026-09-07 dev-200 confirmation: rejected

`EXP146` completed the identical two-pass policy over all dev-200 records.
The final B result was **0.21121** macro positive-F1 in 1,139.5 seconds.  Its
within-run A control was 0.21300, so B changed the score by **-0.00179**.
The fast/holdout gains therefore did not reproduce at dev-200 scale and this
policy is not a submission candidate.

| Measure | Pass A | Final B | B - A |
| --- | ---: | ---: | ---: |
| Macro positive-F1 | 0.21300 | 0.21121 | -0.00179 |
| TP | 49 | 46 | -3 |
| FP | 277 | 230 | -47 |
| FN | 104 | 107 | +3 |
| Changed cells | - | 90 | - |

B removed many false positives, especially for `v13` and `v17`, but its
additional false positives/false negatives harmed `v3`, `v14`, `v17`, and
`v24`. This is not a safe global calibration improvement. Final evidence
validity was 0.822 (276 positive cases); it must not be compared directly to
the earlier small cohorts without accounting for their different case counts.

There was also a material transport risk: `PPS-DEV-160` reached the provider's
8,192-token completion cap in both A and B, emitted malformed JSON in both
passes, and took 177.6 seconds. The stored whole-record fallback kept the
pipeline complete, but this is unacceptable as a reason to promote a doubled
full-dataset submission path. The output artifacts are
`outputs/exp-146-two-pass-adjudication-dev200/` (ignored local data).

The next experiment must not tune this adjudication wording item-by-item.
If a later verification loop is considered, it needs a new hypothesis and a
separate preview: bounded output behavior, a clearly defined subset or trigger,
and a comparison against the single-call control. V-item grouping is likewise
a separate multiplicative execution policy, not an add-on to EXP146.
