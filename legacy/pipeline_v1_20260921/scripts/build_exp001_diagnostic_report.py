#!/usr/bin/env python3
"""Build the canonical artifact input for the EXP-001 diagnostic report."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _source(
    source_id: str,
    label: str,
    path: str,
    *,
    sql: str | None = None,
    tables_used: list[str] | None = None,
) -> dict[str, Any]:
    source: dict[str, Any] = {"id": source_id, "label": label, "path": path}
    if sql is not None:
        source["query"] = {
            "engine": "duckdb",
            "language": "sql",
            "sql": sql,
            "description": "Reproduce the bounded snapshot used by this report.",
            "tables_used": tables_used or [path],
        }
    return source


def build_artifact(diagnostics: dict[str, Any], free_summary: dict[str, Any]) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat()
    per_item = diagnostics["per_item"]
    weakest_items = sorted(per_item, key=lambda row: (row["f1"], row["item"]))[:8]
    representative_items = [
        next(row for row in per_item if row["item"] == item)
        for item in ("v22", "v3", "v13", "v10")
    ]
    largest_gaps = sorted(
        per_item,
        key=lambda row: abs(row["predicted_positive"] - row["gold_positive"]),
        reverse=True,
    )[:8]
    positive_counts = [
        {
            "item": row["item"],
            "series": series,
            "count": row[field],
            "f1": row["f1"],
            "true_positive": row["true_positive"],
            "false_positive": row["false_positive"],
            "false_negative": row["false_negative"],
        }
        for row in largest_gaps
        for series, field in (("Gold positive", "gold_positive"), ("Predicted positive", "predicted_positive"))
    ]
    summary = [{
        "macro_f1": diagnostics["macro_f1"],
        "full_input_rate": diagnostics["input"]["records_fully_in_budget_rate"],
        "gold_evidence_context_rate": diagnostics["input"]["gold_evidence_in_context_rate"],
        "visible_evidence_recall": diagnostics["input"]["visible_gold_evidence_recall"],
        "completion_limit_share": diagnostics["output"]["max_completion_limit_share"],
        "free_success_rate": free_summary["successes"] / free_summary["requested"],
    }]
    sources = [
        _source(
            "diagnostics",
            "EXP-001 reproducible diagnostics",
            "outputs/exp-001-first-submission/diagnostics.json",
            sql="SELECT * FROM read_json_auto('outputs/exp-001-first-submission/diagnostics.json')",
        ),
        _source(
            "free_smoke",
            "Free-route smoke checkpoint and failure log",
            "outputs/exp-001-free-smoke/predictions.jsonl",
            sql=(
                "SELECT 'success' AS status, count(*) AS notices "
                "FROM read_json_auto('outputs/exp-001-free-smoke/predictions.jsonl') "
                "UNION ALL SELECT 'failure', count(*) "
                "FROM read_json_auto('outputs/exp-001-free-smoke/failures.json')"
            ),
            tables_used=[
                "outputs/exp-001-free-smoke/predictions.jsonl",
                "outputs/exp-001-free-smoke/failures.json",
            ],
        ),
        _source(
            "competition_rules",
            "Competition rules and architecture notes",
            "docs/project_description.md",
        ),
    ]
    return {
        "surface": "report",
        "manifest": {
            "version": 1,
            "surface": "report",
            "title": "EXP-001 Baseline Diagnostic",
            "description": "Why the first local baseline scored 0.2204 and what the free route changes.",
            "generatedAt": generated_at,
            "cards": [
                {
                    "id": "macro_f1",
                    "description": "Mean positive-class F1 across v1-v24 on 200 labeled dev notices.",
                    "dataset": "summary",
                    "sourceId": "diagnostics",
                    "metrics": [{"label": "Local macro F1", "field": "macro_f1", "format": "number"}],
                },
                {
                    "id": "full_input",
                    "description": "Share of dev notices whose supplied document text fits within 4,000 characters.",
                    "dataset": "summary",
                    "sourceId": "diagnostics",
                    "metrics": [{"label": "Full document input", "field": "full_input_rate", "format": "percent"}],
                },
                {
                    "id": "output_headroom",
                    "description": "Largest observed completion as a share of the 2,500-token limit.",
                    "dataset": "summary",
                    "sourceId": "diagnostics",
                    "metrics": [{"label": "Max output budget used", "field": "completion_limit_share", "format": "percent"}],
                },
                {
                    "id": "free_success",
                    "description": "Successfully checkpointed notices in the five-notice free-route smoke test.",
                    "dataset": "summary",
                    "sourceId": "free_smoke",
                    "metrics": [{"label": "Free smoke success", "field": "free_success_rate", "format": "percent"}],
                },
            ],
            "charts": [
                {
                    "id": "f1_contrast",
                    "title": "Positive-class F1 across representative items",
                    "subtitle": "Best item, next-best item, dominant over-prediction item, and a zero-F1 absence item.",
                    "type": "bar",
                    "dataset": "representative_items",
                    "sourceId": "diagnostics",
                    "encodings": {
                        "x": {"field": "item", "type": "ordinal", "label": "Item"},
                        "y": {"field": "f1", "type": "quantitative", "label": "F1", "format": "percent"},
                        "tooltip": [
                            {"field": "gold_positive", "type": "quantitative", "label": "Gold positive"},
                            {"field": "predicted_positive", "type": "quantitative", "label": "Predicted positive"},
                        ],
                    },
                    "valueFormat": "percent",
                    "layout": "full",
                }
            ],
            "tables": [
                {
                    "id": "item_f1",
                    "title": "Eight lowest positive-class F1 items",
                    "subtitle": "Labeled dev set, 200 notices; exact values for all 24 items remain in the diagnostic source.",
                    "dataset": "weakest_items",
                    "sourceId": "diagnostics",
                    "defaultSort": {"field": "f1", "direction": "asc"},
                    "density": "spacious",
                    "layout": "full",
                    "columns": [
                        {"field": "item", "label": "Item", "type": "text"},
                        {"field": "gold_positive", "label": "Gold +", "format": "number"},
                        {"field": "predicted_positive", "label": "Predicted +", "format": "number"},
                        {"field": "f1", "label": "F1", "format": "percent"},
                    ],
                },
            ],
            "sources": sources,
            "blocks": [
                {"id": "title", "type": "markdown", "body": "# EXP-001 Baseline Diagnostic"},
                {
                    "id": "technical_summary",
                    "type": "markdown",
                    "sourceId": "diagnostics",
                    "body": "## The 0.2204 score is primarily a judgment-definition failure, not an output truncation failure\n\n- All 200 responses contained a parseable 24-item judgment. The largest completion used 931 of 2,500 tokens, so output truncation is not supported.\n- Input truncation is real: only 8 of 200 notices fit fully inside the 4,000-character document budget. However, 47 of 54 labeled evidence spans were visible, and recall within those visible cases was only 44.7%. More context alone cannot explain the majority of misses.\n- v13 produced 112 positives against 6 gold positives, while eight items scored zero F1. The prompt gives short item names but not operational decision boundaries, so Gemma confuses related procurement restrictions.\n- Evidence validity is a weak confidence signal. A valid substring proves that text exists, not that it constitutes the named violation.",
                },
                {"id": "metrics", "type": "metric-strip", "cardIds": ["macro_f1", "full_input", "output_headroom", "free_success"]},
                {
                    "id": "f1_finding",
                    "type": "markdown",
                    "sourceId": "diagnostics",
                    "body": "## Performance failure is broad, with a small number of exceptions\n\nv22 reached 0.889 F1, but v10, v11, v12, v14-v18, and v20 scored zero. This is not a single-label incident: related amount, product-classification, and absence-detection conditions are being collapsed or ignored. The next experiment must define mutually exclusive decision conditions rather than merely expanding the item-name list.",
                },
                {"id": "f1_chart", "type": "chart", "chartId": "f1_contrast", "layout": "full"},
                {"id": "f1_table", "type": "table", "tableId": "item_f1", "layout": "full"},
                {
                    "id": "count_finding",
                    "type": "markdown",
                    "sourceId": "diagnostics",
                    "body": "## v13 over-prediction dominates false positives while several items are rarely emitted\n\nv13 generated 108 false positives because ordinary small-business eligibility language was treated as a violation without first establishing that the product is a designated competitive product. v24 similarly over-predicted metadata discrepancies. In the opposite direction, the model almost never emitted the five absence-detection violations from partial documents.",
                },
                {
                    "id": "definitions",
                    "type": "markdown",
                    "sourceId": "diagnostics",
                    "body": "## What was measured\n\nThe cohort is all 200 labeled dev notices. The headline metric is the unweighted mean of 24 positive-class F1 values. Input coverage checks whether gold evidence spans occur in the exact 4,000-character context sent to the model. This evidence analysis covers 54 non-absence positive cases with non-empty gold evidence; it does not represent all positive labels.",
                },
                {
                    "id": "method",
                    "type": "markdown",
                    "body": "## The diagnostic separates input, generation, and decision errors\n\nInput coverage is reconstructed with the production prompt builder. Output completeness is measured from the stored raw responses and token usage. Item-level TP, FP, FN, and F1 are recomputed directly from the submission-shaped rows and official dev labels. Free-route behavior is measured in a separate five-notice checkpoint so it cannot alter the paid EXP-001 baseline.",
                },
                {
                    "id": "architecture",
                    "type": "markdown",
                    "sourceId": "competition_rules",
                    "body": "## One Gemma call is efficient, but judgment and evidence should not share one decision contract\n\nMultiple calls are allowed; every notice only has to complete at least one real Gemma call. Calling once per item is infeasible for 1,853 test notices, but a selective second pass is permitted. The recommended design is: first produce 24 judgments with item-specific conditions and candidate spans; then let Python resolve exact substrings; use a second Gemma pass only for ambiguous or evidence-missing positives. A judgment-only free ablation was attempted but all three attempts received provider 429, so its score impact remains unverified.",
                },
                {
                    "id": "free_route",
                    "type": "markdown",
                    "sourceId": "free_smoke",
                    "body": "## The free model route is API-compatible only after disabling provider parameter filtering\n\nWith `require_parameters=true`, OpenRouter returned 404 because no free endpoint matched the requested parameter filter. With the filter disabled, requests reached Google AI Studio, but only 1 of 5 notices completed; the rest exhausted retries on provider 429. The one complete notice matched the paid result on all 24 labels and evidence cells. One additional response matched 23 of 24 paid labels but ignored the nested schema, so equivalence is suggestive—not established.",
                },
                {
                    "id": "limitations",
                    "type": "markdown",
                    "body": "## Limits and uncertainty\n\nThe dev set is explicitly not representative of private-test prevalence. Only 54 positive cases contain gold evidence suitable for context-visibility analysis. The old paid run did not store `finish_reason`; token headroom and complete parsing are strong evidence against truncation but cannot recover the provider's original stop signal. Free-versus-paid quality has only one valid paired completion because of provider 429s.",
                },
                {
                    "id": "next_steps",
                    "type": "markdown",
                    "body": "## Recommended next steps\n\n1. Keep the free model configuration and retry only small checkpoints until provider availability stabilizes; do not launch 200 records at the observed success rate.\n2. Build EXP-002 around explicit per-item decision conditions, especially the v12-v18 product/amount hierarchy and v24 field-by-field comparison.\n3. Replace first-document truncation with a token-budgeted selector that preserves every document type and metadata; target the 32,768-token evaluation sequence budget after reserving structured-output tokens. The baseline's 16,384 setting is not the evaluation limit.\n4. Test judgment-only first-pass versus joint output on the same 20-40 notices before adopting a two-pass pipeline.\n5. Preserve Python exact-substring resolution; do not use missing evidence as a hard classification gate.",
                },
                {
                    "id": "questions",
                    "type": "markdown",
                    "body": "## Questions for the next experiment\n\n- How much of the score gain comes from decision definitions versus additional context?\n- Can candidate sentence retrieval cover absence-detection prerequisites without reading every character?\n- What free-provider success rate and latency are sustainable at different times of day?\n- Which predictions merit a selective second Gemma pass under the two-hour limit?",
                },
            ],
        },
        "snapshot": {
            "version": 1,
            "generatedAt": generated_at,
            "status": "ready",
            "datasets": {
                "summary": summary,
                "per_item": per_item,
                "representative_items": representative_items,
                "weakest_items": weakest_items,
                "positive_counts": positive_counts,
            },
        },
        "sources": sources,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--diagnostics", default="outputs/exp-001-first-submission/diagnostics.json"
    )
    parser.add_argument("--free-dir", default="outputs/exp-001-free-smoke")
    parser.add_argument("--output", default="outputs/exp-001-diagnostic/artifact.json")
    args = parser.parse_args()

    diagnostics = json.loads(Path(args.diagnostics).read_text(encoding="utf-8"))
    free_dir = Path(args.free_dir)
    successes = sum(
        1 for line in (free_dir / "predictions.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()
    )
    failures = json.loads((free_dir / "failures.json").read_text(encoding="utf-8"))
    artifact = build_artifact(
        diagnostics,
        {"requested": successes + len(failures), "successes": successes, "failures": len(failures)},
    )
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
