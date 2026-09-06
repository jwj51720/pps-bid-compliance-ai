# Independent Compliance Research Incubator

This directory is a file-level quarantine for experiments on `dev-wsl`. It does
not replace the shared pipeline, submission package, or canonical root policy.
The parent pipeline is a comparator and the organizer data at
`../data/raw/open/` is read-only.

## Problem framing

For each procurement notice, decide `v1` through `v24`: whether the supplied
notice documents and 나라장터 metadata establish a particular legal violation.
The primary leaderboard metric is the unweighted mean of the 24 positive-class
F1 scores. Evidence is not part of that score, but is required for eventual
qualitative review and must be a verbatim source-document substring.

The data available locally is:

| Split | Notices | Labels | Role |
|---|---:|---|---|
| `train_unlabeled.jsonl.gz` | 20,000 | none | candidate mining and permitted self-labeling |
| `dev.jsonl.gz` | 200 | 24 labels plus evidence | offline evaluation and error analysis |
| `data/test.jsonl.gz` | 10 | none | submission-path fixture only |

Dev has only 5--8 positives per item and is intentionally not prevalence
representative. A dev improvement is therefore evidence for a hypothesis, not
proof of leaderboard calibration.

## Why a separate approach

The prior joint 24-item prompt produces a useful working baseline but conflates
different task shapes:

- document-local restrictions (`v1`--`v9`, `v19`, `v21`--`v23`),
- product, price, and exception gates (`v10`--`v18`),
- absence checks (`v10`, `v11`, `v16`, `v18`, `v20`), and
- document-to-metadata reconciliation (`v24`).

Recorded historical dev results show that simply adding full context or a broad
law bundle did not improve the baseline. EXP-120 (a 4,000-character single
Gemma call with decision cards v6) is now a public-submission-validated control:
dev-200 `0.248932`, public leaderboard `0.244317`. It is not an automatic final
policy; every successor must beat it under the milestone gates. See [research
loop](docs/experiment_loop.md), [portfolio](docs/experiment_portfolio.md), and
the [post-EXP-120 BFS milestone](docs/post_exp120_bfs_milestone.md).

## Intended architecture, if evidence supports it

```text
immutable notice + organizer legal snapshot
        |
        v
deterministic fact and cue extraction (high recall; not a learned classifier)
        |
        +--> one actual-notice Gemma triage call, required for every notice
        |
        v
candidate scheduler: active item groups + exact official-law chunks + evidence windows
        |
        v
small active-item Gemma adjudications
        |
        v
item-aware merge, absence coverage logic, v24 reconciliation, evidence validation
```

The scheduler must be conservative: a rule may request an adjudication, but a
negative rule must not silently suppress a plausible positive without a tested,
source-backed reason. Every final notice retains its actual-notice Gemma call.

## Boundary for eventual integration

Only a validated design is proposed for parent-repository integration. That
proposal must include a patch plan for a shared experiment/submission pipeline,
packaged static assets, exact token admission, offline BGE-M3 behavior if used,
2-hour runtime estimates, and a staged-zip mock test. No code in this directory
is submitted directly.
