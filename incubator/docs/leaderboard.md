# Incubator Research Leaderboard

이 표는 DACON 리더보드가 아니다. 고정된 실험 cohort와 재현 artifact를 가진 내부 연구
기록이다. 서로 다른 cohort의 Macro F1은 직접적인 우열이 아니라 실행 상태와 가설의
증거로 해석한다.

## 공개 제출 교정점

| Submission | 정책 | Dev-200 | 공개 점수 | 차이 |
|---|---|---:|---:|---:|
| `pps_20260905_170543.zip` | EXP-120, 4,000자 + card v6 + 단일 Gemma V/E | 0.248932 | **0.244317** | -0.004615 |

이는 EXP-120 정책군에서 dev-200과 공개 점수가 잘 정렬된 한 개의 관측치다. 이후
후보는 이 정책을 fixed control로 하는 independent cohort와 dev-200 confirmation을
통과해야 한다. 상세 milestone은 `post_exp120_bfs_milestone.md`에 고정한다.

| Run | Policy | Cohort | Macro F1 | Decision |
|---|---|---:|---:|---|
| INC-121 control | card v6 + numbered 4k source + V/E | 32 | 0.25502 | Comparator only; rendering differs from EXP-120. |
| INC-121 A1 | Same input, V-only | 32 | 0.13472 | Rejected: recall collapse. |
| INC-121 A2 | Same input, V + source-anchor ID | 32 | unscorable | Rejected: 2/32 positive-without-anchor semantic failures. |
| INC-122 control | EXP-120-style card v6 V/E | 32 | 0.12500 | Comparator only. |
| INC-122 treatment | + compact profile official-law summary | 32 | 0.08333 | Rejected: -0.04167 macro F1, recall loss. |
| INC-123 | Archived EXP-120 + frozen v2/v3/v21 predicates | 200 | **0.31780** | Advance to isolated package integration; hidden-test transfer unproven. |

| Run | Policy | Cohort | Macro F1 | TP / FP / FN | Evidence validity | API cost | Decision |
|---|---|---:|---:|---|---:|---:|---|
| INC-001 | Joint 24-item, 4,000-character ordered context, no RAG/rules/cards | 24 | 0.13036 | 7 / 30 / 30 | 0.81081 | $0.01657 | Operational baseline accepted; no performance policy promoted |
| INC-002 control | Joint-24 output; v13-focused paired cohort | 18 | v13 F1 0.60000 | 6 / 8 / 0 | 0.42857 | $0.01546 | Comparator only |
| INC-002 treatment | v13-only output; otherwise same context; no facts/law/RAG | 18 | v13 F1 0.28571 | 1 / 0 / 5 | 0.00000 | $0.00790 | Rejected: recall collapse |
| INC-003 control | Joint-24 output; product-fact cohort | 18 | v13 F1 0.57143 | 6 / 9 / 0 | 0.46667 | $0.01513 | Comparator only |
| INC-003 treatment | Joint-24 plus official CSV exact product applicability fact | 18 | v13 F1 0.57143 | 4 / 4 / 2 | 0.37500 | $0.01484 | Partial: FP down, unknown-state recall loss |
| INC-004 treatment | Neutral unknown-state wording, seed-matched repair cohort | 7 | v13 F1 0.28571 | 1 / 4 / 1 | 0.60000 | $0.00487 | Rejected: only half recall recovered; 4/5 unknown negatives false positive |
| INC-006 control | Joint-24; ordered 4,000-character budget | 24 | 0.07963 | 5 / 33 / 32 | 0.71053 | $0.02103 | Contemporary comparator only |
| INC-006 treatment | Same policy; ordered 12,000-character budget | 24 | 0.18407 | 11 / 27 / 26 | 0.84211 | $0.03164 | Coverage signal only; INC-008 rejected fixed-length/full-context promotion |
| INC-008 prefix | Joint-24; 12,000-character diagnostic prefix | 24 | 0.15899 | 9 / 29 / 28 | 0.81579 | $0.03206 | Contemporary comparator only |
| INC-008 full notice | Whole exact-token-admitted notice | 24 | 0.15926 | 10 / 28 / 27 | 0.76316 | $0.04767 | Rejected: no material gain, evidence decline, higher cost |
| INC-010 control | Active v19--v21, 12k prefix | 33 | target F1 0.39434 | 11 / 19 / 6 | 0.96667 | $0.03287 | Comparator only |
| INC-010 treatment | Active v19--v21, lexical candidate windows | 33 | target F1 0.38974 | 10 / 16 / 7 | 1.00000 | $0.01720 | Rejected: lower recall/F1 despite fewer FP and tokens |
| INC-012 control | Joint-24, 12k ordered context | 24 | 0.15480 | 9 / 36 / 28 | 0.82222 | included below | Comparator only |
| INC-012 treatment | Same input plus end-of-context decision contract | 24 | 0.14167 | 7 / 27 / 30 | 0.88235 | $0.06601 paired | Rejected: recall and Macro F1 declined |
| INC-014 control | v20-only, full notice, source-only contract | 15 | v20 F1 0.66667 | 3 / 1 / 2 | n/a (absence item) | paired below | Comparator only |
| INC-014 treatment | Same full notice plus organizer-law v20 fact card | 15 | v20 F1 0.88889 | 4 / 0 / 1 | n/a (absence item) | $0.05085 paired | Provisional: passes gate; requires all-dev confirmation |
| INC-015 control | v20-only, full notice, all dev | 200 | v20 F1 0.60000 | 3 / 2 / 2 | n/a (absence item) | paired below | Comparator only |
| INC-015 treatment | Same full notice plus frozen v20 law card | 200 | v20 F1 0.40000 | 4 / 11 / 1 | n/a (absence item) | $0.67498 paired | Rejected: +9 net FP; no policy promotion |
| INC-017 treatment | v20 structured source-validated predicates, full notice | 200 | v20 F1 0.27273 | 3 / 14 / 2 | diagnostic evidence gate | $0.32832 | Rejected: declaration-present recognition collapsed |
| INC-018 single | Joint 24-item, all documents, all dev | 200 | 0.19361 | 49 / 241 / 104 | 0.70690 | $0.76907 paired | Accepted as global reference baseline |
| INC-018 split | Per-document 24-item passes; OR/AND merge, strict target evidence | 200 | 0.15108 | 63 / 981 / 90 | 0.15613 | $0.76907 paired | Rejected: speculative OR false positives |
| INC-021 | Retrieved organizer-law context, four disjoint full-notice family passes | 200 | 0.21074 | 33 / 111 / 120 | 0.96528 | $1.39503 | Partial: strong precision/evidence gain, recall collapse |
| INC-024 joint | Complete-notice 24-item output, no RAG/facts | 12 preregistered | 0.15933 | 8 / 15 / 11 | 1.00000 | $0.09154 paired | Comparator only |
| INC-024 family | Same complete notice, four disjoint output families only | 12 preregistered | 0.12460 | 9 / 19 / 10 | 1.00000 | $0.09154 paired | Rejected: +1 recall but +4 FP, -0.03472 Macro F1 |
| INC-027 r1 | Complete-notice typed fact ledger then 24-item adjudication | 8 frozen paired | 0.14444 | 7 / 7 / 12 | 1.00000 | $0.02766 | Rejected: only +1 net correct cell; F1/recall below joint control |
| INC-029 | v4/v6/v7/v8 complete applicable-law context, same whole notice | 36 frozen paired | target 0.38515 | 9 / 8 / 16 | 1.00000 | $0.09286 paired | Pilot success: +0.07635 target F1, -7 FP; dev-200 confirmation required |
| INC-030 | Frozen INC-029 policy, all dev confirmation | 200 paired | target 0.24991 | 9 / 22 / 16 | 1.00000 | $0.55276 paired | Rejected: -0.05957 target F1, recall -0.08; pilot was not replication-safe |
| INC-032 | Exact no-law v4/v6/v7/v8 output-group replication | 200 | target 0.22577 | 9 / 36 / 16 | 1.00000 | $0.23419 | Rejected: -0.08371 versus original group run; unstable component |
| INC-033 / 033R | Full-source then source-line predicate-fact audit (v3/v19/v21/v23) | 200 offline | candidate recall / negative rate | v3 1.00 / 0.099; v21 1.00 / 0.124 | provenance retained | $0 | Advance only v3/v21 fact shapes; v19/v23 lack complete positive coverage |
| INC-034 | v21 jurisdictional default-share source predicate | 200 offline | v21 1.00000 | 6 / 0 / 0 | 1.00000 | $0 | Diagnostic passes; compose only with immutable baseline |
| INC-035 | Replace only INC-018 v21/e21 with frozen INC-034 rule | 200 offline | 0.22650 | v21 6 / 0 / 0 | 1.00000 | $0 | Controlled one-item gain; unlabeled source-format audit only |
| INC-036 | v3 single-amount bidder-qualification performance predicate | 200 offline | v3 1.00000 | 8 / 0 / 0 | 1.00000 | $0 | Diagnostic passes after excluding non-qualification performance mentions |
| INC-037 | Replace only INC-018 v3/e3 and v21/e21 with frozen rules | 200 offline | 0.24856 | v3 8 / 0 / 0; v21 6 / 0 / 0 | 1.00000 | $0 | Reproducible composition candidate; no hidden-test claim |
| INC-049 | Criterion/metadata BGE to intact source-line retrieval | 200 offline + BGE | retrieval MRR | 0.12710 vs lexical 0.08045 | n/a | $0.04640 | Reject as evidence gate: Recall@20 only 40.7%, so it cannot replace full-notice judgment or suppress labels |
| INC-050 | Repeated v10--v13 full-notice product applicability fact sheet | 36 × 4 | unscorable | 4 persistent JSON whitespace failures after one recovery | n/a | $0.23549 | No treatment conclusion; provider ignored 500-token cap and emitted 8,192-token whitespace streams |
| INC-051 | Synthetic structured-output transport audit | 21 calls | flat-schema validity | flat strict 10/10; JSON-object 10/10 | n/a | $0.00358 | Reject nested schema (8,192-token whitespace); promote flat strict binary transport |
| INC-052 | Synthetic flat binary + candidate-index transport audit | 10 calls | exact validity | 10/10, no cap breach | n/a | $0.00030 | Advance: candidate IDs can use flat integer indices; enables a clean new product-pilot rerun |
| INC-053 | Flat-transport repeated v10--v13 product fact sheet | 36 × 4 | target Macro F1 | r1 −0.04937; r2 −0.09802 vs paired control | 1.00000 transport validity | $0.12221 | Reject: v12 FP reduction was outweighed by v13 true-positive loss; no all-dev confirmation |
| INC-054 | Flat Joint-24 label-only, full-notice diagnostic | 48 × 2 | Macro F1 vs fixed INC-041 reference | r1 −0.10323; r2 −0.04361 | 1.00000 transport validity | $0.08642 | Reject: removing evidence generation loses established decision signal; no all-dev run |
| INC-055 | Dev/unlabeled template-overlap audit | 200 dev + 20,000 unlabeled offline | exact-document overlap | 0 exact duplicates; universal boilerplate line overlap | n/a | $0 | Reject generic case RAG or label transfer; source-line overlap is non-discriminative |
| INC-057 | Legal predicate feasibility provenance map | 200 offline | source/law observability | v4 5/6, v7 7/7 nonempty organizer evidence with legal units | n/a | $0 | Narrows shared legal-program audit to v4/v7; does not promote rules |
| INC-058 | Common bidder-role source-fact audit (v4/v7) | 200 offline | candidate recall / negative activation | v4 0.0% / 0.5%; v7 28.6% / 7.3% | n/a | $0 | Reject: explicit eligibility role is not observably complete |
| INC-060 | Flat Joint-24 source-line-ID grounded pilot | 48 × 2 | unscorable | 45 positive-without-ID contract failures | JSON 100%, semantic contract failed | $0.10896 | Reject direct all-item line-ID grounding; no partial score or repair |
| INC-062 | Per-positive source-line locator | 71 fixed-positive calls | source-ID transport | 71/71 valid line IDs; 8/11 gold-evidence subset containment | n/a (labels fixed) | $0.07922 | Advance evidence transport only; no label/F1 claim |
| INC-063 | Repeated grounded Joint-24 majority consensus | 48 × 3 | Macro F1 vs mean raw | 0.18425 vs 0.19227 mean raw | evidence gate failed | $0.14432 | Reject global majority; no all-dev consensus or threshold tuning |
| INC-064 | Full-notice legal/factual memo → BGE source-line retrieval | all 12 v4/v7 positive-evidence cells | evidence retrieval MRR | 0.20826 vs criterion 0.13655; one paired regression | n/a | $0.02410 | Reject as candidate gate: ranks 120/141 remain and one pair worsens |
| INC-065 | All-item formal legal-program necessary-observability audit | 200 offline | program eligibility | only v2/v3 (already proven) and v22 (already F1 .909) pass | n/a | $0 | Close broad deterministic-rule expansion; no new high-loss item is observably complete |
| INC-066 | Independent per-item source-line attention proposal → full-notice label pass | 20 × 2 | unscorable | all 40 locators valid but 960/960 IDs were -1; final 24-label objects truncated at 128 tokens | n/a | $0.12108 | Reject before score: unconditional locator has vacuous semantic output; no transport-only rerun |
| INC-067 | Gemma-4 `<|think|>` strict-JSON transport audit | 12 synthetic calls | thinking activation | both arms 6/6 valid, identical 234 tokens, 0 reported reasoning tokens | n/a | $0.00136 | Reject as decision variable: no observable trigger effect via this provider/schema route |
| INC-068 | Same-conversation provisional legal memo → final labels | 20 × 2 | unscorable | control 40/40 valid; memo coverage failed 1/20 and 2/20 | n/a | $0.12111 | Reject: intermediate legal analysis is not reproducibly complete |
| INC-038 | v1--v9 qualification-family source-fact coverage | 200 offline | candidate recall / negative rate | v2 1.00 / 0.150; v4 1.00 / 0.155 | provenance retained | $0 | Advance only v2/v4 legal-role audit; reject broad v1/region auto-rule and task-only v9 assumption |
| INC-039 | v2/v4 strict performance-role audit | 200 offline | candidate recall / negative rate | v2 0.571 / 0.062; v4 0.833 / 0.057 | provenance retained | $0 | Reject as complete automatic gate; role coverage insufficient |
| INC-040 | v2 below-notice performance legal predicate | 200 offline | v2 1.00000 | 7 / 0 / 0 | 1.00000 | $0 | Diagnostic passes; legal threshold comes from organizer notice, not dev |
| INC-041 | Add only v2/e2 to verified INC-037 composition | 200 offline | 0.26750 | v2 7 / 0 / 0 | 1.00000 | $0 | Controlled reproducible candidate; no hidden-test claim |
| INC-042 | Replicated v2/v4 complete-law active adjudication | 36 × 4 | not scored | 20 source-evidence format failures / 144 calls | ineligible | $0.31287 | Rejected before metric: free-text evidence not reliable enough |
| INC-043 | INC-042 whitespace-only evidence resolution audit | 21 failed positive quotes offline | 10 uniquely source-resolved; 11 unresolved | n/a | 1.00000 for resolved slices | $0 | Cannot retroactively rescue INC-042; source-candidate IDs required |
| INC-044 | v2/v4 exact source candidate-ID coverage | 200 offline | v2/v4 gold-evidence coverage 1.000 | n/a | source-preserving IDs | $0 | Candidate-ID evidence contract feasible (≤5/notice) |
| INC-045 | Replicated v2/v4 candidate-ID law adjudication | 36 × 4 | r2 target macro 0.40672 law; r1 unscorable | v4 TP 6 but FP 21–23 | 1.00000 successful calls | $0.21624 | Reject semantic v4 topology; retain candidate-ID transport only |
| INC-046 | v5--v8 regional restriction source/metadata fact audit | 200 offline | candidate recall / negative rate | v5 .857/.472; v6 .833/.474; v7 1.0/.466; v8 .833/.021 | provenance retained | $0 | Reject automatic regional gate; metadata region codes incomplete |
| INC-047 | v9 document-independent product-identifier fact audit | 200 offline | candidate recall / negative rate | 1.000 / .954 | provenance retained | $0 | Reject generic identifier gate; technical identifiers ubiquitous |
| INC-048 | Global source line/sentence evidence-fragment audit | 200 offline | nonempty-gold evidence containment | line generally 1.000; sentence often loses tables/layout | provenance retained | $0 | Promote immutable source line as retrieval/evidence unit; not sentence splitting |

## Comparison notes

INC-005 is an offline structural audit, not a scored model run: it found no
output-length truncation but only 30.76% mean source-document character
coverage under the 4,000-character pilot cap. Its report is the basis for the
bounded input-coverage ablation, not a performance claim.

INC-011 is also offline only: its first v24 typed candidate extractor reached
87.5% positive candidate recall with 76.0% negative candidate rate, so it is
blocked from a Gemma pilot.

The same 24-notice cohort scored 0.14605 with the preserved historical
EXP-001 output. INC-001 and that output agree on 548/576 label cells (95.14%).
The independent baseline deliberately uses a simpler implementation and is not
an exact rerun, so the -0.01570 difference is a calibration observation, not a
selection result.

Per-run local artifacts live under the ignored `incubator/runs/` tree. The
tracked experiment note contains the hypothesis, gates, aggregate diagnostics,
and next decision without copying competition documents.

INC-004's first run was invalidated by concurrent checkpoint writers, and its
second locked run used a seed mismatch. Neither is shown above. The listed
seed-matched run had one malformed control response; the neutral treatment's
own failure-free result independently fails its pre-registered gate.

INC-024 is a mechanism result rather than a proposal to compare its 12-notice
Macro F1 with full-dev runs. It cleanly refutes standalone output-family
decomposition under identical complete inputs; INC-021's score cannot be read
as evidence for the decomposition because it also changed legal context.

INC-025 is an unscored BGE retrieval gate: complete-notice leave-one-out
retrieval reached 2× label enrichment for only 8/24 items at ranks 1/3/5, with
no coherent family. Generic Case RAG is therefore not promoted to a Gemma
few-shot experiment.

INC-027's original execution was invalid after a malformed extractor response.
The separately recorded r1 used a clarified fact-type schema and per-notice
durable checkpoints, completed 16/16 calls, and is the only scored INC-027 arm.
It rejects global extraction/adjudication separation, not source-preserving
typed-field analysis for a genuinely cross-source item such as v24.

INC-029's positive small-cohort result is not a policy candidate after INC-030:
the all-dev confirmation failed and its embedded repeat of the same 36 notices
showed 7--8/144 label-cell output variation despite identical recorded request
settings. Future small paid pilots need an independently repeated arm before
they can justify a dev-200 escalation.
