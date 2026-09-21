# v24 source/card/validation recheck

Scope: offline evidence audit, not a new prompt experiment. No paid calls or label overrides.

Read EXP203/204 plans/results, actual incumbent v24 card and organizer item table, then
re-exported eight gold-positive notices with unchanged metadata/all source documents:

```bash
.venv/bin/python scripts/audit_product_item_sources.py --items v24 \
  --output outputs/v24-source-concordance-audit-20260915
```

Source packets/report preserve doc order, hashes and lookup facts for audit only. The script
now accepts explicit item selection; default product-item audit behavior is unchanged.
Data regression tests:7passed. Raw JSON gzip records also inspected independently of loader.

## Confirmed constraints

Fixed fast has3 v24 positives; fixed independent holdout has0. A negative-only holdout can
measure FP but cannot validate positive recall. Do not promote a v24 candidate based on fast
gain plus zero holdout FP alone, or silently invent another gold-selected paid holdout.

EXP204 already audited all8 positives and explained six with budget, competitive-contract
category, qualification region or required registered-industry facts. Two positives049/062
were unexplained on those axes. Re-read both full packets383/165lines now:

| ID | observed same-role counterpart agreement | unresolved observations |
| --- | --- | --- |
|049|budget660m/estimate600m match; regionGyeongsangnam-do matches; travel1261/1263 OR matches; two-stage specification/price matches|university-only qualification is an institution restriction, not established registered-industry mismatch; dates differ but not an organizer-listed v24 axis|
|062|budget250m/estimate227272727 consistent; competitivecategory restricted + negotiated award consistent; no qualification region and metadataN; event agency registration matches|specific institution performance restriction is v4-style fact, not itself a counterpart mismatch|

This does not establish gold error. It establishes that v24 annotation cannot currently be
reproduced for these two records using the organizer-listed four axes. Do not add dates,
institution restrictions or other v positives to v24 just to match these labels.

Both raw organizer records have exactly D0 announcement only (10055/3169 characters), and
normalized records preserve that count/text. Original dropped_doc_counts is{}, and organizer
input_completeness says complete observation. Announcements reference attachments, but those
references do not create supplied D1 documents. There is no local loader attachment-drop proof.
“All supplied sources delivered” must not be paraphrased as “all referenced real-world files available.”

## Card wording risk distinct from input delivery

Incumbent card0 condition ends `제한 문구만 있는 경우`. This is ambiguous when a qualification
restriction exists and metadata explicitly says regional/industry restrictionN: a source phrase
alone without a counterpart is not a mismatch, but an explicitN is a counterpart fact. The
phrase must not exempt an actual presence/negative-flag contradiction. This is a potential
card ambiguity, not a demonstrated performance cause; EXP204 already added presence/set
role guidance and failed to establish a useful family. Do not repeat that intervention under
a new schema or wording name without distinct evidence.

## Decision

Do not start v24-only/review/V-only paid experiment yet. Required independent positive
validation is unavailable in the fixed holdout, two of three fast positives remain unexplained,
and role-pair/proof intervention was already tried. Correct earlier broad claims: v24 input
delivery is verified, semantic labeling/concordance and generalization are not fully verified.
Continue source-first structural candidate selection on informative cohorts, not more v24
gold-driven prompt corrections. This audit does not resolve the whole performance objective.
