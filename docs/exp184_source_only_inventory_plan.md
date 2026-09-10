# EXP184 — strict source-only broad inventory

작성일: 2026-09-10 (dev / mac)

## Hypothesis

EXP171/179의 1차 system contract는 공고 원문만 읽어 7개 category의 변경 없는 사실 후보를
수집한다고 명시한다. 그러나 현재 shared pipeline의 `fact_inventory_full_final_v1` 구현은
`build_messages()`를 사용해 1차 user message에 friendly 나라장터 metadata를 함께 넣는다.
그 metadata는 1차 output의 허용 입력이 아니며, 실제 출처 substring도 아니다. 같은 7-category
schema와 excerpt cap을 유지하고 1차를 `system + exact admitted source pack`으로 제한하면,
원문 탐색이라는 역할을 명확히 하고 입력 토큰/주의 분산을 줄이면서 final의 완결 입력은 그대로
보존할 수 있다.

This is not EXP180's item-specific timeline addition, EXP182's replacement ledger, a card/metadata
edit, a new fact schema, grouping, RAG, or a Python rule. It changes only the stage-1 message
builder. Stage 2 remains exactly the complete-fact full-source V/E policy: cards v6, the needed
friendly metadata, product applicability fact, advisory navigation, and all tokenizer-admitted
original source packs.

## Contract and failure semantics

Stage 1 uses `build_source_only_fact_messages(build_fact_inventory_system_prompt(...), source)`.
It receives no card, metadata, product context, label, law text, or final output contract. Its JSON
schema, max three excerpts per category, source substring validation, doc-id resolution,
deduplication, and malformed-to-empty advisory behavior stay identical to EXP179. An empty or
malformed inventory never produces a Python label.

Final message construction, V/E schema, exact tokenizer packing, source coverage, evidence
validation, merge, cards, product lookup, provider parameters, and frozen postprocess do not
change.

## Required gates

1. Config declares EXP179 as base with only `staged_run.mode` allowed.
2. Exact tokenizer profile records stage/final pack count and source omission; it must not exceed
   EXP171 topology and must report the per-stage token reduction separately from final admission.
3. Mock source-only, malformed, duplicate, multi-pack, empty-ledger, final-recovery, CSV/evidence
   paths. Assert the serialized 1st stage contains no metadata heading or product/card text.
4. Export and read the actual short complete, attachment, and overflow stage/final messages;
   audit all 24 semantic input contracts in final messages and full source coverage.
5. Run one fast20 only after the gates. Advance unchanged to frozen holdout20 only if the all-item
   result improves over EXP179 without worsened parser/evidence behavior. A failed fast20 ends this
   message-builder variant without wording or cap tuning.

## Preflight record — 2026-09-10

`scripts/preflight_experiment.py` reports exactly one controlled difference:
`staged_run.mode: fact_inventory_full_final_v1 -> fact_inventory_full_final_source_only_v1`.
The fast-panel mock completed 20/20. Its serialized 1st-stage messages all have exactly a system
message and `[공고 자료 원문]` user message; no `[나라장터 입력 메타]`, product section, or card text
appears in any stage-1 pack.

Exact Gemma chat-template profiling across the dev200 tokenizer-admitted 216 source packs found
`2,395,152 -> 2,329,063` stage-1 input tokens: 66,089 fewer total, or 306.0 fewer per pack
(11,088.7 -> 10,782.7 mean; max 26,570 -> 26,302). This is an input-token measurement, not an
evaluator vLLM runtime claim. `outputs/exp184-admission-audit-v1/final_admission.json` records
374 source documents, zero document/metadata omissions, no missing card, and no over-budget final
pack.

The label-blind 24-v semantic-input audit passed for all reviewed exact messages:

- `outputs/exp184-semantic-contract-audit-v1/PPS-DEV-062/` — short complete
- `outputs/exp184-semantic-contract-audit-v1/PPS-DEV-046/` — attachment
- `outputs/exp184-semantic-contract-audit-v1/PPS-DEV-082/` — overflow

The source-stage messages in these artifacts were read alongside the final messages: the former
contain exact source only, while the latter retain cards, friendly metadata/product fact, advisory
inventory, and complete admitted original source. The next permitted action is one fast20 provider
probe; no card/schema/merge/provider change accompanies it.

## Result and decision — 2026-09-10

`outputs/exp-184-source-only-inventory-fast-panel-c4/` completed 20/20 at macro positive-F1
`0.283333`, below EXP179's exact repeat `0.287500` (`-0.004167`). Both runs have 23 stage-1 and
24 final calls (47 total). EXP184 had no stage parse error but one final-recovery event
(`PPS-DEV-051`); the recovery completed with no persisted final parse error. CSV validation passed
with two invalid-positive-evidence warnings, the same count as EXP182 but fewer than EXP179's
three. Remote elapsed time (`149.954s`) and provider token totals are not evaluator runtime proof.

Relative to EXP179, EXP184 gains v22 one TP and removes v9 two FPs and v24 one FP, but loses v1
one TP, v4 one TP, and v23 one TP; it also introduces two v13 FPs and one v15 FP. The changed-cell
ledger is preserved in the experiment `predictions.jsonl` and `errors.csv`. The small aggregate
drop and recovery mean this cannot be treated as a quality improvement despite the strict input
contract and 66,089-token first-stage reduction.

**Decision: reject EXP184.** Do not run its holdout or dev200 extension, and do not tune the
source-only instruction, category cap, navigation location, cards, or merge. The submitted EXP171
artifact remains immutable; for continued experiments, the metadata-bearing broad inventory is the
empirical incumbent rather than silently replacing it with this stricter message builder.
