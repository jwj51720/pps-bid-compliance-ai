# INC-016: v20 Predicate-Candidate Audit

INC-015 showed that a single final v20 question lets law context cause
applicability leakage. This offline audit separates two source-location tasks:
potential SW-business applicability and a potential declaration that the
large-company participation restriction applies (or its basis). The extractor
does not determine either predicate and cannot emit v20.

The relevant preflight checks are (1) coverage of labeled v20 positives by
the conjunction `SW candidate AND no declaration candidate`, and (2) the
candidate rate among negatives. Even a high-rate candidate is only admissible
as fixed evidence for an LLM predicate review, never as an automatic decision.

If this audit has full positive coverage, the next paid experiment will compare
the INC-015 control with a structured Gemma diagnostic that emits source-backed
`sw_applicability`, `declaration_status`, and `exception_status` fields. Only
after a separately declared conservative merge and full-dev evaluation may it
be considered for v20.

## Result

The candidate conjunction covered 5/5 positives. Its negative rate was 13.85%
(27/195), compared with 14.87% for the SW candidate alone; declaration
candidates appeared in only 2/195 negatives and none of the positives. The
extractor is therefore useful as an audit/retrieval signal, but the 27
candidate negatives prohibit automatic v20 labeling. It passed only the
preflight gate for INC-017's all-document predicate review.
