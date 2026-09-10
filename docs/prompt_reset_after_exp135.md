# EXP135 public result 이후 prompt reset

작성일: 2026-09-09 (dev / mac)

## Trigger

`pps_20260907_174343.zip` (EXP135 two-way v-item partition)은 local dev-200
macro positive-F1 `0.24694`였으나 public `0.2200692374`, runtime `93분 28초`를
기록했다. Runtime은 2시간 제한 안이므로 실패 원인은 처리량이 아니라 quality
generalization이다.

EXP135가 same-template public single-call control보다 낮았다는 직접 증거는 아직
없다. 그런 public control을 제출하지 않았기 때문이다. 다만 frozen fast-20,
independent holdout-20, dev-200의 세 local gain만으로 이 output partition을
canonical policy로 올릴 수 없다는 증거는 충분하다. Root `config.yaml`은 다시
exact organizer-format single-call V/E control로 돌린다. EXP135는
`configs/config.exp135-two-way-g02-dev200.yaml`과 제출 zip으로 재현 가능한
historical result로 보존한다.

## What is closed

- raw law/article bundle, law routing, or law-summary RAG injection
- full-document split × v-item grouping and broad OR/AND merge
- global second adjudication (EXP146 dev-200 non-improvement plus malformed
  runaway)
- dev labels를 보고 v별 숫자·키워드·Python correction을 계속 누적하는 방식
- full card set, V-only, generic source-first wording, generic precedent RAG
- EXP135 G01/G02 membership 또는 group-local wording을 dev label에 맞춰 조정하는
  follow-up

The negative result does not prove that every multi-call design is wrong. It
does mean that any future multi-call design needs a new source-complete,
label-blind semantic hypothesis and cannot be justified by EXP135's local
scores.

## P0 — exact prompt and semantic-input audit (offline only)

This reset does not start with a paid prompt rewrite. It first establishes
what the current control actually says and what each judgment requires.

### Current control

- one organizer-ordered 4,000-character context
- all 24 v items in one V/E JSON response
- human-readable organizer metadata lines
- no cards, product CSV text, law text, RAG, split, grouping, or Python label
  correction
- offline vLLM submission and OpenRouter experiments share this pipeline;
  only provider/scheduling/evaluation differ.

Actual shared-pipeline messages were exported without a model call under
ignored `outputs/prompt-reset-p0/`:

| Fixture | Purpose | Review finding |
| --- | --- | --- |
| `pps-dev-062.messages.md` | short complete notice | no truncation/omission marker |
| `pps-dev-042.messages.md` | long announcement | `[절단]` marker present |
| `pps-dev-01.messages.md` | attachments plus overflow | announcement truncation and omitted 과업지시서/제안요청서 markers present |

The messages establish that the current baseline does not falsely claim to
have read omitted documents. They do **not** establish that item requirements
are semantically complete.

### Required audit matrix

Use `docs/semantic_input_contract_v1.md` and organizer sources only. For each
of v1–v24, record:

1. which current rendered system/user span supplies its item description;
2. which applicability facts, 1-condition, material 0-condition/exception,
   source document type, and metadata/CSV facts are absent from that control;
3. whether the absence is structural (the necessary source cannot fit the
   one-context policy) or semantic (the source is present but the instruction
   is merely an item name/note);
4. whether the missing information can be represented as a compact,
   organizer-proven condition without creating a new threshold or dev-derived
   rule.

This audit must not use dev labels/evidence to choose a target v or change a
condition. It is a source/provenance inventory. A complete matrix is a gate,
not evidence that adding the missing prose improves F1.

### P0 result (completed offline)

`scripts/audit_semantic_input_matrix.py` now generates the checked matrix and
exact fixtures under `outputs/semantic-input-matrix-v1/`; its procedure and
human-review conclusion are recorded in
`docs/semantic_input_matrix_v1_plan.md`. It verified all 24 item rows and
ledger provenance entries. For the exact 4,000-character control, all 200
dev notices render an announcement, while every present 규격서 (56),
과업지시서 (53), and 제안요청서 (56) is omitted behind that announcement.
The prompt has no item-specific 1/0 condition or friendly exact
competition-product CSV fact. This closes the inventory, not the prompt
branch: any candidate must now name one coherent missing information class
and rerun the same audit against its own config.

## Why this is the next step

The exact organizer prompt supplies mostly item names and brief notes. The
semantic contract shows many items need a contract profile, amount band,
actual-qualification distinction, whole-notice absence scope, counterpart
metadata field, or explicit exception. Conversely, earlier full decision-card
prompts lowered quality; simply pasting all conditions is not a solution.

P0 therefore separates two questions that prior experiments conflated:

- Does the current message lack a fact needed to *state the task*?
- Or does it contain the relevant notice/metadata fact but Gemma still apply
  the boundary poorly?

Only the first can justify a compact prompt-information treatment. The second
requires a different hypothesis; it is not solved by more law text, longer
context, or a stronger generic persona.

## Data-availability correction

The repository has 200 labeled dev notices and only a **10-notice public
sample** at `data/raw/open/data/test.jsonl.gz`. The 1,853 evaluation notices
are not locally available. Do not claim a dev-vs-test distribution audit or
use that 10-row sample as a representative public distribution.

## Entry gate for the next paid run

No paid run is authorized until all conditions hold:

1. P0's 24-item source/span matrix is complete and reviewed.
2. A one-sentence hypothesis changes exactly one prompt-information component
   from the exact single-call control; it does not change context, schema,
   cards, decoder, grouping, or merge at the same time.
3. A versioned config declares `base_config` and `allowed_policy_changes`.
4. Exact rendered messages for short, truncation, and attachment fixtures are
   exported/read; source coverage, tokenizer admission, mock, and isolated
   output paths pass.
5. Fast-panel results remain selection-only. Any apparent gain must reproduce
   on an independent cohort and dev-200 before a submission decision.

## Near-term continuation

Complete the matrix first. Then choose at most one compact information class
that is missing across a semantically coherent set of items, or close the
prompt-content branch if no such class exists. Do not begin by changing
temperature, output mode, document length, cards, or v grouping again.
