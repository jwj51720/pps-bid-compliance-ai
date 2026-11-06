#!/usr/bin/env python3
"""Compare two exact-ID experiment outputs without hiding off-target drift."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.schema import ITEMS


def _read_csv_by_id(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    result = {row["id"]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"duplicate IDs in {path}")
    return result


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _per_item(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    result = {row["item"]: row for row in rows}
    if set(result) != set(ITEMS):
        raise ValueError(f"per-item metrics do not cover v1..v24: {path}")
    return result


def compare(
    base_dir: Path,
    candidate_dir: Path,
    labels_path: Path,
    focus_items: tuple[str, ...],
) -> dict[str, Any]:
    if any(item not in ITEMS for item in focus_items):
        raise ValueError("focus items must be v1..v24")
    if len(set(focus_items)) != len(focus_items):
        raise ValueError("focus items must not repeat")

    base = _read_csv_by_id(base_dir / "submission.csv")
    candidate = _read_csv_by_id(candidate_dir / "submission.csv")
    labels = _read_csv_by_id(labels_path)
    if set(base) != set(candidate):
        raise ValueError("base and candidate IDs differ")
    if not set(base) <= set(labels):
        raise ValueError("labels do not cover the compared IDs")

    base_meta = _read_json(base_dir / "run_meta.json")
    candidate_meta = _read_json(candidate_dir / "run_meta.json")
    cohort_checks = {
        "input_sha256_equal": base_meta.get("input_sha256") == candidate_meta.get("input_sha256"),
        "labels_sha256_equal": base_meta.get("labels_sha256") == candidate_meta.get("labels_sha256"),
        "input_count_equal": base_meta.get("input_count") == candidate_meta.get("input_count"),
        "fast_panel_equal": (
            base_meta.get("fast_panel_ids_path") == candidate_meta.get("fast_panel_ids_path")
        ),
    }
    if not all(cohort_checks.values()):
        raise ValueError(f"run cohorts are not comparable: {cohort_checks}")

    base_metrics = _read_json(base_dir / "metrics.json")
    candidate_metrics = _read_json(candidate_dir / "metrics.json")
    base_items = _per_item(base_dir / "per_item_metrics.csv")
    candidate_items = _per_item(candidate_dir / "per_item_metrics.csv")
    focus = set(focus_items)
    changed: list[dict[str, Any]] = []
    for record_id in sorted(base):
        for item in ITEMS:
            before = int(base[record_id][item])
            after = int(candidate[record_id][item])
            if before == after:
                continue
            gold = int(labels[record_id][item])
            changed.append({
                "id": record_id,
                "item": item,
                "scope": "focus" if item in focus else "off_target",
                "base": before,
                "candidate": after,
                "gold": gold,
                "effect": (
                    "corrected" if before != gold and after == gold
                    else "regressed" if before == gold and after != gold
                    else "changed_but_still_wrong"
                ),
            })

    def summarize(scope: str) -> dict[str, int]:
        values = [row for row in changed if row["scope"] == scope]
        return {
            "changed": len(values),
            "corrected": sum(row["effect"] == "corrected" for row in values),
            "regressed": sum(row["effect"] == "regressed" for row in values),
            "changed_but_still_wrong": sum(
                row["effect"] == "changed_but_still_wrong" for row in values
            ),
        }

    per_item = []
    for item in ITEMS:
        before = base_items[item]
        after = candidate_items[item]
        per_item.append({
            "item": item,
            "scope": "focus" if item in focus else "off_target",
            "base": {
                key: float(before[key]) if key in {"precision", "recall", "f1"} else int(before[key])
                for key in (
                    "true_positive", "false_positive", "false_negative",
                    "precision", "recall", "f1",
                )
            },
            "candidate": {
                key: float(after[key]) if key in {"precision", "recall", "f1"} else int(after[key])
                for key in (
                    "true_positive", "false_positive", "false_negative",
                    "precision", "recall", "f1",
                )
            },
            "f1_delta": float(after["f1"]) - float(before["f1"]),
        })

    base_macro = float(base_metrics["leaderboard_metric"]["macro_f1"])
    candidate_macro = float(candidate_metrics["leaderboard_metric"]["macro_f1"])
    return {
        "base": str(base_dir),
        "candidate": str(candidate_dir),
        "labels": str(labels_path),
        "record_count": len(base),
        "focus_items": list(focus_items),
        "cohort_checks": cohort_checks,
        "macro_f1": {
            "base": base_macro,
            "candidate": candidate_macro,
            "delta": candidate_macro - base_macro,
        },
        "focus_changes": summarize("focus"),
        "off_target_changes": summarize("off_target"),
        "per_item": per_item,
        "changed_cells": changed,
    }


def _markdown(result: dict[str, Any]) -> str:
    macro = result["macro_f1"]
    lines = [
        "# Paired experiment comparison", "",
        f"- Base: `{result['base']}`",
        f"- Candidate: `{result['candidate']}`",
        f"- Records: {result['record_count']}",
        f"- Focus items: {', '.join(result['focus_items']) or '(none)'}",
        f"- Macro F1: {macro['base']:.6f} → {macro['candidate']:.6f} "
        f"({macro['delta']:+.6f})", "",
        "## Changed-cell attribution", "",
        "| Scope | Changed | Corrected | Regressed | Still wrong |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for key, label in (("focus_changes", "Focus"), ("off_target_changes", "Off-target")):
        row = result[key]
        lines.append(
            f"| {label} | {row['changed']} | {row['corrected']} | "
            f"{row['regressed']} | {row['changed_but_still_wrong']} |"
        )
    lines += ["", "## Per-item", "", "| Item | Scope | Base TP/FP/FN/F1 | Candidate TP/FP/FN/F1 | ΔF1 |", "| --- | --- | --- | --- | ---: |"]
    for row in result["per_item"]:
        before, after = row["base"], row["candidate"]
        lines.append(
            f"| {row['item']} | {row['scope']} | "
            f"{before['true_positive']}/{before['false_positive']}/{before['false_negative']}/{before['f1']:.4f} | "
            f"{after['true_positive']}/{after['false_positive']}/{after['false_negative']}/{after['f1']:.4f} | "
            f"{row['f1_delta']:+.4f} |"
        )
    lines += ["", "## Changed cells", ""]
    lines.extend(
        f"- `{row['id']}` {row['item']} ({row['scope']}): "
        f"{row['base']}→{row['candidate']}, gold={row['gold']} ({row['effect']})"
        for row in result["changed_cells"]
    )
    if not result["changed_cells"]:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", required=True)
    parser.add_argument("--candidate-dir", required=True)
    parser.add_argument("--labels", default="data/raw/open/dev_labels.csv")
    parser.add_argument("--focus-items", nargs="*", default=[])
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = compare(
        Path(args.base_dir), Path(args.candidate_dir), Path(args.labels),
        tuple(args.focus_items),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(_markdown(result), encoding="utf-8")
    print(json.dumps({key: result[key] for key in (
        "record_count", "focus_items", "cohort_checks", "macro_f1",
        "focus_changes", "off_target_changes",
    )}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
