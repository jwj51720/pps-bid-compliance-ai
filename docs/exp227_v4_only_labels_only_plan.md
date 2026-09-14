# EXP227 — v4-only label-only diagnostic

## New question

EXP210/EXP187 showed that asking for all 24 labels without evidence harms
quality. They do not answer whether a single difficult item benefits when the
model can spend its response entirely on one binary decision. EXP219 already
established a complete-input v4-only V/E specialist with recall 1.0 across
fast, holdout, and dev200, but low precision. EXP227 isolates only the response
burden: same v4 card, readable metadata, organizer semantics, all admitted
source documents, and model parameters; output only `{v4: 0|1}`.

## Controlled policy

- base: `configs/config.exp219-v4-only-scope-fast-panel-c4.yaml`;
- candidate: `configs/config.exp227-v4-only-labels-only-fast-panel-c4.yaml`;
- allowed change: `prompt.output_mode` only;
- active item remains v4 and profile remains `complete_fact_subset_v1`;
- cards, prompt mode, metadata/product policy, source admission, overflow merge,
  model/provider settings, and Python postprocess remain fixed;
- this is label-quality-only. It is not submission-ready and intentionally has
  no e4. Python does not infer evidence from phrases or alter v4.

If label-only improves v4 F1 consistently, a separate successor may ask an
independent Gemma locator for source text only on model-positive records, with
Python restricted to exact substring validation. That evidence architecture is
not part of EXP227.

## Gates and sequence

Preflight must report only output mode. Exact tokenizer admission, complete
source audit, short/attachment/largest rendered review, active semantic
contract, schema/parser mock, and tests must pass. Fast compares v4 TP/FP/FN
directly with EXP219. Only improved v4 F1 without recall collapse advances
unchanged to holdout, and only consistent holdout advances to dev200.

Do not interpret blank evidence validity as a failure of the declared label
diagnostic, but do not package or promote it as a submission policy either.

## Fast20 result and decision

- preflight found only `prompt.output_mode`;
- exact fast and dev200 admission retained all inputs, with 20/20 and 200/200
  one-pass topologies and 374/374 dev documents;
- rendered short/attachment/largest messages and active semantic contracts
  passed; mock passed; tests were 212 passed;
- provider call: 20 calls, 20.3 seconds, every completion exactly 8 tokens,
  parse error 0;
- v4-only label result was exactly identical to EXP219 V/E: predicted-positive
  IDs and TP/FP/FN were `3/3/0`, precision `.5`, recall `1.0`, F1 `.666667`.

The hypothesis is rejected. Removing evidence output greatly reduces completion
tokens but does not change v4 label calibration. Since EXP219 already produces
valid evidence for five of the same six positives, adding a separate locator
would add cost without a label gain. Do not advance to holdout/dev200 or infer
that item-local V-only generally improves quality.
