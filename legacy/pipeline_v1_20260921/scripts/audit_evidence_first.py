#!/usr/bin/env python3
"""Measure whether source-unit evidence retrieval is structurally plausible.

This is E0 of ``docs/evidence_first_research_plan.md``.  It evaluates gold
evidence visibility but does not create candidate contexts or invoke a model.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data import load_records
from src.evidence_audit import locate_evidence, paragraph_spans, spans_covering
from src.prompt import build_official_baseline_context

ITEMS = tuple(f"v{index}" for index in range(1, 25))


def _summary(values: list[int]) -> dict[str, int | float]:
    if not values:
        return {"count": 0, "median": 0, "p90": 0, "max": 0}
    ordered = sorted(values)
    return {
        "count": len(values),
        "median": ordered[(len(ordered) - 1) // 2],
        "p90": ordered[min(len(ordered) - 1, int((len(ordered) - 1) * 0.9))],
        "max": ordered[-1],
    }


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def audit(records: list[dict[str, Any]], labels: dict[str, dict[str, str]], context_chars: int) -> dict[str, Any]:
    per_item: dict[str, Counter[str]] = {item: Counter() for item in ITEMS}
    document_types: Counter[str] = Counter()
    match_modes: Counter[str] = Counter()
    notice_oracle_chars: list[int] = []
    notice_oracle_units: list[int] = []
    source_unresolved: list[dict[str, str]] = []
    rows: list[dict[str, Any]] = []

    for record in records:
        label = labels[record["id"]]
        context = build_official_baseline_context(record, context_chars)
        spans = paragraph_spans(record)
        oracle_keys: set[tuple[str, int, int]] = set()
        for index, item in enumerate(ITEMS, 1):
            if int(label[item]) != 1:
                continue
            metrics = per_item[item]
            metrics["positive"] += 1
            evidence = label[f"e{index}"]
            if not evidence.strip():
                metrics["blank_evidence"] += 1
                rows.append({"id": record["id"], "item": item, "kind": "blank_evidence"})
                continue
            metrics["nonempty_evidence"] += 1
            location = locate_evidence(record, evidence)
            if location is None:
                metrics["source_unresolved"] += 1
                source_unresolved.append({"id": record["id"], "item": item})
                rows.append({"id": record["id"], "item": item, "kind": "source_unresolved"})
                continue
            metrics["source_resolved"] += 1
            document_types[location.document_type] += 1
            match_modes[location.match_mode] += 1
            visible = location.source_text in context
            metrics["visible_in_4k"] += int(visible)
            units = spans_covering(location, spans)
            metrics["paragraph_reachable"] += int(bool(units))
            for unit in units:
                oracle_keys.add((unit.doc_id, unit.start, unit.end))
            rows.append({
                "id": record["id"], "item": item, "kind": "resolved",
                "document_type": location.document_type,
                "match_mode": location.match_mode,
                "visible_in_4k": visible,
                "paragraph_count": len(units),
            })
        chosen = [span for span in spans if (span.doc_id, span.start, span.end) in oracle_keys]
        if chosen:
            notice_oracle_chars.append(sum(len(span.text) for span in chosen) + 2 * (len(chosen) - 1))
            notice_oracle_units.append(len(chosen))

    item_report: dict[str, dict[str, Any]] = {}
    totals: Counter[str] = Counter()
    for item, metrics in per_item.items():
        totals.update(metrics)
        item_report[item] = {
            **dict(metrics),
            "four_k_evidence_recall": _rate(metrics["visible_in_4k"], metrics["source_resolved"]),
            "paragraph_reachability": _rate(metrics["paragraph_reachable"], metrics["source_resolved"]),
        }
    return {
        "audit": "evidence_first_e0",
        "scope": {
            "records": len(records),
            "items": len(ITEMS),
            "baseline_context_chars": context_chars,
            "warning": "Gold labels/evidence are evaluation-only and were not used to construct a model input.",
        },
        "overall": {
            **dict(totals),
            "four_k_evidence_recall": _rate(totals["visible_in_4k"], totals["source_resolved"]),
            "paragraph_reachability": _rate(totals["paragraph_reachable"], totals["source_resolved"]),
            "source_unresolved_examples": source_unresolved,
            "match_modes": dict(match_modes),
            "evidence_document_types": dict(document_types),
            "oracle_paragraph_pack_characters": _summary(notice_oracle_chars),
            "oracle_paragraph_pack_units": _summary(notice_oracle_units),
        },
        "per_item": item_report,
        "rows": rows,
    }


def _markdown(report: dict[str, Any]) -> str:
    overall = report["overall"]
    lines = [
        "# E0 — 원문 증거 관측성 audit",
        "",
        "이 문서는 gold evidence를 **평가용으로만** 사용한 offline 관측 결과다. 이 결과로 retrieval query나 model prompt를 만들지 않았다.",
        "",
        "## 전체 결과",
        "",
        f"- positive cells: {overall.get('positive', 0)}",
        f"- nonempty evidence: {overall.get('nonempty_evidence', 0)}",
        f"- blank evidence: {overall.get('blank_evidence', 0)}",
        f"- source unresolved: {overall.get('source_unresolved', 0)}",
        f"- EXP120 4,000자 context evidence recall: {overall['four_k_evidence_recall']}",
        f"- paragraph reachability: {overall['paragraph_reachability']}",
        f"- oracle paragraph-pack characters: {overall['oracle_paragraph_pack_characters']}",
        "",
        "## 항목별 결과",
        "",
        "| item | positive | nonempty | blank | unresolved | 4k recall | paragraph reach |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item, row in report["per_item"].items():
        lines.append(
            f"| {item} | {row.get('positive', 0)} | {row.get('nonempty_evidence', 0)} | "
            f"{row.get('blank_evidence', 0)} | {row.get('source_unresolved', 0)} | "
            f"{row['four_k_evidence_recall']} | {row['paragraph_reachability']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", default="data/raw/open/dev.jsonl.gz")
    parser.add_argument("--labels", default="data/raw/open/dev_labels.csv")
    parser.add_argument("--context-chars", type=int, default=4000)
    parser.add_argument("--output-dir", default="outputs/evidence-first-e0")
    args = parser.parse_args()
    if args.context_chars <= 0:
        raise ValueError("--context-chars must be positive")
    records = load_records(args.records)
    with Path(args.labels).open(encoding="utf-8", newline="") as handle:
        labels = {row["id"]: row for row in csv.DictReader(handle)}
    if {record["id"] for record in records} != set(labels):
        raise ValueError("record IDs and label IDs differ")
    report = audit(records, labels, args.context_chars)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "report.md").write_text(_markdown(report), encoding="utf-8")
    print(output_dir / "report.md")
    print(json.dumps(report["overall"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
