# EXP180 — v23 timeline navigation 유료 전 검토

작성일: 2026-09-10 (dev / mac)

## 가설과 비교 계약

가설은 `일정_설명회`의 최대 3개 broad excerpt가 공고일·설명회·제안서 마감의 **역할**을
보존하지 못할 수 있다는 것이다. EXP180은 지방계약법 + 협상에의한계약 notice에서만
source-only stage-1b를 한 번 더 호출해 다섯 날짜 역할의 unchanged source substring을
수집한다. 날짜 계산·최소일수·법률판단·v23/다른 v의 label/evidence 확정은 stage-1b와
Python이 하지 않는다.

final은 EXP179와 같은 card v6, friendly metadata, product fact, all admitted original source,
V/E schema, merge, evidence resolver, frozen EXP123 postprocess를 유지한다. navigation의
빈 값이나 malformed output은 final 0이 아니다.

- base: `configs/config.exp179-source-first-full-final-repeat-fast-panel-c4.yaml`
- candidate: `configs/config.exp180-v23-timeline-navigation-fast-panel-c4.yaml`
- declared allowed difference: `staged_run.mode` only
- preflight result: PASS; effective difference is exactly
  `fact_inventory_full_final_v1 → fact_inventory_full_final_timeline_v23`.

## Label-blind representability evidence

`scripts/audit_source_first_relation_capacity.py` read EXP171's stage-1 raw inventory responses
and organizer metadata only; it read neither dev labels nor final judgments. Output:
`outputs/exp181-source-first-relation-capacity-audit/relation_capacity.json`.

All 200 notices / 216 source packs had a valid inventory. In the local-negotiated v23 slice,
41 notices were applicable and 38 (92.68%) had at least one `일정_설명회` source pack at the
three-excerpt cap. This proves capacity pressure, not a missing fact, violation, or expected F1
gain. It justifies this single item-scoped relation probe; it does not justify an all-item ledger.

## Input and contract review

The following exact rendered messages were exported and read:

- short local-negotiated notice: `outputs/exp180-semantic-contract-audit-v1/PPS-DEV-062/rendered_inputs/pps-dev-062.final.messages.md`
- attachment notice: `outputs/exp180-semantic-contract-audit-v1/PPS-DEV-046/rendered_inputs/pps-dev-046.final.messages.md`
- attachment/overflow notice: `outputs/exp180-semantic-contract-audit-v1/PPS-DEV-082/rendered_inputs/pps-dev-082.final.messages.md`

For the eligible short notice, the stage-1b message contains only the role-extraction system
contract and `[공고 자료 원문]`; it contains no metadata, card, law, product, label, or final
judgment instruction. Its final message retains all 24 cards, friendly applicability facts,
complete source, broad navigation, and the explicit timeline navigation disclaimer. The
non-eligible attachment/overflow notices receive no stage-1b or timeline navigation, leaving
their final task otherwise identical to EXP179.

`scripts/audit_candidate_semantic_contract.py` returned 24/24 PASS for all three review records.
The stage-1b is therefore supplementary and does not replace any final semantic-input condition.

## Mock and exact-token capacity gate

`python scripts/run_experiment.py --config configs/config.exp180-v23-timeline-navigation-fast-panel-c4.yaml --mock --fresh --dump-inputs --dump-inputs-markdown` completed 20/20.

- CSV validation: PASS; malformed/final recovery: 0.
- stage-1b topology: 6 eligible fast20 notices, 8 timeline calls (including overflow), timeline parse errors 0.
- `scripts/audit_complete_fact_admission.py`: dev200 374 supplied source documents, source omission 0, metadata omission 0, active cards missing 0, over-budget pack 0.
- `scripts/profile_exp180_timeline_admission.py` used the exact Gemma chat template, saved EXP171 generic navigation, and no labels/provider calls. With 41/200 eligible notices, it measured 216 generic stage calls + 53 timeline stage calls + 219 final calls = 488 total calls with empty timeline navigation. The conservative schema upper (five roles × two synthetic 360-character excerpts) makes 226 final calls / 495 total, still source omission 0.

This is a bounded whole-notice extra pass, not document × v-group multiplication. It has no
evaluator vLLM throughput proof; remote wall time will not be used as such proof.

## Paid fast20 gate and analysis plan

The next run is the versioned fast20 config above, with no other code/config/card/prompt change.
Record macro positive F1, v23 TP/FP/FN/F1, all-item changed-cell ledger versus EXP179, source
coverage, parser/recovery, evidence validity, stage/final/timeline call counts, and runtime.

Advance only if v23 improves over EXP179 with no non-v23 global damage and operational gates stay
clean. Then use an unchanged policy on independent holdout20; only a same-direction holdout result
can justify dev200. A fast-only gain cannot alter the submission candidate.
