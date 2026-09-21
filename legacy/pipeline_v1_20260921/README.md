# Legacy pipeline v1 snapshot

This directory contains the historical pipeline as it existed at Git commit
`a79603a` on 2026-09-21, immediately before the clean-room implementation.

It is preserved only for source consultation and experiment archaeology.

- It is outside the active `src/` import root.
- New code must not add this directory to `sys.path`.
- New code must not import modules from this directory.
- Historical scripts, tests, and submission entrypoints are colocated here
  because they import the historical `src.*` modules.
- Historical configs and output documentation remain at their original paths
  for provenance, but are not active clean-room manifests.

The active implementation is `src/pps_ai/`. The active experiment runner is
`scripts/run_clean_reference_baseline.py`. The active tests are those directly
under the repository's top-level `tests/` directory.

To inspect an unmodified pre-move tree, use Git commit `a79603a`; do not add a
compatibility import from the active source tree.
