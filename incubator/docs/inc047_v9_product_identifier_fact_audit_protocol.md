# INC-047: v9 Product-Identifier Fact Audit

## Question

v9 is a product-specification issue but its positive evidence spans notices and
specifications. This audit tests document-type-independent *identifier facts*,
not a brand blacklist or automatic violation rule.

## Frozen fact forms

On every unchanged source line, retain a candidate when it contains at least
one structural product-identifier form: an explicit manufacturer/model/chipset
field label; a Latin token with an attached digit; or an all-caps hyphenated
technical designation. Also retain line provenance and document type. These
forms describe typography, not a learned vocabulary; no specific brand, source
window, popularity frequency, or label-derived token is added.

## Gate

Report v9 positive candidate coverage, negative activation, document
distribution, and the candidate facts for every positive. A future method must
still distinguish a binding specification from a descriptive/equivalent-product
mention using organizer-law context. Candidate presence alone is never v9=1.
