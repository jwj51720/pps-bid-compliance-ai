# EXP190 — v23 specialist final owner

## Why this is the next probe

EXP172 merge diagnostic establishes that direct complete-source failure is not
caused by overflow merge: 186/200 notices are one-pack and 175/186 FP/FN cells
are already wrong there.  v23 is the clearest relation failure (1 TP, 25 FP,
4 FN on dev200).  Its false positives commonly cite price-bid or electronic
bid dates, although the v23 card requires a *local negotiated-contract*
applicability gate, amount tier, and an announcement-to-site-briefing or
proposal-deadline relation.

EXP180 tested a non-final date-role navigation pass.  It was source-valid but
lost on fast20 (`0.241667` vs EXP179 repeat `0.287500`): its one fast-panel v23
TP became 0 and generic final labels also changed.  Therefore EXP190 does not
retry a date navigation append, and does not claim that adding more excerpts
fixes the judgment.

## Hypothesis

For notices whose organizer metadata says both `적용계약법=지방계약법` and
`낙찰방법=협상에의한계약`, an independently rendered **v23-only V/E final
owner** can apply the existing v23 card more reliably when its prompt requires
an explicit sequence of source-grounded gates.  The normal EXP179 full-source
V/E final still owns v1--v22 and v24.  The v23 specialist, also Gemma and also
given complete original source plus the same human-readable metadata/card,
owns only v23/e23.  Python merely replaces that output field after parsing;
it makes no legal decision and no label rule.

The specialist prompt restates only existing card conditions:

1. confirm local negotiated-contract applicability;
2. identify the source announcement date and only a qualifying site-briefing
   or proposal-submission deadline;
3. identify the provided amount tier and card minimum period;
4. test urgent/re-notice exception from source;
5. emit 1 only if all required facts and the calendar comparison are explicit.

It expressly says that price-bid, electronic-bid, opening, evaluation, or
contract dates are not qualifying endpoints by themselves.  This is a
prompt-level ordering of v23 card's existing 0-condition, not a new threshold
or Python date rule.

## Frozen comparison contract

- Base config: `configs/config.exp179-source-first-full-final-repeat-fast-panel-c4.yaml`.
- Allowed policy change: `staged_run.mode` only.
- Retained exactly: cards v6; competition product facts; source-first category
  inventory; all final source documents; tokenizer packing; V/E evidence
  resolver; non-v23 merge; frozen EXP123 v2/v3/v21 replacements; model and
  provider parameters.
- Changed only: eligible notices receive one extra v23-only complete-source
  model final and that model output is the final v23/e23.  Ineligible notices
  receive no specialist call and retain the base v23 result.

This is not v-item grouping and does not multiply each source pack by every
item.  It is a single, evidence-proven item probe.  It is not submission-safe
unless later quality and runtime gates pass.

## Required pre-paid gates

1. Preflight must report only `staged_run.mode` effective policy change.
2. Export/read exact specialist and normal-final prompts for a short complete
   notice, a tokenizer overflow notice, and an eligible local-negotiated
   notice.  Verify no raw metadata JSON, law text, or case RAG appears.
3. Run the semantic-input contract audit for all 24 final items; additionally
   trace the specialist's v23 applicability, 1-condition, 0-condition,
   human-readable metadata facts, and original-source span.
4. Exact tokenizer admission must preserve all documents in both normal final
   and v23 specialist contexts.  Mock must cover eligible/ineligible routing,
   malformed specialist output recovery to base v23, evidence substring
   validation, and unchanged non-v23 fields.
5. Output must preserve 49 CSV columns and source-only evidence validation.

## Quality gate

Run only `configs/dev_fast_panel_v1.json` first.  Require no parse/recovery
error, no source omission, and an improved or at least non-worse v23
TP/FP/FN *without* all-item macro damage relative to EXP179 repeat.  Only a
directionally positive fast result earns the independent holdout20 run; only
fast+holdout agreement earns dev200.  A failure ends this branch: no prompt
wording tuned to individual dev IDs or labels.

## Fast20 result — rejected

Executed 2026-09-10 with the exact config above after preflight, mock, and
semantic-contract/rendered-message review. The isolated output is
`outputs/exp-190-v23-specialist-final-fast-panel-c4/`.

| run | Macro positive-F1 | v23 TP / FP / FN | calls | elapsed |
| --- | ---: | ---: | ---: | ---: |
| EXP179 repeat base | 0.287500 | 1 / 3 / 0 | 40 | prior repeat |
| EXP190 | 0.232738 | 1 / 5 / 0 | 53 | 174.5 s |

The 53 observed calls are 23 source-inventory packs, 24 normal-final packs,
and six eligible v23-specialist packs. There were no final or specialist parse
recoveries. The exact base/candidate full-row difference also includes ordinary
provider variance, so it is not evidence that the v23 field alone caused every
macro change. But the treatment's own audit is decisive: all six eligible
notices received specialist `v23=1`; only PPS-DEV-141 was gold positive. The
other five were false positives. The normal final in the same run had v23=0
for four of those five false positives, so the specialist created the over-call
rather than repairing it.

This rejects a v23-only V/E owner with checklist wording. It shows that an
explicit sequence in a prose system prompt is not a sufficient control: Gemma
anchors on the local-negotiated applicability fact and does not reliably carry
the date-role/amount/exception gates through to its JSON decision. Do not run
holdout or dev200 and do not promote this mode. Any successor must change the
*observable intermediate contract*, not merely restate the same gates in a
newer v23 prompt.
