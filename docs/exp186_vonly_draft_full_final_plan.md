# EXP186 — complete-source V-only draft, full-source V/E verifier

작성일: 2026-09-10 (dev / mac)

## Why this is a new test

Two related branches are already closed, but neither is this contract:

- EXP125 changed a 4,000-character organizer baseline from V/E to a single final V-only response;
  it fell from `.171958` to `.137500` and could not produce submission evidence.
- EXP144–146 used a 4,000-character V/E draft followed by a V/E adjudicator. It showed small-panel
  gains but fell from `.21300` to `.21121` on dev200 and doubled a non-complete-source topology.

EXP186 instead gives **both** calls card v6, friendly required metadata, exact product applicability,
and every exact-token admitted original source pack. Pass A returns only all-24 labels, making a
cheap, explicitly untrusted reading draft. Pass B receives the same complete final input plus the
24 draft labels, re-reads the actual source, and is the only owner of final V/E and evidence. No
draft evidence is transported, no label is Python-merged, and an A parse failure means B receives
no draft rather than a Python-imputed label.

This deliberately replaces—not adds to—EXP171's factual inventory stage. Its topology is therefore
approximately the direct full-source two-call count, not a three-stage multiplication. It tests the
user-visible hypothesis that forcing one full read to make only V decisions can improve the final
verifier's legal V/E reasoning while retaining required evidence in B.

## Fixed input and output contract

Pass A: full complete-fact source context, exact adaptive pack admission, all v1--v24, output schema
`{v1: 0|1, ..., v24: 0|1}`. It has no evidence output and cannot be submitted.

Pass B: same card/meta/product/full-source input for each admitted final pack, plus a clearly headed
untrusted 24-label draft after the actual source. It must independently emit ordinary V/E JSON for
all 24 items. Its non-absence evidence must be an unchanged substring from its own source pack;
absence evidence remains blank. B is the only final judgment. Python only parses, validates source
substrings, and performs the existing pass merge.

An A parse failure or missing/invalid draft removes the advisory draft from B; it does not select
any label. A B parse failure uses the ordinary full-source V/E transport recovery, never an A label.

## Explicit exclusions

There is no multi-V-only vote, majority/OR/AND rule, v grouping, document×group multiplication,
RAG, card change, metadata change, evidence-first selector, source reduction, or decoding change.
Multiple independent V-only drafts would add a third whole-source read and require a model-owned
resolution pass, exceeding this candidate's bounded topology; it is not part of EXP186.

## Required gates before a provider call

1. A config names the matching direct full-source EXP172 policy as base and permits only the staged
   execution mode. It must be invalid if cards/products/full-source overflow admission are absent.
2. Exact tokenizer profiling on dev200 records A source contexts and B draft-bearing final contexts,
   including empty and 24-label draft conditions. It reports source omissions, final pack count, and
   batch-64 topology against EXP171's observed 435 calls.
3. Mock all-item V-only parse, malformed A without draft, overflow packs, malformed B recovery,
   evidence substring validation, 49-column CSV, and output serialization.
4. Export/read actual short complete, attachment, and overflow A/B messages. B must pass the 24-item
   semantic-input contract and preserve all document types; A must show only complete factual input
   plus the V-only output contract.
5. A fast20 result must improve over the matching EXP169 direct full-source control and not regress
   parser/evidence behavior before an unchanged frozen holdout20. Promotion to dev200 requires the
   same direction on holdout. A failure closes this topology without draft wording or voting variants.

## Preflight record — 2026-09-10

`scripts/preflight_experiment.py` reports exactly one controlled difference from EXP169:
`staged_run.mode: <unset> -> vonly_draft_full_final_v1`. The implementation keeps the V-only draft
and V/E final in the shared pipeline. It serializes both exact message packs, records whether a
draft was available, and has no Python label merge. On malformed A, B has no advisory draft; on
malformed B, the recovery is one ordinary complete-source V/E call.

The fast-panel mock completed 20/20 and explicitly verified stage provenance. The full test suite
passed 148 tests, including the V-only-draft final-owner test and the untrusted-draft evidence
contract test. The rendered stage A output contract is exactly 24 integers; B's draft is headed as
non-source material and says that evidence must come from the actual complete source.

`scripts/profile_exp186_vonly_admission.py` performed exact Gemma tokenizer admission over dev200:
215 draft calls plus 216 final calls, or 431 total; batch size 64 requires four draft and four final
rounds. Draft prompt tokens total 3,170,914 (p50 12,795; max 30,268), and B prompt tokens total
3,268,593 (p50 13,203; max 30,268). Both stages have zero source-document omissions. This is a
call/token topology result, not vLLM throughput evidence.

The label-blind semantic contract audit passed all 24 items on the actual rendered short,
attachment, and overflow fixtures:

- `outputs/exp186-semantic-contract-audit-v1/PPS-DEV-062/`
- `outputs/exp186-semantic-contract-audit-v1/PPS-DEV-046/`
- `outputs/exp186-semantic-contract-audit-v1/PPS-DEV-082/`

The dev200 final base admission artifact records 374 source documents, zero source or metadata
omissions, no missing active card, and no over-budget final pack at
`outputs/exp186-admission-audit-v1/final_admission.json`. The next permitted action is one paid
fast20 probe only; cards, source admission, merge, provider parameters, and output schema remain
fixed.
