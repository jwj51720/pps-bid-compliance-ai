# EXP181 — notice procedure model feasibility plan

작성일: 2026-09-10 (dev / mac)

## 출발점

EXP171의 7개 source fact category는 final full-source V/E에 유일하게 일관된 구조적 개선을
주었다. 하지만 category는 raw excerpt 배열이고 role·같은 조항·대응 필드쌍을 보존하지
않는다. EXP181은 그것을 all-v label schema로 바꾸려는 계획이 아니다. 먼저 **공고의 절차와
사실 관계**가 source-only로 보존될 때 final이 full original source를 더 잘 재대조할 수
있는지를 검증하는 feasibility branch다.

EXP180의 v23 timeline role navigation은 fast20 `.241667`으로 EXP179 `.287500`보다 낮았고,
holdout/dev200 gate에서 종료됐다. 따라서 EXP181은 날짜 role을 늘리거나, EXP180의 prompt를
수정하거나, v23를 Python으로 보정하지 않는다.

## Label-blind evidence and limit

`outputs/exp181-source-first-relation-capacity-audit/relation_capacity.json`은 EXP171's raw
stage-1 response와 organizer metadata만 읽었다. labels/final judgment는 읽지 않았다.

| relation requirement | current broad category | eligible notices with that category at cap |
| --- | --- | ---: |
| v3 performance amount ↔ same-object reference amount | 참가자격_실적_지역 + 금액_메타대조 | 183 / 200 (91.50%) any cap |
| v8 same qualification clause: performance ↔ region | 참가자격_실적_지역 | 12 / 29 (41.38%) |
| v9 maker/model ↔ equivalent/special-need qualifier | 규격_모델_기술요구 | 113 / 200 (56.50%) |
| v19 undertaking ↔ pre-bid/pre-proposal timing/purpose | 제출서류_확약서 | 180 / 200 (90.00%) |
| v21 each-member share ↔ joint method/member role | 계약방식_공동계약 | 25 / 41 (60.98%) |
| v22 briefing attendance ↔ eligibility consequence | 일정_설명회 | 74 / 85 (87.06%) |
| v23 notice date ↔ briefing/proposal role | 일정_설명회 | 38 / 41 (92.68%) |
| v24 notice field ↔ metadata counterpart | 금액_메타대조 | 177 / 200 (88.50%) |

A cap hit proves only that a stage pack had no fourth excerpt slot. It does not prove omitted
facts, violations, or expected F1. The independent relationship types show why a generic schema
is conceivable, but EXP180 proves that role annotation alone can harm final judgment. Therefore
this evidence authorizes only the feasibility work below, not a paid EXP181 prompt run.

## Candidate, if feasibility passes

Base is EXP179. Stage-1a and final remain unchanged. A single additional source-only stage-1b runs
once per exact admitted source pack; it has no metadata, card, law, product fact, label, date
calculation, or evidence-finalization instruction. It returns at most one unchanged source
substring for each of these **procedure facts**, with document ID resolved by Python:

1. qualification clause: participant subject, restriction, exception/qualifier;
2. product requirement: product/direct-production/SME condition, qualification scope;
3. specification requirement: maker/model requirement, equivalent/necessity qualifier;
4. required document: document/undertaking, submission stage/purpose;
5. contract/joint relation: method, member/role, minimum share;
6. schedule relation: event role, time, attendance eligibility consequence;
7. notice-to-metadata counterpart: explicit document field value only.

This is a source navigation ledger, not a v-keyed result. It must not emit `위반`, `0`, `1`,
law terms, inferred metadata values, calculated relations, or paraphrases. A missing/malformed
field is an empty navigation value only. Final Gemma still owns every V/E decision from card v6,
friendly metadata/product facts, the ledger, and all original sources; Python retains only
substring validation, provenance, parsing, and existing merge.

## Mandatory feasibility gates

No config, paid provider call, or canonical change is permitted until all gates pass.

1. **Schema necessity review:** map every proposed field to one of the eight documented relation
   requirements above. Remove a field that merely repeats a category or has no source endpoint.
2. **Schema/output bound:** serialize the maximal structured response. Its completion budget,
   exact Gemma tokenizer admission, dev200 stage/final pack count, and 1,853-notice call upper
   bound must be compared with EXP171's 435 dev200 calls and EXP180's 495 conservative total.
3. **Source-only proof:** export a short, attachment, and overflow stage-1b input and verify that
   its user message contains only `[공고 자료 원문]` and actual source packs. Validate every
   returned candidate against that pack and resolve document ID before it can reach final.
4. **Final completeness proof:** export the matching final messages and audit every v's card,
   required friendly metadata/product fact, full document scope, source omission, and token
   budget. The new ledger cannot replace an original source or semantic-input contract span.
5. **Mock failure matrix:** empty ledger, malformed stage-1b, duplicate excerpt, multi-pack
   provenance, absence item, evidence validation, and final parse recovery must show that no
   Python branch produces a final 0/1 from navigation.
6. **One-variable preflight:** candidate config must name EXP179 as base and allow only
   `staged_run.mode`. It must use `configs/dev_fast_panel_v1.json` and a new isolated output.

## Quality sequence and stop conditions

If all gates pass, one paid fast20 probe records macro F1, per-item TP/FP/FN, all changed cells,
navigation parser/source validity, evidence warnings, exact call topology, and runtime. It advances
only on an improvement over EXP179 with no material all-item damage, then runs the unchanged
independent holdout20 before dev200. A fast-only improvement never changes the submission policy.

If schema admission materially increases final packs, stage-1b cannot copy unchanged source facts,
or fast20 declines, this branch ends without field-by-field prompt tuning. No raw-law RAG, case
RAG, v grouping, 4k final reduction, or Python label rule is a fallback.

## Feasibility result — provider call not authorized (2026-09-10)

The minimal source-only procedure schema was constructed solely to measure its worst-case
topology. It has seven documented relation fields, each with at most two unchanged source
substrings; it has no v keys or legal/label values. Exact Gemma chat-template profiling used the
saved EXP171 generic navigation and no labels/provider calls:
`outputs/exp181-procedure-feasibility/profile.json`.

| scenario | generic stage | procedure stage | final | total calls | final source omission |
| --- | ---: | ---: | ---: | ---: | ---: |
| empty procedure ledger | 216 | 216 | 219 | **651** | 0 |
| 7 fields × 2 synthetic 360-char excerpts | 216 | 216 | 229 | **661** | 0 |

Even the empty ledger is 156 calls (31.5%) above EXP180's conservative 495-call upper profile.
The procedure pass is applied to every source pack, so batch size cannot reduce that call count.
Although source coverage and exact admission are sound, this fails EXP181's token/runtime gate
before any source-only schema quality claim exists. No EXP181 config or paid fast20 run is made.

The retained primitive and profile are audit-only evidence of rejection; they are not an invitation
to shrink field limits, tune wording, or re-open a document × group design. The architecture search
must next favor a bounded whole-notice change whose call count is materially below this topology.
