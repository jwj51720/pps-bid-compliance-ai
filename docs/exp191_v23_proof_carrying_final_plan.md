# EXP191 — v23 proof-carrying specialist final

## Evidence for a new response contract, not another wording tweak

EXP190 rejected a v23-only final whose system prompt merely listed the five
existing card gates.  All six eligible fast20 notices were labelled 1 (1 TP,
5 FP), including notices where the normal all-item final was 0.  The model's
ordinary V/E JSON gives no observable indication of which prerequisite it
actually used.  It can anchor on `지방계약법 + 협상에의한계약` and emit 1
without binding it to a qualifying date role, amount tier, or exception.

EXP191 changes that observable response contract for this one proven failure.
It does not add law text, thresholds, product facts, Python date arithmetic,
or label rules; it does not repeat EXP180's advisory date-navigation append.

## Candidate architecture

Base remains EXP179 source-first/full-source final. For only organizer-metadata
eligible local negotiated notices, an independent Gemma v23 final receives the
same v23 card, human-readable metadata, and complete exact-token source packs.
Its JSON must contain:

```json
{
  "지방협상_근거": "source substring or null",
  "공고일_근거": "source substring or null",
  "종료일_근거": "source substring or null",
  "종료일_역할": "현장설명회 | 제안서마감 | 없음",
  "긴급재공고_근거": "source substring or null",
  "판정": {"위반여부": 0, "근거문구": null}
}
```

All five proof fields are source observations, not Python-derived facts and not
the final legal result. The model owns `판정`. It must explicitly return
`종료일_역할=없음` if only price/electronic-bid/opening/evaluation/contract
dates occur. The existing `v23` card retains the only 10/20/40-day and
exception interpretation. Python resolves every non-null proof/evidence as an
unchanged source substring for audit, but never changes `판정` based on a
proof's presence, absence, or consistency.

The parsed model-owned `판정` replaces only v23/e23 as EXP190 did. Malformed
proof payload or final payload recovers to the normal EXP179 v23 field; an
empty or malformed proof therefore never becomes a deterministic 0.

## Controlled comparison

- Base: `configs/config.exp179-source-first-full-final-repeat-fast-panel-c4.yaml`.
- Allowed policy change: `staged_run.mode` only.
- Same cards, products, source-first inventory, full final sources, exact
  admission, normal final/merge, frozen v2/v3/v21, provider parameters, and
  eligible router as EXP190.
- One changed eligible-only call: the v23 specialist response schema and
  prompt output contract. This is not a new Python legal decision.

## Gates and decision rule

Before paid fast20: preflight; mock coverage for complete and malformed proof
payload; exact rendered input review for short, attachment, and overflow
eligible records; semantic-input contract audit for all 24 main-final items
plus v23 specialist; source-substring validity/count report; 49-column output.

Fast20 must improve v23 precision without losing its only TP and must not lower
macro F1 from EXP179 repeat. Otherwise stop: do not tune proof labels, examples,
or wording on individual dev rows. Only a directionally positive fast result
earns independent holdout20, then dev200. Runtime remains diagnostic-only.

## Fast20 result — rejected, with a narrower root cause

Executed 2026-09-11 after preflight, mock 20/20, and exact rendered-input/
semantic-contract audit. Isolated artifacts are under
`outputs/exp-191-v23-proof-specialist-fast-panel-c4/`.

| run | Macro positive-F1 | v23 TP / FP / FN | calls | elapsed |
| --- | ---: | ---: | ---: | ---: |
| EXP179 repeat base | 0.287500 | 1 / 3 / 0 | 40 | prior repeat |
| EXP191 | 0.216667 | 1 / 3 / 0 | 53 | 101.1 s |

No proof payload or final parse recovery occurred. The overall macro movement
also includes normal remote-call variance, and the v23 score itself is
unchanged, so this result does **not** support a holdout or dev200 expansion.

Unlike EXP190, the proof fields expose what happened. The model usually copied
the contract source, an announcement/date candidate, and a date role, but the
schema did not require it to expose the monetary tier, applicable 10/20/40-day
minimum, or calculated calendar interval. It still issued v23=1 when a
prerequisite was missing or comparison was wrong:

- PPS-DEV-062 (gold 0): source proof has 2026-02-20 and proposal date
  2026-03-11, yet it emits 1. The decision trace contains no amount-tier or
  day-count field by which the period comparison can be audited.
- PPS-DEV-191 (gold 0): `공고일_근거` is empty, yet it emits 1.
- PPS-DEV-169 (gold 0): `공고일_근거` is empty, yet it emits 1 from a proposal
  time alone.

Thus proof-carrying *source roles alone* is rejected. The next justified
design, if pursued, is not prompt wording: it must require model-visible
`적용 금액구간`, `적용 최소일수`, and `계산 일수` alongside the source roles,
while retaining model ownership of the label and forbidding Python arithmetic
or label override. That would be a new response-contract experiment and needs
its own plan/gates; do not mutate EXP191 after seeing these IDs.
