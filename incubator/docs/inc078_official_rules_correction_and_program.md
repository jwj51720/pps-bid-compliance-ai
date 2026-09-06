# INC-078: Official-rule correction and high-leverage research program

## Correction

INC-077 is superseded.  It incorrectly treated the absence of a narrow
source-fact predicate and a missing local submission tokenizer as a reason to
close broad improvement paths.  The official rules instead permit all of the
following within the fixed-final-model boundary:

- arbitrary local development and use of all 20,000 organizer unlabeled
  notices;
- external-LLM self-labeling when its inputs are competition-provided material;
- static RAG assets generated from that material;
- multiple Gemma calls per final notice, subject to the two-hour run limit and
  the requirement that each notice has at least one successful actual-notice
  Gemma call.

The rules still prohibit trained classifiers, fine-tuning, and external
non-competition content.  Predictions for a test notice must be independent of
other test notices.  These are the actual boundaries of this program.

The public score is Macro F1 of the 24 labels.  Evidence is evaluated only in a
second-stage qualitative review for the leading submissions.  Label inference
and evidence resolution must therefore be separate stages: evidence may improve
after label policy is fixed, but an evidence-string gate must not silently
downgrade a label prediction.

## Evidence base and calibration anchor

| Source | Local dev | Public leaderboard | Interpretation |
|---|---:|---:|---|
| EXP-109 official baseline, 4,000-char ordered document prefix, one joint V/E call | 0.22350 | 0.21036 | The only currently known dev-to-public calibration pair; retain as a control. |
| EXP-014 full split + cards/product context | 0.22802 | 0.18350 | A small dev gain did not generalize and consumed 96m50s. Do not make split/evidence-gated architecture the default. |
| EXP-120 4,000-char single pass + card v6 | 0.24893 | not submitted | A cheap local candidate (337s), not evidence of public gain. It must be a separate control arm. |
| INC-041 (incubator-only) | 0.26750 | not submitted | Exploratory evidence only, not a claim of public improvement. |

`dist/pps-artifacts_20260904_mac.tar.xz` now contains the original EXP-014 and
EXP-109 submission zips, their staged source, configurations, and full-dev
artifacts.  Audit confirms the EXP-109 zip uses fixed Gemma vLLM with batch 128,
16,384 maximum sequence length, 1,536 output tokens, and no derived assets.
The archive also supplies EXP-110--120 local results; they are historical
evidence, not independent public validation.

## New hypothesis tree

### H0 — reliable online control

Reconstruct two submission-parity *label-first* direct Gemma controls: EXP-109
(the public-calibrated envelope) and EXP-120 (the best known cheap local
single-pass variant).  Neither is expected to win on its local score alone;
together they provide a public-calibrated fall-back, a local comparator, and a
runtime budget for added calls.

### H1 — offline case knowledge from the 20,000 notices

Use an external teacher to create an auditable structured decision record for
unlabeled notices: 24 labels, a short item-specific decision rationale, and
source offsets/snippets where applicable.  The teacher sees only the notice,
metadata, and supplied official law.  The static record is not a learned model.

Build lexical + BGE-M3 retrieval over those records, retaining both positive and
negative cases.  At final inference, retrieve cases using only the current test
notice, then supply concise retrieved case facts alongside the complete current
notice to Gemma.  This differs fundamentally from INC-055: it does not transfer
a dev label from generic boilerplate; it gives Gemma independently produced,
item-specific precedents from the permitted 20,000-record corpus.

### H2 — multi-call reasoning, not brittle Python thresholds

Use the fast direct label pass and one independent case-augmented/legal reviewer
pass.  A final Gemma adjudicator may see the complete current notice plus the
two structured opinions and decide disagreements.  This is permitted and avoids
choosing a character cutoff or a dev-derived per-item threshold.  Calls are
scheduled within an explicit 2-hour budget; only disagreement/uncertainty cases
need the third call.

### H3 — evidence as a post-label service

After label decisions are fixed, resolve evidence only for positive
non-absence items from the current source documents, using exact substring
validation and a fallback blank when no valid quote is found.  This keeps the
leaderboard objective from being damaged by output/evidence transport failures
while preserving a path to second-stage evidence quality.

## Experiment sequence and decision gates

1. **Corpus inventory (INC-079):** produce a deterministic 20,000-notice
   structure/metadata/document-family inventory.  It chooses representative
   teacher strata without labels or handcrafted character thresholds.
2. **Teacher calibration (INC-080):** select a fixed, diverse unlabeled pilot
   from those strata.  Create records with two prompt topologies (direct legal
   decision report versus extract-then-decision report), validate schema/source
   provenance, and measure cost, latency, label sparsity, and inter-run
   agreement.  No dev-label tuning occurs in this step.
3. **Case-RAG ablation (INC-081):** hold the online label prompt fixed and
   compare direct control, lexical cases, BGE cases, and hybrid cases on dev.
   Retrieval corpus is unlabeled self-label output only.  Report all 24 F1s,
   prediction prevalence, and runtime.  A method advances only if it improves
   macro F1 without a concentrated collapse and has a credible 1,853-notice
   runtime projection.
4. **Adjudication ablation (INC-082):** run only on cases where H0/H1 disagree;
   compare a predeclared final Gemma adjudicator with each constituent pass.
   The decision rule is model adjudication, not a dev-selected count/length
   cutoff.  Confirm the selected topology on a frozen dev partition, then once
   on full dev.
5. **Scale-up:** if an H1/H2 topology passes, label progressively larger,
   stratified portions of 20,000 (pilot -> 2k -> 10k -> 20k), with immutable
   manifests and a cost ceiling per stage.  Scale is a corpus-coverage variable,
   not a new prompt search.  Re-run the fixed dev ablation after each scale.
6. **Submission parity:** package static records/indexes and the exact online
   pipeline, then use the public EXP-109 control and the candidate as separate
   reproducible submissions.  Do not infer a public gain from dev alone.

## What is deliberately not carried forward

- No character-count cutoff (including 165 or 12,000) is a decision policy.
- No rule is promoted merely because it improves one exploratory cohort.
- No evidence requirement is used as a label veto.
- No dev label is put into a retrieval corpus for test inference.
- No unavailable local tokenizer or organizer clarification is treated as a
  prerequisite for the permitted self-label/RAG program.

## Sources

- Official rules: <https://dacon.io/competitions/official/236754/overview/rules>
- Official evaluation: <https://dacon.io/competitions/official/236754/overview/evaluation>
- Official data specification: <https://dacon.io/competitions/official/236754/talkboard/417195>
