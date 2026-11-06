# Prompt Probe v3

## Purpose and limits

This is a fixed five-notice diagnostic cohort for isolating prompt and
document-context policy changes. It is not a fast-panel replacement and no
setting may become a submission/default policy from this document alone.
Every apparent improvement must be rerun on `dev_fast_panel_v1`, then dev-200.

The fixed cohort is [`configs/dev_prompt_probe_v3.json`](../configs/dev_prompt_probe_v3.json):
`PPS-DEV-04`, `PPS-DEV-13`, `PPS-DEV-15`, `PPS-DEV-29`, and `PPS-DEV-060`.
It was selected without model predictions, using only organizer dev labels,
document shape/length, contract-law metadata, and organizer CSV lookup status.
It includes national/local, multi/single-document, matched/not-matched product
lookup, v10/v11 absence detection, and v24 comparison examples.

All tests use the same Gemma model, temperature 0, seed, provider, VE response
contract, and unchanged-source evidence request. A non-absence positive always
requests an original document substring; this is an invariant, not an ablation.

## Prompt sequence

| Config | Single controlled difference from parent | Result status |
|---|---|---|
| EXP076 P0 | Organizer-style 4,000-char baseline | Anchor |
| EXP077 P1 | `plain` -> `markdown_v2` only | Structure |
| EXP078 P2 | minimal item list -> item-table official references | Item explanation |
| EXP079 P3 | decision cards v2 on | 1/0 conditions |
| EXP080 P4 | official 21-line metadata -> complete metadata JSON | Metadata rendering |
| EXP081 P5 | concise Korean competition-product lookup text on | CSV context |

`preflight_experiment.py` verified the declared one-field differences for
EXP077--EXP081. A first P5 call was invalidated before comparison because the
new official-profile branch did not render its product context. The renderer was
fixed, tests and mock input inspection passed, and P5 was rerun. Only the rerun
is reported below.

## Document sequence

| Config | Context policy | Interpretation |
|---|---|---|
| EXP076 D1 | 4,000-char one call | Baseline document policy |
| EXP082 D2 | complete documents, one call, exact-token admission | Over-budget notices are excluded and written to `admission.json`, never truncated or zero-filled |
| EXP083 D3 | document-level exact-token split/merge, strict evidence, absence AND | Full coverage policy |
| EXP084 | EXP083 with absence AND -> OR only | Absence merge diagnostic |

The strict evidence gate and per-pass absence AND are recorded as linked
correctness changes in EXP083's config: they are not silently inherited.

## 2026-09-03 first-run results

| Experiment | Notices | Calls | Macro F1 | Prompt / completion tokens | Runtime |
|---|---:|---:|---:|---:|---:|
| EXP076 P0 | 5 | 5 | 0.04167 | 19,516 / 4,331 | 41.0s |
| EXP077 P1 | 5 | 5 | 0.04167 | 20,355 / 4,431 | 38.9s |
| EXP078 P2 | 5 | 5 | 0.04167 | 30,455 / 4,338 | 37.7s |
| EXP079 P3 | 5 | 5 | 0.04167 | 43,890 / 3,428 | 41.2s |
| EXP080 P4 | 5 | 5 | 0.04167 | 44,206 / 3,936 | 51.1s |
| EXP081 P5 (rerun) | 5 | 5 | 0.04167 | 45,365 / 3,752 | 38.6s |
| EXP082 D2 | 3 admitted / 5 selected | 3 | 0.00000 | 18,456 / 2,160 | 24.9s |
| EXP083 D3 AND | 5 | 11 | 0.04167 | 81,778 / 8,043 | 65.3s |
| EXP084 D3 OR | 5 | 11 | 0.04167 | 81,778 / 8,351 | 70.8s |

All runs had zero parse-error passes and evidence validity 1.0. EXP082 admitted
only `PPS-DEV-13`, `PPS-DEV-29`, and `PPS-DEV-060`; `PPS-DEV-04` required
20,354 prompt tokens and `PPS-DEV-15` required 19,583, exceeding the 14,848
prompt-token budget. Its score is therefore conditional on three records and
must not be compared as an equal-denominator winner.

### What can and cannot be concluded

- No component has shown a macro-F1 improvement in this five-notice first pass.
  The added official references and cards more than doubled prompt tokens with
  no observed score gain here.
- This is **not proof of no effect**. The cohort is deliberately tiny and the
  remote provider showed label-level variation even at temperature 0. For
  example, EXP084 changed `PPS-DEV-04/v4` despite OR/AND being logically
  irrelevant to v4; that change is transport/model variation, not a merge-rule
  effect.
- Do not promote or discard cards, Markdown, full metadata, product context, or
  an absence merge policy based on these scores. The next valid action is a
  paired rerun of the reference and only a candidate with a directional,
  item-level signal; otherwise stop this screening and use the fixed fast20.
- Full split covered all five notices but required 11 calls versus five for
  D1, and about 4.2x prompt tokens. It has no quality evidence here to justify
  a runtime-risk promotion.

Exact inputs for manual inspection are preserved in the ignored outputs for
EXP076, EXP077, EXP081 (rerun), EXP082, and EXP083 as `input_examples.md`.

## 2026-09-03: presence/absence two-group probe

The first probe did not identify an input-information winner. EXP085/EXP086
therefore test a smaller hypothesis: a model should not have to apply the
opposite presence and absence truth conditions in one response.

Both configurations use the same default Markdown v2 prompt, complete metadata
JSON, 4,000-character one-call document context, no cards, no CSV lookup, and
the same model settings.

| Experiment | Calls | Macro F1 | Prompt / completion tokens | Result |
|---|---:|---:|---:|---|
| EXP085 control | 5 | 0.04167 | 28,027 / 3,081 | One response for v1--v24 |
| EXP086 two groups | 10 | 0.11111 | 45,716 / 3,247 | `G01_presence_items` (19) + `G02_absence_items` (v10, v11, v16, v18, v20) |

No parse errors occurred. The two group outputs are concatenated by their
disjoint v keys; no cross-group OR/AND merge is applied.

The meaningful changes were:

- `PPS-DEV-13/v10`: FN -> TP. This is the desired absence-detection signal.
- `PPS-DEV-15/v12`: FN -> TP. Although v12 is in the presence group, it likely
  benefits from a shorter item list and removal of the five opposite-condition
  items.
- `PPS-DEV-29/v16`: FP -> TN.
- New errors: `PPS-DEV-13/v11` FP and `PPS-DEV-060/v12` FP.

This is a directional result only. The five-record cohort has one v10 and one
v11 positive, so EXP086 is a fast20 rerun candidate, not a canonical policy.
Its roughly 1.63x prompt-token cost and exactly 2x call count must be assessed
against quality and submission runtime before promotion.

## 2026-09-03: dedicated v24 call

EXP087 ran the full three-group policy (`presence`, `absence`, `v24`) from
scratch. Its aggregate score fell to 0.04167, but unchanged v10/v12 outputs
also changed on that remote rerun. It is therefore a valid end-to-end sample,
but not a causal estimate of the v24 call.

EXP088 is the causal overlay: it reuses EXP086's exact presence/absence group
responses and performs only five new `v24` calls. Thus the only final field
that could change was v24.

| Experiment | New calls | Macro F1 | v24 TP / FP / FN | Finding |
|---|---:|---:|---:|---|
| EXP086 two groups | 10 | 0.11111 | 0 / 0 / 1 | Reference |
| EXP088 v24 overlay | 5 additional | 0.11111 | 0 / 0 / 1 | No v24 prediction changed |

The dedicated v24 calls consumed 19,448 prompt and 175 completion tokens. The
only v24-positive notice, `PPS-DEV-29`, remained 0. Do not add a third v24 call
to a submission candidate on this evidence; the next possible v24 experiment
must change the comparison instruction itself, not merely isolate the key.

## 2026-09-03: two-group labels-only output

EXP089 changes only `prompt.output_mode` from EXP086's VE contract to
`labels_only`; the same two item groups, document policy, metadata, model, and
group concatenation remain in place.

| Experiment | Macro F1 | Prompt / completion tokens | Summed call latency |
|---|---:|---:|---:|
| EXP086 two-group VE | 0.11111 | 45,716 / 3,247 | 77.9s |
| EXP089 two-group v-only | 0.04167 | 47,624 / 1,185 | 68.3s |

v-only reduced completion tokens by 63.5%, but lost the two useful changes from
EXP086: `PPS-DEV-13/v10` reverted TP -> FN and `PPS-DEV-15/v12` reverted TP ->
FN. It also removed several false positives. The net macro-F1 decrease means
that the evidence-generation contract is currently a useful reasoning scaffold,
not merely output overhead. Keep VE for the two-group fast20 candidate; do not
promote v-only on this probe.
