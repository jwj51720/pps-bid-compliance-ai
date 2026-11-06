# INC-033: Predicate-Ready Source-Fact Audit

## Hypothesis

Some labels require a legal predicate over explicit facts rather than broad
semantic classification: v3 compares a required performance amount to the
procurement amount, v19 distinguishes a supplier-confirmation stage, v21 reads
a joint-contract share, and v23 relates local negotiated procurement, a site
briefing and time. If complete source paragraphs can expose these facts with
high recall and a manageable negative candidate rate, a future deterministic
predicate may be legally reviewed. If not, no rule or prompt wrapper is
authorized.

## Frozen extractor

The extractor reads every original document in full and emits source paragraph
blocks only when explicit marker classes occur:

- v3: `실적` plus an amount expression in one paragraph;
- v19: `확약서`/`공급확약` plus an explicit submission/contract/bid-stage
  expression in one paragraph;
- v21: `공동`/`공동수급` plus an explicit percentage in one paragraph;
- v23: `현장설명`/`현장 설명회` plus an explicit date/time expression in one
  paragraph, and separately records the unmodified organizer metadata regime.

Paragraphs are delimited by source line breaks or blank-line blocks; no
character-radius window, dev-selected cue, numerical threshold, or model call
is used. The source block is retained unchanged with document ID and offset.

## Audit and gates

Dev labels are used only to report candidate recall and negative candidate
rate. The script never emits a violation label. A later predicate branch is
permitted only when an item has 100% gold-positive candidate coverage, the
candidate facts have source provenance, and a complete cited legal predicate
can be written without a dev-derived number or exception. A candidate rate in
negatives is a review burden, not a classifier score.

## One permitted segmentation repair

The initial paragraph audit may treat a source document with no blank lines as
one enormous block. INC-033R therefore compares the same frozen marker pairs
on each unchanged nonempty source line. This is a source-format boundary, not
a character radius, numerical threshold, cue change, or label rule. It is
accepted only if v3/v21 retain complete positive candidate coverage while the
negative candidate rate declines; otherwise paragraph-level candidates remain
an audit artifact and no predicate branch proceeds.
