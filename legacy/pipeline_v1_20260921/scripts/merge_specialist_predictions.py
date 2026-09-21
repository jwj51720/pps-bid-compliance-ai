#!/usr/bin/env python3
"""Replace declared output cells with model-owned specialist predictions."""

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

from src.config import load_config
from src.data import load_record_id_panel, load_records, select_records_by_id
from src.evaluate import evaluate_submission, write_rows
from src.submission import validate_submission, write_submission


def _read_submission(path: Path) -> tuple[list[str], dict[str, dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate IDs in {path}")
    return ids, {row["id"]: row for row in rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", required=True)
    parser.add_argument("--specialist-dir", required=True)
    parser.add_argument("--specialist-config", required=True)
    parser.add_argument("--items", nargs="+", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    items = tuple(args.items)
    invalid = [item for item in items if item not in {f"v{i}" for i in range(1, 25)}]
    if invalid:
        raise ValueError(f"invalid specialist items: {invalid}")

    base_dir = Path(args.base_dir)
    specialist_dir = Path(args.specialist_dir)
    output_dir = Path(args.output_dir)
    base_ids, base = _read_submission(base_dir / "submission.csv")
    specialist_ids, specialist = _read_submission(specialist_dir / "submission.csv")
    if base_ids != specialist_ids:
        raise ValueError("base and specialist ordered IDs differ")

    config = load_config(args.specialist_config)
    if tuple(config.active_items) != items:
        raise ValueError(
            f"specialist config active_items {config.active_items} != requested {items}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    merged_rows: list[dict[str, Any]] = []
    changed_non_specialist: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    specialist_columns = {column for item in items for column in (item, f"e{item[1:]}")}
    for record_id in base_ids:
        row: dict[str, Any] = dict(base[record_id])
        for column in specialist_columns:
            before = row[column]
            after = specialist[record_id][column]
            row[column] = after
            if before != after:
                changes.append({"id": record_id, "column": column, "base": before, "specialist": after})
        for column, value in row.items():
            if column != "id" and column not in specialist_columns and value != base[record_id][column]:
                changed_non_specialist.append({"id": record_id, "column": column})
        merged_rows.append(row)
    if changed_non_specialist:
        raise AssertionError(f"non-specialist cells changed: {changed_non_specialist[:3]}")

    write_submission(merged_rows, output_dir / "submission.csv")
    records = load_records(config.data.input_path)
    if config.data.fast_panel_ids_path:
        records = select_records_by_id(
            records, load_record_id_panel(config.data.fast_panel_ids_path)
        )
    validation = validate_submission(output_dir / "submission.csv", records)
    if not validation.passed:
        raise RuntimeError(f"merged submission validation failed: {validation.errors[:3]}")

    metrics = None
    if config.data.labels_path:
        metrics, per_item, errors = evaluate_submission(
            output_dir / "submission.csv", config.data.labels_path, records
        )
        (output_dir / "metrics.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        write_rows(output_dir / "per_item_metrics.csv", per_item)
        write_rows(output_dir / "errors.csv", errors)
    audit = {
        "base_dir": str(base_dir),
        "specialist_dir": str(specialist_dir),
        "specialist_config": args.specialist_config,
        "items": list(items),
        "record_count": len(merged_rows),
        "changed_cells": changes,
        "changed_non_specialist_cells": changed_non_specialist,
        "validation": {
            "passed": validation.passed,
            "errors": validation.errors,
            "warnings": validation.warnings,
        },
        "macro_f1": metrics["leaderboard_metric"]["macro_f1"] if metrics else None,
    }
    (output_dir / "merge_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    base_meta = json.loads((base_dir / "run_meta.json").read_text(encoding="utf-8"))
    specialist_meta = json.loads(
        (specialist_dir / "run_meta.json").read_text(encoding="utf-8")
    )
    merged_meta = {
        **base_meta,
        "experiment_id": f"{base_meta.get('experiment_id', 'base')}+specialist",
        "composition": {
            "base_dir": str(base_dir),
            "specialist_dir": str(specialist_dir),
            "specialist_items": list(items),
            "specialist_runtime_seconds": specialist_meta.get("runtime_seconds"),
            "specialist_usage": specialist_meta.get("usage"),
        },
        "macro_f1": audit["macro_f1"],
    }
    (output_dir / "run_meta.json").write_text(
        json.dumps(merged_meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"record_count": len(merged_rows), "changed_cells": len(changes), "macro_f1": audit["macro_f1"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
