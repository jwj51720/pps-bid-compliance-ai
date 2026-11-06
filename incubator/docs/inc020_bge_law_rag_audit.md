# INC-020: Organizer-Law BGE-M3 Retrieval Audit

This broadens the experiment program from prompt-only changes to a reusable
organizer-law retrieval layer. Every supplied law text is chunked with exact
source offsets and embedded using the competition-permitted `BAAI/bge-m3`
model through OpenRouter. Each of the 24 organizer item-table definitions,
including both national and local references, is embedded as an independent
legal query and retrieves four source chunks.

This is not a judgment experiment: retrieval chunks are fixed legal context,
not notice evidence or labels. The run preserves model, source hashes, chunk
boundaries, query text, embeddings, rankings, token usage, and estimated cost.
The next gate is a manual/structural audit that every retrieved chunk actually
supports an item-table cited law before using the index in a family-pass model
experiment.

## Result

The index contains 23 organizer law files and 1,815 chunks. It embedded
1,234,291 tokens through `baai/bge-m3` at $0.01234. The top results recover
the expected legal family for high-specificity items: v10--v13 retrieve the
competition-product/direct-production law set and v20 retrieves the software
participation guideline. The full retrieval manifest and source hashes were
used as fixed context in INC-021. This establishes BGE retrieval as a viable,
cheap source-grounded component; it does not establish a final judgment policy.
