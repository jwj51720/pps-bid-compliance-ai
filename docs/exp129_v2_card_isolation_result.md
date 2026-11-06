# EXP129 — v2 card and output-scope diagnostic result

Plan: [EXP129 plan](exp129_v2_card_isolation_plan.md)  
Configs: `config.exp129a-v2-item-table-probe.yaml`,
`config.exp129b-v2-card-v6-probe.yaml`,
`config.exp129c-full-organizer-v2-probe.yaml`  
Ignored raw artifacts: `outputs/exp-129{a,b,c}-*/`

## Input and implementation checks

All three inputs were generated from the shared pipeline and read before any
provider call:

| Case | Exact review files (one per arm) | Finding |
|---|---|---|
| Short complete notice | `outputs/prompt-audit-config.exp129{a,b,c}-*/pps-dev-02.messages.md` | v2 source restriction is visible |
| Announcement overflow | `.../pps-dev-042.messages.md` | the supplied announcement ends with `[절단]` |
| Visible high-value restriction | `.../pps-dev-053.messages.md` | 1억원 실적 참가자격 is visible |
| Attachment overflow fixture | `.../pps-dev-01.messages.md` | `[미수록 문서] 과업지시서 1건, 제안요청서 1건` is visible |

For each of those four IDs, the actual `messages[1].content` SHA-256 was
identical across all three request JSON files. EXP129A/B each requested only
`v2`; their system-prompt diff was exactly the one v2 card block. EXP129C had
the unchanged organizer 24-item system prompt and 24-key schema. No arm used
laws, product CSV context, retrieval, merge logic, or post-processing.

`preflight_experiment.py` accepted the declared diffs, both subset arms and
the full arm completed mock execution, and Gemma `apply_chat_template`
admission put every cohort record in one pass. The largest prompt was 3,328
tokens in EXP129A, 3,458 in EXP129B, and 3,960 in EXP129C, below the 14,848
prompt budget.

## v2 results

The frozen 14-notice cohort includes every one of the seven dev v2 positives
and seven hash-selected negatives. It is intentionally diagnostic, not an
independent ranking cohort; the 24-item macro F1 is not meaningful for the
subset arms because inactive outputs are zero placeholders.

| Arm | Requested outputs | TP / FP / FN | Precision | Recall | v2 F1 | Parse errors | Mean completion tokens |
|---|---:|---:|---:|---:|---:|---:|---:|
| EXP129C | v1–v24, exact organizer | 2 / 1 / 5 | .667 | .286 | .400 | 1 | 1,324 |
| EXP129A | v2 only, item table | 7 / 3 / 0 | .700 | 1.000 | **.824** | 0 | 45 |
| EXP129B | v2 only, v6 card | 5 / 1 / 2 | .833 | .714 | .769 | 0 | 50 |

EXP129A recovered the five source-visible v2 positives that EXP129C missed:
`PPS-DEV-02`, `-03`, `-042`, `-069`, and `-078`. It retained EXP129C's v2 FP
on `-051` and added FPs on `-066` and `-083`. Thus output-scope reduction
helps recall here but does not by itself solve the v2 semantic boundary.

The v6 card correctly suppressed the `-066` and `-083` FPs, but also changed
true positives `-042` and `-062` to 0. Its clause that treats unconfirmed
amount/contract-type/exception applicability as 0 is therefore too
conservative for this diagnostic. **Do not promote v6's v2 text, edit it from
these labels, or run its wording variants.**

## Response-contract observation

EXP129C's `PPS-DEV-160` provider response ran for 106.7 seconds, reported
8,192 completion tokens despite the request's `max_tokens: 1536`, then became
malformed JSON by emitting an unbounded repeated newline evidence string. The
shared parser recorded one parse error and safely produced that pass's zeros;
the run otherwise completed 14/14 in 119.8 seconds. This negative notice does
not account for the five v2 false negatives, but it is a material remote
provider reliability observation. Treat remote full V/E output length as a
runtime and malformed-output risk; do not infer offline vLLM behavior from
this single OpenRouter violation without a dedicated adapter/runtime check.

## Decision

The useful result is not a submission candidate. It is evidence that the
exact 24-item V/E response contract can materially suppress source-visible
item recall, while a one-item call reduces both output length and malformed
JSON risk. The next structural experiment may test a small, fixed semantic
partition using the organizer renderer and no card/RAG change. It must first
measure calls/runtime and inspect exact per-group messages. It may not simply
promote one-item calls or multiply into 24 calls.
