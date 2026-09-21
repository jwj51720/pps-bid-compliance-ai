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
| v2 | A goods-manufacturing/service notice below its applicable threshold uses past completed performance as an actual participation qualification. Select the threshold from the contract law and actually applicable institution rule: national ordinary goods/services KRW230m; an actually applicable public-corporation/quasi-government rule KRW710m; local goods-manufacturing/services use the MOEF-notified procurement amount (organizer notice: KRW230m), not local rule 24's MOIS/KRW500m regional-restriction branches. For local contracts, allowed performance restriction at/above that amount additionally requires special equipment/technology for goods manufacturing or special technology for services. | Past performance is evaluation/introduction only, at/above the applicable amount for this below-threshold item, not goods manufacturing/service, or price/law/institution rule/role is unproven. Do not substitute budget/base amount for estimated price or infer special technology from a generic contract type. | 공고문, 제안요청서, qualification attachments | 적용계약법, 소관구분, 업무구분, 입찰추정가격, 계약방법, 낙찰방법 | national decree/rules 21/24/25, local decree/rule 20/25, local limited-tender guide, MOEF price notice |
| v3 | Compare one actual-qualification performance requirement to the same-object/same-unit reference. National size/quantity/amount is capped at 1x. Local size/quantity is ordinarily capped at 1/3 and may rise to at most 1x only for an established need based on characteristics/safety/difficulty/method; local amount is capped at 1x. The item-name `1배수 이상` conflicts with the rules' allowance of exactly 1x, so do not silently invent the equality label. | Cumulative/evaluation performance, different object/unit, no comparable value, an established local upward allowance within 1x, or the unresolved exact-1x boundary. | 공고문 and qualification attachments | 적용계약법, 입찰추정가격, 배정예산금액 | rule 25, government/local limitation guide |
| v4 | Actual qualification recognizes only performance ordered by a specific institution or narrowly named/institution-type/business-type performance that excludes substantially equivalent performance without concrete necessity. This amount-independent scope is confirmed jointly by the organizer limitation guide and organizer v4 labels/evidence, including multiple positives below the general notice amount and one v3=0/v4=1 case. | General performance open across ordering institutions and equivalent types, evaluation-only performance, statutory qualification, not an actual qualification, or concrete technical/method/performance/quality necessity. | 공고문, 제안요청서 | 적용계약법, 업무구분 | government/local limitation guide; organizer dev labels/evidence/metadata used only to resolve the published-definition conflict |
| v5 | At/above the selected regional-restriction amount, bidder headquarters/place-of-business is geographically restricted without authority. National: general construction KRW8.8bn, specialist/other construction KRW1bn, ordinary goods/services KRW230m; actually applicable public-corporation/quasi-government rule: construction KRW26.5bn, goods/services KRW710m. Local: general construction KRW15bn, specialist/other construction KRW1bn, listed technical/design/supervision/engineering services KRW330m (safety inspection/precision diagnosis KRW150m), and other goods/services use the rule-24 article-5/MOIS/KRW500m branches. | Site/delivery place only, below selected amount, explicit authority, or law/institution/work-type/price/role unproven. | 공고문 and qualification attachments | 적용계약법, 소관구분, 업무구분, 입찰추정가격, 계약방법, 지역제한여부, 제한지역코드목록; article-5 applicability/entity subtype must be supplied, not inferred from name | decree 21/20, national/local rule 24, price notice |
| v6 | Below the same full national/public-corporation/local construction/goods/service threshold ladder as v5, actual bidder location is narrowed from the ordinary province-level range to city/county/district without an established allowance. | A qualifying two-or-more-quotation small-contract provision permits the narrower area; site/delivery geography only; or threshold/role/unit/exception unproven. | 공고문 and qualification attachments | 적용계약법, 소관구분, 업무구분, 계약방법, 낙찰방법, 입찰추정가격, 지역제한여부, 제한지역코드목록 | decree 21/20, national/local rules 24/25, price notice, small-contract guide |
| v7 | Below the same full threshold ladder as v5, actual bidder geography combines a base area with adjacent or other additional regions without an established allowance. | Single region; site/delivery names only; or an established contract-law allowance such as a cross-border site, adjacent delivery/maintenance location, fewer than10 qualified firms, or qualifying local small-contract rule. | 공고문 and qualification attachments | 적용계약법, 소관구분, 업무구분, 계약방법, 낙찰방법, 입찰추정가격, 지역제한여부, 제한지역코드목록 | decree 21/20, national/local rules 24/25, price notice, small-contract guide |
| v8 | The same bidder qualification simultaneously imposes performance and regional restriction in a local-small regime where that combination is not allowed. | Only one restriction, different clauses/subjects, or allowance/regime unproven. | Same qualification clause(s), including attached requirements | 적용계약법, 계약방법, 낙찰방법, 입찰추정가격, 지역제한여부, 제한지역코드목록; performance facts must come from the same notice qualification clause(s) | local rule 25, small-contract guide |
| v9 | A supplied document makes a maker/brand/spec/model a required delivery condition without a real equivalent-product route or contract-law-specific necessity. Local explicit exception is limited to special life/health/safety/hygiene reasons; national necessity must be concrete (for example lawful sole-source/compatibility/no substitute), not generic technical-support convenience. | Example, installed-equipment description, general performance specification, real equivalent-product allowance, or concrete applicable exception. | 공고문, 규격서, 과업지시서, 제안요청서 | 적용계약법, 업무구분, 계약방법 | government/local limitation guide |
| v10 | Exact organizer CSV and notice facts establish a competition/direct-purchase product; across the complete notice, required direct-production condition is absent. | CSV not matched/unknown, or condition exists. | All supplied documents for absence check | 세부품명번호목록; friendly exact CSV applicability text | SME law 9, competition-product notice |
| v11 | Organizer CSV candidate and actual purchased object/conditions establish a competition product; across the complete notice, required SME-only limited competition or SME-only designated competition is absent and no applicable article-7 special reason permits another method. | Non-applicable/uncertain product; required restriction exists; or an actually applicable special reason: statutory priority/direct contract product, article-8 association-recommended direct contract, failed SME competition followed by a new other competition, or specific technology/service/public-institution circumstance. Mere future rebid guidance, negotiated method, or a technology word is not the exception. | All supplied documents for absence and exception check | 세부품명번호목록; friendly exact CSV row including conditions and provenance; any exception reason must be present in supplied notice/organizer metadata rather than inferred | SME law 7, SME decree 7, decree 21/20 |
| v12 | The actual purchased object is outside SME-law article9 coverage, but direct-production confirmation is an actual participation qualification. Article9 covers SME-competition procurement and specified competition-product direct contracts at/above KRW10m; a generic special-equipment/technology condition does not itself authorize the certificate for a general product. | Article9-covered procurement, non-qualification mention, or purchased-object/product-row/condition/method/price relationship unproven. | 공고문 and qualification attachments | 세부품명번호목록, 입찰추정가격, 계약방법; friendly exact CSV applicability text | SME law 9, SME decree 10, decree 21/20 |
| v13 | An applicable competition product is actually restricted to small enterprise/microenterprise without the article7-2 designated-product or qualifying three-or-more-small-firms association joint-project authority. | General/uncertain product; preference only; applicable designated-product authority; or qualifying joint-project participant limitation / association-recommended designated competition. | 공고문 and all qualification/joint-project attachments | 세부품명번호목록; friendly exact CSV row including conditions/provenance; designation/joint-project facts must come from supplied organizer material or notice and are not implied by ordinary competition-product membership | SME law 7-2, decree 21/20 |
| v14 | A non-competition good/service at KRW230m or more has actual SME-only qualification without a separate statute authorizing that restriction. Article2-3 exceptions waive below-threshold priority procurement; they do not authorize an above-threshold general-product SME restriction. | Below KRW230m, applicable competition product, no actual SME qualification, a separate statute actually authorizes the restriction, or required fact unproven. Do not substitute KRW710m or a local regional amount. | 공고문 and qualification attachments | 세부품명번호목록, 입찰추정가격; friendly exact CSV row including conditions/provenance | SME decree 2-2/2-3, decree 21/20, national price notice |
| v15 | A non-competition good/service from KRW100m to below KRW230m has actual small/micro-enterprise-only qualification that remains for ordinary for-profit bidders without an applicable exception. | Broader SME class admits medium firms; applicable competition product; outside band; exception removes the size restriction; or required fact unproven. Merely additionally admitting a qualifying nonprofit does not erase the remaining restriction on ordinary firms. | 공고문 and qualification attachments | 세부품명번호목록, 입찰추정가격; friendly exact CSV row including conditions/provenance | SME decree 2-2/2-3, decree 21/20 |
| v16 | In the v15 band, the required SME restriction or an actually applicable article2-3 exception is absent across the complete notice. | Competition/uncertain applicability, required restriction exists, or an applicable exception exists. Exceptions include failed SME tender; necessary nonprofit participation for the enumerated service classes; another statute's priority/direct/designated contract; specific performance/technology/quality making priority procurement infeasible; or equivalent ministerial notice reason. | All supplied documents for absence and exception check | 세부품명번호목록, 입찰추정가격; friendly exact CSV row including conditions/provenance; exception reason from supplied notice/organizer fact | SME decree 2-2/2-3, decree 21/20 |
| v17 | A non-competition good/service below KRW100m admits medium enterprises through an SME/broad `중·소기업` qualification without the article2-2 eligible-pool/failed-tender allowance or another applicable article2-3 exception. | Small/micro-enterprise-only restriction is the normal class; outside band; competition product; applicable explicit exception; or required fact unproven. | 공고문 and qualification attachments | 세부품명번호목록, 입찰추정가격; friendly exact CSV row including conditions/provenance | SME decree 2-2(1)(1)/2-3, decree 21/20 |
| v18 | In the below-KRW100m non-competition band, required small/micro-enterprise restriction or an actually applicable article2-2/2-3 exception is absent across the complete notice. | Competition/uncertain applicability, condition exists, or an applicable exception exists. A mandatory eligibility certificate outside a qualification heading is not ignored; evaluation/template/background mention alone is not a restriction. | All supplied documents for absence and exception check | 세부품명번호목록, 입찰추정가격; friendly exact CSV row including conditions/provenance; exception reason from supplied notice/organizer fact | SME decree 2-2(1)(1)/2-3, decree 21/20 |
| v19 | A supply/technical-support undertaking is an actual pre-bid or pre-proposal submission requirement, rather than post-award/contract/delivery document. | Generic document list; contract/delivery stage; time/purpose unclear. | 공고문, 규격서, 과업지시서, 제안요청서 | 업무구분, 계약방법 | decree 12/13, rule 17, limitation guide |
| v20 | Actual SW project is in the relevant amount/large-enterprise band and the required participation limit or explicit statutory exception is absent across complete notice. | SW registration/wording alone; band or exception unknown; condition present. | All supplied documents for absence check | 정보화사업여부, 업무구분, 입찰추정가격, 긴급공고여부; any re-notice fact must come from notice text because the organizer baseline metadata has no dedicated field | SW Act/guideline appendix |
| v21 | A minimum contract-participation share required of each joint-contract member falls outside the method/profile rule: national joint performance ordinarily10%, specified KRW100bn-or-more chapter6/8 construction5%, prime-contractor management5%; local ordinarily5%. | National divided performance does not inherit the10% minimum; local divided performance or cross-statute trade consortium has no minimum; expressly justified ±20% adjustment (local4–6%) applies; or the number is representative/local-firm/discipline performance share rather than every member's minimum. | 공고문, 공동수급 협정/attachments | 적용계약법, 공동도급구성방식, 입찰추정가격 | national/local joint-contract guide |
| v22 | In negotiated contract, non-attendance at briefing explicitly bars proposal/bid participation. | Briefing notice, recommendation, optional attendance, material distribution, or non-negotiated contract. | 공고문, 제안요청서 | 낙찰방법, 계약방법 | decree 43 |
| v23 | In a local negotiated contract, test three distinct statutory relations without substituting one for another: announcement→proposal deadline uses the price-band 40/20/10-day period (urgent/re-notice 10 days); when a proposal-request briefing is held, briefing→proposal deadline uses the same price-band period and announcement→briefing separately uses 7 days. Each period is counted from the day before its statutory endpoint as the source states. | National/non-negotiated; price-bid/opening/evaluation date substituted for proposal deadline or briefing; no briefing means no announcement→briefing test; missing role/date/price-band/urgent-or-re-notice fact. | 공고문, 제안요청서 | 적용계약법, 낙찰방법, 입찰추정가격, 공고게시일자, 긴급공고여부; briefing/proposal deadline and re-notice facts must come from notice text because they have no dedicated organizer baseline metadata field | local decree 35, award guide chapter 7 section 3 |
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
