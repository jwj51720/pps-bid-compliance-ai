#!/usr/bin/env python3
"""Create a human-review pack for baseline prompt observability."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data import load_records
from src.prompt_observability import ITEMS, audit_prompt_observability


def markdown(report: dict) -> str:
    lines = [
        "# Baseline prompt observability audit",
        "",
        "Gold labels/evidence are used only to evaluate the already-built 4,000-character context. "
        "They are not used to create a prompt, rule, or retrieval query.",
        "",
        "## Overall",
        "",
    ]
    for key, value in sorted(report["overall"].items()):
        lines.append(f"- {key}: {value}")
    lines.extend([
        "",
        "## Per item",
        "",
        "| item | positive | source visible | outside 4k | no gold evidence | absence scope incomplete |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for item in ITEMS:
        row = report["per_item"][item]
        lines.append(
            f"| {item} | {row.get('positive', 0)} | {row.get('source_visible', 0)} | "
            f"{row.get('source_outside_4k', 0)} | {row.get('positive_without_gold_evidence', 0)} | "
            f"{row.get('absence_requires_full_scope', 0)} |"
        )
    lines.extend(["", "## Review cases", ""])
    for row in report["rows"]:
        if row["observability"] not in {"source_outside_4k", "absence_requires_full_scope"}:
            continue
        lines.append(f"### {row['id']} / {row['item']} — {row['observability']}")
        lines.append("")
        lines.append(
            f"- documents: {', '.join(row['document_types'])}; "
            f"truncated: {row['context_truncated']}; omitted: {row['context_has_omitted_documents']}"
        )
        if row.get("source_document_type"):
            lines.append(f"- gold source: {row['source_document_type']}:{row['source_document_id']}")
        if row.get("gold_evidence"):
            lines.append(f"> {row['gold_evidence']}\n")
        else:
            lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", default="data/raw/open/dev.jsonl.gz")
    parser.add_argument("--labels", default="data/raw/open/dev_labels.csv")
    parser.add_argument("--context-chars", type=int, default=4000)
    parser.add_argument("--output-dir", default="outputs/prompt-observability-s1")
    args = parser.parse_args()
    records = load_records(args.records)
    with Path(args.labels).open(encoding="utf-8", newline="") as handle:
        labels = {row["id"]: row for row in csv.DictReader(handle)}
    report = audit_prompt_observability(records, labels, args.context_chars)
    destination = Path(args.output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (destination / "report.md").write_text(markdown(report), encoding="utf-8")
    print(destination / "report.md")
    print(json.dumps(report["overall"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
