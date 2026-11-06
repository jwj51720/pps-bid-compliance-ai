# Incubator Idea Notes

This is a hypothesis ledger, not a result log. A note becomes a policy only
after a preregistered experiment and reproducible artifact support it.

## Verified so far

- INC-121 reconfirms that a joint 24-item V-only answer is not a safe way to
  reduce output burden: under fixed card-v6/4k numbered-source input it lost
  0.12030 macro-F1 and 0.21311 micro recall against V/E. It also rejects a
  global V-plus-source-anchor contract before score: two of 32 A2 outputs
  asserted v23 without a required anchor. Preserve deterministic spans only as
  a Python evidence-validation/retrieval mechanism; do not demand an anchor
  for every final positive or retry that contract on the same cohort.

- A 4,000-character prefix is insufficient exposure; generic full-notice input
  is not a reliable improvement over a bounded prefix.
- Exact token admission is feasible for all dev notices under the final 32k
  context policy, but more context alone can dilute evidence validity.
- Product unknown-state wording and generic candidate-window judgment have not
  met recall/F1 gates.
- Raw provider content must be checkpointed before parsing; every run requires
  an exclusive lock. OpenRouter concurrency is an experiment-speed mechanism,
  not a submission runtime claim.
- The Gemma end-of-context contract reduced false positives but failed recall
  and Macro-F1 gates; it is not a default prompt policy.
- INC-027 r1 eliminated parse failures through schema clarification and durable
  per-notice checkpoints, but complete-notice extraction followed by
  adjudication lost paired Macro F1 and recall. Treat this as a rejected global
  topology, not evidence against typed source facts used only for audit.
- INC-028 fixed complete named-section boundaries for the manual INC-023 law
  citations, but exact legal-context admission remains blocked on the packaged
  Gemma tokenizer. Do not substitute character counts or a remote token probe.
- INC-030 rejects complete applicable-law context for v4/v6/v7/v8: it reduced
  FP but lost recall and target Macro F1 on all dev. The INC-029 small pilot
  also changed 7--8 of 144 cells when reissued unchanged. Treat a requested
  OpenRouter seed as a reproducibility aid, not a guarantee; future pilot
  promotions require an independently repeated arm before dev-wide spend.
- INC-032 independently rejects no-law output grouping for v4/v6/v7/v8. Its
  two all-dev runs imply very different counterfactual global gains, so choose-
  the-best reruns, output partitions, and post-hoc ensembles are prohibited.
- INC-033R establishes that source-line—not arbitrary character-window—facts
  can fully cover v3 and v21 positives while sharply reducing benign candidate
  activation. v19 and v23 do not meet the complete-coverage gate and remain
  unsuitable for an automatic predicate.
- INC-049 tests the newly proposed criterion-to-source retrieval link directly,
  without an LLM rationale.  BGE plus metadata improves source-evidence MRR
  over lexical matching (0.1271 vs 0.0804) but retrieves only 40.7% of
  organizer nonempty evidence within 20 lines.  Do not use BGE source ranking
  to gate labels, replace full document context, or invent a per-item cutoff.
  A future fact-ledger query remains an idea only if it is independently
  compared against this frozen retrieval baseline and full-document final
  judgment remains intact.
- INC-050 establishes an important transport constraint: strict JSON schema
  and requested `max_tokens=500` did not bound this Gemma/OpenRouter route;
  25/144 initial responses ran to a provider-reported 8,192 whitespace tokens,
  and four remained malformed after a single identical recovery.  Treat
  structured-output recovery and provider completion enforcement as a separate
  experimental variable before interpreting future prompt/model treatments.
- INC-051 isolates that constraint: flat strict JSON schema passes 10/10 with
  26-token outputs, while the nested object-per-item schema fails immediately
  at 8,192 whitespace tokens.  Future calls should use flat fields, but a
  separate no-data audit must first validate flat evidence-candidate fields.
- INC-053 validly retests the frozen v10--v13 product applicability sheet with
  flat transport and rejects it in both repeats (−0.0494, −0.0980 target
  Macro F1).  The sheet removes some v12 false positives but loses v13 true
  positives.  Do not reword/reconfirm product fact sheets; carry forward only
  the flat response transport and source-candidate infrastructure.
- INC-034/036 separately pass their stated deterministic gates on v21 and v3:
  a jurisdictional minimum-share default and a single-amount bidder-
  qualification performance requirement compared with organizer budget. The
  rules reject ambiguous/missing facts rather than resolving them heuristically.
- INC-037 composes only these four target cells into the immutable INC-018 CSV:
  Macro F1 is 0.24856, all positive evidence is source-contained, and all other
  cells/row order are unchanged. This is a reproducible candidate component,
  not evidence that the same score transfers to hidden notices. Do not mine its
  82 v3 or 9 v21 unlabeled positives for thresholds or prevalence claims.
- INC-038 rejects generic institution and region source cues as automatic
  policies (94.8% and about 65.8% negative activation). It also rejects the
  task-document-only v9 assumption (0/6 coverage). Its v2/v4 performance facts
  are fully covering with roughly 15% negative activation, so the next broad
  qualification branch is a joint legal-role/applicability audit for those two
  items—not a numeric threshold tweak.
- INC-039 rejects its strict v2/v4 candidate role as a complete automatic gate:
  it misses 3/7 v2 and 1/6 v4 positives. INC-040 resolves v2 separately using
  the organizer's actual 230M notice amount and a true entry-eligibility role,
  reaching 7/0/0 without a dev-derived cutoff. INC-041 composes v2/v3/v21 to
  0.26750 with no non-target cell changes. Freeze all three wordings now;
  v4 remains a semantic specific-performance problem suitable for replicated
  LLM adjudication, not another lexical expansion.
- INC-042 rejects the first replicated v2/v4 LLM topology before score
  comparison: 20/144 responses had a positive judgment with non-verbatim
  evidence. INC-043 can recover only 10 via unique whitespace-only matching,
  leaving 11 altered/omitted quotes. Future active LLM outputs must choose a
  Python-generated exact source-candidate ID; do not retry free-text quotation
  with cosmetic prompt edits or score failed records as zero.
- INC-044/045 establish source candidate IDs as a viable evidence transport
  (143/144 successful schema/evidence pairs) but reject v4 legal adjudication:
  the model fires on generic and expressly non-exclusive performance text,
  yielding 21–23 FP despite all 6 TP. Candidate IDs solve quotation fidelity,
  not legal semantics. Park v4 rather than tune it on these same notices.
- INC-046 parks v5--v8 automatic regional rules: facts miss at least one
  positive for v5/v6/v8, while generic region facts fire in roughly 47% of
  negatives and organizer region-code metadata is absent in several positives.
  Do not compensate with a dev-tailored place-name dictionary.
- INC-047 parks generic v9 model/brand identifier rules: typography-level facts
  cover all positives but activate in 95.4% of negatives. Do not add dev-case
  brand names; a future v9 branch must distinguish binding specification from
  descriptive/equivalent-product language.
- INC-048 establishes unchanged source lines as the retrieval/evidence unit for
  a future extract→retrieve route. Punctuation sentence splitting loses table
  and layout evidence; it may index tokens but must not be the default final
  evidence segmentation. Lines over 500 characters remain unresolved unless a
  separately valid unchanged subspan is available.

## Evidence architecture ideas (not yet policies)

- Separate legal judgment from verbatim quotation. A model may identify the
  right rationale yet reflow punctuation, tables, or line breaks. Generated
  rationale text can retrieve an original source fragment, but it cannot itself
  become submission evidence.
- Test a provenance-preserving three-stage route only against a frozen control:
  (1) an item-specific extractor receives the full notice and legal criterion
  and returns a concise rationale/fact ledger; (2) Python splits the original
  source deterministically on document, line, and punctuation/layout boundaries
  and ranks unchanged fragments against that ledger using lexical plus permitted
  BGE-M3 similarity; (3) a final adjudicator receives the full notice, the
  extracted ledger, and retrieved exact source candidates, then selects a
  candidate ID or `NONE`. Python supplies the evidence substring.
- Retrieval may expand attention but must never invent, rewrite, concatenate,
  or silently truncate evidence. The candidate fragment must be one unchanged
  source substring at most 500 characters; ambiguity or poor match remains
  unresolved rather than being forced to a positive.
- Before paid calls, measure extractor-to-source retrieval recall on a frozen
  labeled audit set, candidate cardinality, and exact evidence containment.
  Compare a one-call candidate-ID adjudicator with the three-stage route under
  identical cohort, law context, output schema, and repeat policy. Do not
  conflate an evidence-recovery gain with a legal-decision gain.

**INC-064 result:** a full-notice, item-specific legal/factual memo improved
BGE source-line MRR (0.13655 → 0.20826) but had one of twelve paired rank
regressions and left two v4 gold lines at ranks 120 and 141.  It is not safe
to turn the memo into a retrieval/candidate gate or a label condition.  A
future use, if any, must leave the complete notice in the final adjudicator
and treat the memo/candidates as optional attention support only.

## Pending ideas (not yet policies)

- Legal-essence cards: INC-070 source-audited only 11/24 compact cards.
  INC-071 is invalid because its control accidentally lacked item names; do
  not treat its apparent gains as a card signal.  A fresh paired test must put
  the identical item-definition/absence contract in both arms and add only
  the accepted card statements to treatment.
- INC-072 supplied that valid paired comparison and rejects direct global
  legal-essence injection: repeat deltas were +0.00260 and -0.05801.  Cards
  suppress FP but lose recall, especially v11/v23.  Retain them only as
  controlled vocabulary for an e-prime extraction/fallback experiment; never
  turn an empty e-prime into a negative label.
- INC-073 rejects a one-call joint e-prime extractor/hybrid: positive e-prime
  coverage was only 55.56% and 44.44%, with deltas -0.09963 and +0.00380.
  The fallback itself is safe, but a nonempty incomplete summary can still
  cause a wrong e-prime-only decision.  A future e-prime branch needs a
  homogeneous item family and a measured completeness gate before adjudication.
- INC-074/075 distinguish evidence locality from decision locality.  Although
  v7/v23 nonempty gold evidence is entirely in the announcement, a
  full-document versus announcement-only paired test had deltas -0.02381 and
  +0.35119 and did not improve v23 FP.  Do not hide other documents as a
  predictive policy; retain source-document type only for evidence transport.
- INC-076 freezes a 100/100 multi-label-balanced prospective holdout.  INC-041
  is 0.25580 versus 0.27625 across folds, so future pilot deltas materially
  below roughly 0.02 are not integration evidence.  Explore on one fold and
  confirm once unchanged on the other; stop selecting directions from repeated
  all-dev scores.

- Gemma-specific prompt contract: inspect current official Gemma documentation
  before a new prompt experiment; compare one structured reasoning/output
  contract against a fixed control, never bundle it with context or rules.
- Complete legal-article context isolation: after token-admission preflight,
  compare one joint-24 full-notice control against the same joint output with
  only source-complete, item-linked organizer-law units. Do not conflate this
  with output family decomposition, RAG examples, or a dev-derived length cap.
- Evidence architecture: deterministic source-offset spans may repair evidence
  alignment even when they do not improve judgment F1.
- BGE-M3 remains deferred until lexical retrieval shows a source-coverage gap
  that exact cues cannot close.
- v20 law decision card: audit the organizer guideline as a fact packet before
  any active-item call. Treat missing information-project metadata as unknown;
  never use it as an applicability gate.
- v20 law-card pilot passed on 5 positives plus 10 matched negatives (F1
  0.66667 to 0.88889). Freeze its wording and test the paired card/control on
  all dev notices before proposing any policy promotion.
- INC-015 rejected the frozen v20 card on all dev: it raised recall but added
  nine net false positives and reduced F1 (0.60 to 0.40). Preserve the law
  facts only. A future candidate must separately request source-backed SW
  applicability and declaration status before a deterministic v20 merge; do
  not repair with amount, metadata, or lexical cue gates.
- INC-017 also rejected that predicate decomposition (F1 0.27273). Its
  declaration-present field was absent for 198/200 notices; source-substring
  gating added two false negatives. Post-hoc lexical rescue stays below the
  no-card control, so park v20 rather than tune it against the same dev set.
- INC-018 establishes `single_full` as the first credible dev-200 global
  reference (Macro F1 0.19361, close to the external 0.21). Per-document
  OR/AND merging is rejected: it raised recall but drove FP to 981 and evidence
  validity to 0.15613. Next research is a v10--v18 product/procurement family
  applicability matrix, not another document-pack or v20 prompt variant.
- INC-019 rejects a single v10--v18 product-family card: exact competition
  product codes leave many positives unknown, while small-business language is
  nearly ubiquitous in negatives. Split future work into v10--v13
  competition-product and v14--v18 general-product amount/exception families;
  never turn product-code match, non-match, or absence into an automatic label.
- INC-020/021 establish a permitted organizer-law BGE-M3 index and show that
  retrieved-law family passes improve global Macro F1 0.19361 to 0.21074 while
  sharply improving evidence validity and reducing FP. The remaining problem
  is recall from globally compressed law excerpts; next test adaptive legal
  context admission rather than an OR ensemble or another item-local prompt.
- INC-022 was invalidated before completion (625/800 calls). Its 165/600-char
  excerpt settings were derived from dev token fit, not a generalizable legal
  or submission invariant. Never tune fixed context length to dev extremes;
  future RAG context must preserve complete retrieved legal article/paragraphs
  and use a predeclared, submission-parity token admission policy.
