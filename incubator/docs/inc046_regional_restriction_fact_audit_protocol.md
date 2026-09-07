# INC-046: Regional-Restriction Legal Fact Audit

## Family scope

Audit v5--v8 as one legal applicability family without predicting any label:
v5 high-notice regional restriction, v6 low-notice city/county/district
restriction, v7 low-notice adjacent-area expansion, and v8 simultaneous
performance plus regional restriction.

## Frozen facts

From every unchanged source line retain: (a) a regional qualification anchor
(`본점`, `주된 영업소`, `소재지`, `관할구역`, `지역제한`); (b) an explicit
administrative-region token; and (c) separately, an explicit performance
amount fact. Preserve raw contract law, estimated price, region code/list, and
contract method as applicability facts. No inferred region hierarchy, notice
threshold, exception, or violation is emitted.

## Gate

Report positive evidence coverage, negative activation, region source type,
and missingness of required raw facts. This branch can advance only if every
item's positives have source/metadata facts and organizer law can resolve the
region unit and price applicability without a development-derived lookup. A
generic region word never becomes an automatic rule.
