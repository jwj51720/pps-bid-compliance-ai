# INC-064: Rationale-to-Source Retrieval Gate

## Question

Can a model first state the *legal/factual issue* in a full notice, without
being asked for an exact quotation or a binary decision, and can that memo
retrieve the organizer's unchanged evidence line better than the item-table
criterion alone?  This is the provenance-preserving route proposed in the
idea note.  It is an evidence/attention gate only; no generated memo becomes
evidence or changes any label.

## Why this is distinct

INC-027 rejected a global fact-ledger followed by 24 judgments.  INC-049
rejected criterion/metadata-to-line retrieval as a *label gate*.  Neither
tests an item-specific legal reading of a complete notice as the retrieval
query.  INC-062 shows a direct locator can select a line after an upstream
positive is fixed, but does not test whether a free legal rationale can be
mapped back to source without asking it to copy text.

## Frozen scope and control

The cohort is every dev-200 positive with organizer nonempty evidence for v4
or v7 (not a selected subset).  These are the two remaining high-loss,
law-resolved, source-observable items from INC-057; they are used solely to
measure whether a route can retain known evidence.  The comparator is the
same BGE-M3 ranking query made from the item table, item-linked law text, and
notice metadata.  Both representations rank the identical complete,
unchanged source-line set of the same notice.

For each cohort cell, one Gemma call receives metadata, the complete ordered
notice, the exact item definition and its organizer-linked legal source text.
It returns a concise Korean ``memo`` describing only the factual and legal
question that should be checked in the source.  It must not output a label,
quote, line ID, or invented factual conclusion.  The source line index is
formed mechanically from every intact original line; no document is dropped,
no character-derived selection rule exists, and no retrieved line can alter a
label in this experiment.

``max_tokens=256`` is an API resource reservation for a single memo, not a
semantic or character threshold.  The evaluation reports the full rank of
the organizer evidence and the standard rank curve (1, 3, 5, 10, 20), rather
than choosing a rank cutoff as a prediction policy.

## Validity and decision rule

- Any malformed memo response is a failed cell; it is not retried with a
  changed prompt or repaired into a label.
- BGE uses the permitted `BAAI/bge-m3` endpoint only.  Each source line and
  query is recorded with source and prompt hashes.
- This route advances to a subsequent, separately preregistered *judgment*
  pilot only if it gives paired rank improvement over the criterion control
  without any cell losing the organizer evidence entirely.  A higher score
  at one hand-picked rank is explicitly insufficient.
- If this gate fails, no source-candidate adjudication or score claim follows;
  it closes the rationale-to-retrieval topology as an evidence improvement.

The maximum remote spend is $0.15.  The run is checkpointed per cell and
records raw completions and reported API usage.
