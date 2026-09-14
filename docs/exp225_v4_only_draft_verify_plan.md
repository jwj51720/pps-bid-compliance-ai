# EXP225 — v4-only full-source draft and independent final verification

## Why this is not EXP186/187 repeated

EXP186/187 tested all 24 items in two or three complete-source stages and
degraded sharply. EXP225 does not retry that topology. It is restricted to the
one item for which an independent v4-only reader has already shown recall 1.0
on fast, holdout, and dev200 but excessive false positives. EXP222 showed that
putting more reasoning fields inside the same response does not bind Gemma's
logic. The remaining smallest test is whether a separate v4-only final reader,
after seeing an explicitly untrusted v4-only draft, rejects unsupported
positives while rereading the complete source itself.

## Contract

- base config:
  `configs/config.exp219-v4-only-scope-fast-panel-c4.yaml`
- candidate:
  `configs/config.exp225-v4-only-draft-verify-fast-panel-c4.yaml`
- allowed effective changes: the `staged_run` section and its
  `staged_run.mode` value only (the preflight reports both the section creation
  and the scalar mode);
- stage A reads corrected v4 card, all readable required metadata, organizer
  semantics, and every admitted original document, then emits only v4;
- stage B receives the same complete v4 inputs plus A's explicitly untrusted
  label (never A evidence), rereads the original source, and solely owns final
  v4/e4;
- Python does not vote, OR/AND, derive, or override either label. A malformed
  draft is omitted. Ordinary final parse/evidence handling remains unchanged;
- cards, profile, model parameters, source admission, merge target, and output
  semantics remain fixed.

This is a local quality diagnostic. It adds a second full-source call for the
specialist, but only one active item. Runtime promotion is considered only
after quality gates.

## Gates and sequence

Before the provider call, preflight must show only staged mode; exact tokenizer
profiling must show complete source in both stages; actual short, attachment,
and overflow messages must be read; active semantic contract and mock must
pass. Fast success requires v4 F1 or precision to improve over EXP219 while
retaining useful recall and zero non-v4 merge changes. Only then repeat unchanged
on holdout; only consistent holdout can advance to dev200.

Do not tune the draft wording, introduce a Python consistency rule, or extend
this to other items if fast fails.

## Fast20 result

- preflight reported only the declared staged-section creation and mode;
- exact dev200 topology projection: 200 draft + 200 final calls, with zero
  source omissions in either stage and 200/200 single-pass final messages;
- actual short, attachment, and largest final messages were read; each contains
  the corrected v4 card, metadata, complete source, explicitly untrusted draft,
  and subset-correct `지정 항목(v4)` re-review instruction;
- active semantic contract passed 1/1 on all three; mock passed; tests were
  212 passed;
- provider call: 40 stage calls over 20 notices, 40.4 seconds, parse error 0;
- EXP205 base `.325000`; EXP219 one-stage v4 specialist `.352778`; merged
  EXP225 `.356250`;
- v4 TP/FP/FN changed from EXP219 `3/3/0` to `3/2/0`, precision `.50 -> .60`,
  recall `1.0`, F1 `.666667 -> .750000`;
- changed non-v4 cells: 0; positive v4 evidence validity: 5/5.

The independent pass improves precision without losing recall, unlike the
same-response field schema. EXP226 repeats the exact policy on the frozen
holdout before any dev200 or selective-routing work.

## Independent holdout20 result and decision

- provider call: 40 stage calls over 20 notices, 41.2 seconds, parse error 0;
- EXP206 base `.208333`; EXP220 one-stage specialist and merged EXP226 both
  `.229167`;
- v4 TP/FP/FN remained `1/2/0`, precision `.333333`, recall `1.0`, F1 `.5`;
- changed non-v4 cells: 0; all three positive evidence strings were valid.

The verifier neither improves nor harms the independent holdout. Because the
fast precision gain is not directionally reproduced, the predeclared promotion
gate fails. Do not run the 400-call dev200 extension or build positive-only
routing from this result. Together with EXP186/187, the evidence says repeated
V-only reading is not yet a reliable general performance lever: the item-local
version can stabilize one cohort, but has no confirmed out-of-panel gain.
