# INC-084 — Luna full-notice teacher calibration

## Question

Can a stronger external teacher turn the organizer-provided documents and a
concise item-level legal core into materially better self-labels than the
historical Gemma submission control? This is a teacher-quality measurement,
not a submission result: the final runtime must still use the fixed Gemma
model and must inspect the actual notice.

## Fixed design

- Population: every one of the 200 organizer-provided dev notices.
- Input: all source documents in prescribed order, all notice metadata, item
  table, and `decision_cards_v6.json` (concise legal applicability/condition
  cores). No dev label is included in any prompt.
- Teacher: native OpenAI `gpt-5.6-luna`, strict 24-field JSON schema,
  `max_output_tokens=2048`, concurrency 4.
- Comparator: archived EXP109 one-pass Gemma control, the only known
  local/public-aligned submission control (dev macro F1 0.223498; public
  0.210360).

The first five-request smoke test at 768 output tokens showed reasoning-token
exhaustion and malformed/incomplete useful answers. It was discarded rather
than patched. At 2048 tokens, retrying the one transient failure produced
200/200 schema-valid answers.

## Result

| System | Dev macro positive-F1 | Scope |
| --- | ---: | --- |
| EXP109 Gemma control | 0.223498 | historical submission-shaped control |
| Gemini 2.5 Flash + legal core | 0.225958 | earlier independent teacher check |
| Luna + legal core | **0.328732** | full dev-200 teacher calibration |

Luna improves 11 labels, leaves 8 unchanged, and degrades 5. Largest gains are
`v21` (+0.790), `v20` (+0.500), `v22` (+0.429), `v3` (+0.364), and `v2`
(+0.314). Its central benefit is substantially lower false-positive activation
on several restriction items: EXP109-only positives contain 20 gold positives
but 199 gold negatives, whereas Luna-only positives contain 27 gold positives
and 57 gold negatives. This is a diagnostic comparison, **not** a licensed
dev-tuned ensemble rule.

The full item table and exact disagreement counts are in
`runs/inc084_openai_luna_full_dev_card/comparison_exp109_per_item.csv` and
`comparison_exp109_summary.json`. The request/response/checkpoint artifacts
make the run auditable and resumable.

## What this establishes and what it does not

1. Concise, condition-oriented legal cores are decisively preferable to the
   prior full official-law ledger in this setting. The latter reached only
   0.176677 on its interrupted 91-notice completion and triggered provider
   budget errors; it is not a path to scale.
2. A viable high-quality external self-label teacher now exists. It is still
   not enough evidence to label all 20,000 notices or choose a final retrieval
   topology. The dev set is small and the apparent gain can be distributional.
3. The remaining hard labels are not solved by generic extra context: `v6`,
   `v7`, `v10`–`v12`, `v14`, `v16`, and `v18` remain at zero F1. These need
   explicit condition/fact extraction and/or a distinct case-retrieval route,
   not threshold tweaks.

## Next experiment, selected before bulk labelling

Run a separate *fact-ledger then adjudicate* teacher topology on a predeclared,
stratified 64-notice dev slice. Stage A must emit, for every item, a compact
source-grounded statement of the observed fact required by the legal core (or
`no applicable fact found`); Stage B receives only that ledger plus the same
legal core and returns the 24 decisions. It will be compared with the direct
Luna result on exactly the same 64 notices. The question is architectural:
whether externalizing the relevant fact protects the weak/absence items and
creates a reusable, retrieveable case record. It is not a search over
character/token cutoffs and no post-hoc label-specific merge will be selected.

Only if that topology either improves broadly or yields clearly auditable case
records without large degradation will we label the fixed 256-notice unlabeled
pilot and assess retrieval against dev. Bulk 20,000 self-labelling follows only
after that gate.
