# Semantic input contract v1

## Purpose and status

This is a **pre-prompt completeness contract**, not a model prompt, card, RAG
bundle, label rule, or submission policy. Its purpose is to prevent a paid
experiment from claiming to test a legal judgment when its rendered message
contains only an item name or an unsupported shorthand.

Every statement below is distilled from the organizer-provided `항목표.json`
and `data/derived/legal_condition_ledger_v1.json`. The ledger retains the
complete organizer-law source chunks and hashes. This contract introduces no
dev-label facts, notice-specific facts, or inferred product status.

The v6 row was corrected on 2026-09-11 after tracing both national and local
rule 25. Limited tendering is part of the base applicability; a qualifying
small-contract rule is a possible allowance for a narrower area, not the sole
v6 applicability gate. See `docs/v6_applicability_scope_audit_result.md`.

For an active item, a paid prompt run must show, in its exact rendered input:

1. the matching profile-specific decision condition below;
2. the listed metadata/CSV facts, rendered in human-readable form when they
   exist for that notice;
3. the listed source-document scope (or a declared complete-document strategy
   for absence items);
4. a statement that an unverified premise does not establish a violation.

`document evidence` means the actual notice/attachment text. Metadata and the
product CSV establish applicability only; neither is an evidence quote.

### Source-scope safety invariant

The organizer description states that a violation can be present in an
attachment, not only in the announcement. The item table and retained legal
ledger do **not** positively prove an exclusive source-document type for the
remaining items. Therefore, until an organizer source establishes a narrower
location, the admission requirement for every active v is the exact set
**전체 제공 문서 (공고문, 규격서, 과업지시서, 제안요청서, 예외공표서)**. A row's
document-scope wording below describes common locations or special emphasis;
it must not be used to silently omit another supplied document. This is a
source-coverage requirement, not a claim that each document always contains
evidence.

## Deterministic profile selection

Use organizer metadata only. This selection is already defined in
`FourProfileGroupLawBundleRouter.profile_for_record`, but this contract does
not inject any law bundle:

| Profile | Metadata condition |
| --- | --- |
| `national` | 적용계약법 = 국가계약법 |
| `local_small` | 지방계약법 and 계약방법 = 수의계약 or 낙찰방법 = 소액수의견적 |
| `local_negotiated` | 지방계약법 and 낙찰방법 = 협상에의한계약 |
| `local_general` | remaining 지방계약법 notices |

## Item contracts

| Item | Applicability and 1-condition | Material 0-condition / exception | Required notice scope | Required metadata / organizer fact | Ledger source family |
| --- | --- | --- | --- | --- | --- |
| v1 | Actual participation qualification closes entry to a particular institution class, beyond general licence/registration/reporting/legal qualification. | General licence, registration, security suitability, or no institution-class restriction. | 공고문 and qualification attachments | 적용계약법 | decree 12/13, decree 21/20 |
| v2 | A manufacturing/service notice below the notice threshold uses past performance as an actual participation qualification without an applicable statutory exception. | Past performance is only evaluation/introduction, or price/type/exception is not established. | 공고문, 제안요청서, qualification attachments | 적용계약법, 업무구분, 입찰추정가격, 계약방법, 낙찰방법 | decree 21/20, rule 25, local general guide |
| v3 | A single actual-qualification performance amount exceeds one times the same contract-object, same-unit reference price. | Cumulative performance, scoring, different object/unit, or no comparable value. | 공고문 and qualification attachments | 적용계약법, 입찰추정가격, 배정예산금액 | rule 25, government/local limitation guide |
| v4 | At/above threshold, actual qualification is limited to a specific institution or issuer/type of performance without an established special technical/process/performance/quality necessity. | General qualification/performance, or threshold/restriction/necessity is unknown. | 공고문, 제안요청서 | 적용계약법, 업무구분, 입찰추정가격 | government/local limitation guide |
| v5 | At/above applicable threshold, a geographic condition is an actual participation qualification outside the permitted range. | Place of delivery/site only; a region name alone is not a restriction. | 공고문 and qualification attachments | 적용계약법, 입찰추정가격, 계약방법, 지역제한여부, 제한지역코드목록 | decree 21/20, local rule 24, price notice |
| v6 | Below the applicable notice threshold, a national or local limited tender actually restricts bidder location to a city/county/district narrower than the ordinary province-level range, or another city/county/district restriction lacks an established allowance. | A qualifying two-or-more-quotation small-contract provision expressly permits the narrower city/county area; site/delivery geography only; amount, bidder restriction, or area unit is unproven. | 공고문 and qualification attachments | 적용계약법, 계약방법, 낙찰방법, 입찰추정가격, 지역제한여부, 제한지역코드목록 | national rule 25, local rule 25, small-contract guide |
| v7 | In the same local-small regime, actual participation area is expanded beyond the permitted base area to neighbouring city/county/district or province. | Multiple place names alone; no actual participation restriction; allowance/contract regime unproven. | 공고문 and qualification attachments | 적용계약법, 계약방법, 낙찰방법, 입찰추정가격, 지역제한여부, 제한지역코드목록 | local rule 25, small-contract guide |
| v8 | The same bidder qualification simultaneously imposes performance and regional restriction in a local-small regime where that combination is not allowed. | Only one restriction, different clauses/subjects, or allowance/regime unproven. | Same qualification clause(s), including attached requirements | 적용계약법, 계약방법, 낙찰방법, 입찰추정가격, 지역제한여부, 제한지역코드목록; performance facts must come from the same notice qualification clause(s) | local rule 25, small-contract guide |
| v9 | A specification/task/RFP makes a particular maker/model a required supply condition without equivalent/compatible alternative or concrete special-need basis. | Example, installed-equipment description, general performance specification, or explicit equivalent product allowance. | **규격서, 과업지시서, 제안요청서**; announcement alone is not sufficient evidence. | 업무구분; apply law for rule profile | government/local limitation guide |
| v10 | Exact organizer CSV and notice facts establish a competition/direct-purchase product; across the complete notice, required direct-production condition is absent. | CSV not matched/unknown, or condition exists. | All supplied documents for absence check | 세부품명번호목록; friendly exact CSV applicability text | SME law 9, competition-product notice |
| v11 | Exact organizer CSV and notice facts establish a competition product; across the complete notice, required SME competition restriction is absent. | CSV not matched/unknown, or restriction exists. | All supplied documents for absence check | 세부품명번호목록; friendly exact CSV applicability text | SME law 7, decree 21/20 |
| v12 | A non-competition/general product has direct-production confirmation as an actual participation qualification without established authority. | Competition product, uncertain classification, or non-qualification mention. | 공고문 and qualification attachments | 세부품명번호목록; friendly exact CSV applicability text | decree 21/20 |
| v13 | Exact competition-product applicability plus actual qualification limited only to small enterprise/microenterprise, without established authority. | General product, unclear applicability, or preference/recommendation only. | 공고문 and qualification attachments | 세부품명번호목록; friendly exact CSV applicability text | SME law 7, decree 21/20 |
| v14 | General product at/above threshold has actual SME-only qualification without a statutory priority/special-performance/technology/quality exception. | Classification, price, restriction, or exception unproven. | 공고문 and qualification attachments | 세부품명번호목록, 입찰추정가격; friendly exact CSV applicability text | SME decree 2-2/2-3, decree 21/20 |
| v15 | General product from KRW 100m to below threshold has actual small/micro-enterprise-only qualification without 판로지원 exception. | Classification, exact price band, restriction, or exception unproven. | 공고문 and qualification attachments | 세부품명번호목록, 입찰추정가격; friendly exact CSV applicability text | SME decree 2-2/2-3, decree 21/20 |
| v16 | In the v15 band, the required SME restriction or explicit 판로지원 exception is absent across the complete notice. | Competition/unknown applicability, or required restriction/exception exists. | All supplied documents for absence check | 세부품명번호목록, 입찰추정가격; friendly exact CSV applicability text | SME decree 2-2/2-3, decree 21/20 |
| v17 | General product below KRW 100m has actual SME/small/micro qualification outside the permitted rule or exception. | Classification, price, qualification, or exception unproven. | 공고문 and qualification attachments | 세부품명번호목록, 입찰추정가격; friendly exact CSV applicability text | SME decree 2-2/2-3, decree 21/20 |
| v18 | In the v17 band, required small/micro restriction or explicit exception is absent across complete notice. | Competition/unknown applicability, or condition/exception exists. | All supplied documents for absence check | 세부품명번호목록, 입찰추정가격; friendly exact CSV applicability text | SME decree 2-2/2-3, decree 21/20 |
| v19 | A supply/technical-support undertaking is an actual pre-bid or pre-proposal submission requirement, rather than post-award/contract/delivery document. | Generic document list; contract/delivery stage; time/purpose unclear. | 공고문, 규격서, 과업지시서, 제안요청서 | 업무구분, 계약방법 | decree 12/13, rule 17, limitation guide |
| v20 | Actual SW project is in the relevant amount/large-enterprise band and the required participation limit or explicit statutory exception is absent across complete notice. | SW registration/wording alone; band or exception unknown; condition present. | All supplied documents for absence check | 정보화사업여부, 업무구분, 입찰추정가격, 긴급공고여부; any re-notice fact must come from notice text because the organizer baseline metadata has no dedicated field | SW Act/guideline appendix |
| v21 | A minimum share required of each joint-contract member falls outside the method- and profile-specific permitted minimum/range. | Representative share, investment/performance ratio, method/exception unknown. | 공고문, 공동수급 협정/attachments | 적용계약법, 공동도급구성방식, 입찰추정가격 | national/local joint-contract guide |
| v22 | In negotiated contract, non-attendance at briefing explicitly bars proposal/bid participation. | Briefing notice, recommendation, optional attendance, material distribution, or non-negotiated contract. | 공고문, 제안요청서 | 낙찰방법, 계약방법 | decree 43 |
| v23 | Local negotiated contract's actual notice/briefing/proposal deadline interval is below profile price-band minimum; national contracts are inactive. | National/non-negotiated; price-bid/opening date substituted for proposal deadline; missing necessary date. | 공고문, 제안요청서 | 적용계약법, 낙찰방법, 입찰추정가격, 공고게시일자, 긴급공고여부; briefing/proposal deadline must come from notice text because it has no dedicated organizer baseline metadata field | local decree 35, award guide |
| v24 | Same semantic field in notice and metadata has incompatible explicit values: budget, contract method, regional restriction, or industry restriction. | Missing document value, different fields, mere wording/category difference, or restriction phrase without metadata conflict. | Any document carrying counterpart field | 배정예산금액, 계약방법, 지역제한여부, 제한지역코드목록, 업종제한여부, 면허업종제한목록 | item table / metadata comparison |

## Current-prompt audit: EXP141 is incomplete

The exact G02 system message exported at
`outputs/exp-141-two-call-g02-overlay-dev200/prompt_review/pps-dev-062.grouped.messages.md`
contains only the five item names and short organizer notes. It contains none
of the v6–v9/v19 applicability, material exception, document-scope, or
profile-specific conditions in this contract. EXP141 was therefore stopped and
marked invalidated; its partial output is audit-only.

This contract must be reviewed and, if necessary, corrected against the
retained organizer-law chunks before it is rendered into any new candidate
prompt. Passing this review is not evidence that a new prompt will improve
F1; it is only the minimum condition for the experiment to actually test its
claimed legal reasoning hypothesis.
