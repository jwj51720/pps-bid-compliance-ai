# EXP182 — procedure-ledger replacement plan

작성일: 2026-09-10 (dev / mac)

## Hypothesis

EXP171's quality signal may come from separating source reading from final legal judgment, rather
than from its exact seven broad category names. Replace—not append—the first-stage 7-category
inventory with a compact source-only procedure ledger that preserves related endpoint candidates.
The final still receives decision cards v6, friendly metadata/product facts, every exact-token
admitted original source pack, and one advisory navigation ledger before V/E.

This differs from EXP174 (four excerpts/category), EXP175 (navigation position), EXP176/177
(exception category), EXP180 (conditional additional timeline pass), and rejected EXP181 (an
additional all-notice procedure pass). It retains EXP171's two-stage topology and final source
coverage; it has no v grouping, labels, law RAG, card edit, Python label rule, or final 4k anchor.

## Replacement ledger contract

Stage 1 has seven procedure fields, max two unchanged source excerpts each:

`참가자격_관계`, `제품자격_관계`, `규격요구_관계`, `제출서류_관계`, `공동계약_관계`,
`일정참가_관계`, `공고메타_대조값`.

Each field maps to the relation requirements documented in EXP181's label-blind audit. The source
prompt forbids v labels, law judgment, metadata values, calculations, and paraphrases. If related
endpoints are separate, it permits at most two source-order excerpts. Python only validates each
excerpt against its current source pack, resolves doc id, deduplicates, and never derives a label.

## Gates before implementation or provider call

1. Exact Gemma tokenizer profile must show all source documents retained, no over-budget final
   message, and call topology no greater than EXP171's observed 435 dev200 calls plus a small
   admission-only variance.
2. The compact ledger's worst final-token burden must not exceed EXP171's current navigation
   upper bound; otherwise it is only a relabelled token increase.
3. Build a dedicated mode without changing generic cards/meta/product/full-source final policy.
   Its config names EXP179 as base and declares only `staged_run.mode`.
4. Mock source-only, malformed, duplicate, multi-pack, empty-ledger, evidence, and final recovery
   behavior; no navigation state may create a Python label.
5. Export/read short complete, attachment, and overflow stage/final inputs. Audit 24/24 final
   semantic input contract and exact source coverage.

Only then run one fast20 probe. Advance only on a clean all-item result above EXP179, then frozen
holdout20 and dev200. A failed fast20 ends this schema without field wording/limit tuning.

## Preflight record — 2026-09-10

The implementation is a replacement mode, `procedure_inventory_full_final_v1`. It uses the same
source packs as EXP171, but its first stage is source-only (system prompt plus the exact source
pack): it receives no cards, friendly metadata, product fact, labels, or final V/E task. The final
message retains cards v6, friendly metadata/product applicability, the complete original admitted
source pack, and the advisory procedure ledger. Empty or malformed ledger values are never a
Python 0 decision.

`scripts/preflight_experiment.py` reports exactly one controlled change relative to EXP179:
`staged_run.mode: fact_inventory_full_final_v1 -> procedure_inventory_full_final_v1`.

Exact Gemma-tokenizer profiling against EXP171's saved dev200 source packs was rerun with
`scripts/profile_exp181_procedure_feasibility.py`. The replacement topology has 216 source-ledger
calls and 216 final calls (432 total) with an empty ledger; its schema upper bound is 216 plus 227
final calls (443 total). Both profiles have zero source-document omissions. This is a tokenizer
admission estimate, not vLLM runtime evidence.

The fast-panel mock completed 20/20 records. It serializes the first stage under the explicit
`procedure`/`by_field` provenance key, rather than mislabeling it as a generic category inventory.
`pytest -q` passed 147 tests. The three label-blind semantic-input audits passed all v1--v24:

- `outputs/exp182-semantic-contract-audit-v1/PPS-DEV-062/` — short complete local-negotiated notice
- `outputs/exp182-semantic-contract-audit-v1/PPS-DEV-046/` — attachment notice
- `outputs/exp182-semantic-contract-audit-v1/PPS-DEV-082/` — overflow notice

`outputs/exp182-admission-audit-v1/final_admission.json` records dev200 final source coverage:
374 source documents, zero source omissions, zero metadata omissions, no missing active cards, and
no over-budget packs. The actual rendered inputs in the three audit directories were read: the
first-stage messages are source-only and the final messages preserve all four required input
components. The next permitted action is one paid fast20 probe; no holdout or dev200 provider run
is authorized by this preflight itself.
