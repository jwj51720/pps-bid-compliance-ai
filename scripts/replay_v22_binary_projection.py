#!/usr/bin/env python3
"""Replay stored v22 observations through the card-defined binary reducer."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pps_ai.decisions.v22_briefing import decide_v22_briefing
from src.pps_ai.native_v22_diagnostic import (
    load_native_v22_config, parse_v22_response, prepare_native_v22_panel,
)
from src.pps_ai.preflight import compare_manifests
from src.pps_ai.runtime.openrouter import atomic_json


def _resolved(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    manifest_path = args.config.resolve()
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != "clean-native-v22-diagnostic":
        raise ValueError("not a native v22 replay manifest")
    if raw.get("run") != {"mode": "offline_response_replay"}:
        raise ValueError("v22 replay mode differs")
    diff = compare_manifests(manifest_path, ROOT)
    if diff["status"] != "PASS":
        raise ValueError("v22 replay manifest diff failed")
    base_path = _resolved(raw["experiment"]["base_config"])
    base = load_native_v22_config(base_path, ROOT)
    _, views, source_preflight = prepare_native_v22_panel(base)
    response_dir = _resolved(raw["data"]["responses_path"])
    if not response_dir.is_dir():
        raise FileNotFoundError(response_dir)
    with _resolved(raw["data"]["labels_path"]).open(encoding="utf-8", newline="") as handle:
        gold = {row["id"]: int(row["v22"]) for row in csv.DictReader(handle)}

    counts: Counter[str] = Counter()
    rows = []
    for notice_id, view in views.items():
        response_path = response_dir / f"{notice_id}.json"
        if not response_path.is_file():
            raise FileNotFoundError(response_path)
        observation = parse_v22_response(
            json.loads(response_path.read_text(encoding="utf-8")), view,
        )
        if not observation["valid"] or observation["axes"] is None:
            raise ValueError(f"{notice_id}: invalid stored observation")
        decision = decide_v22_briefing(observation["axes"])
        actual = gold[notice_id]
        counts["tp"] += int(decision == 1 and actual == 1)
        counts["fp"] += int(decision == 1 and actual == 0)
        counts["fn"] += int(decision == 0 and actual == 1)
        counts["tn"] += int(decision == 0 and actual == 0)
        counts["raw_unknown"] += int(observation["state"] == "U")
        if decision == 1 and not observation["source_ids"]:
            raise ValueError(f"{notice_id}: positive lacks exact evidence")
        rows.append({
            "id": notice_id, "gold": actual, "v22": decision,
            "raw_state": observation["state"], "axes": observation["axes"],
            "evidence": observation["quote"] if decision == 1 else "",
            "source_ids": observation["source_ids"] if decision == 1 else [],
        })
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    denominator = 2 * tp + fp + fn
    report = {
        "status": "REPLAY", "experiment_id": raw["experiment_id"],
        "cohort": raw["evaluation"]["cohort"], "records": len(rows),
        "logical_calls": 0, "reused_responses": len(rows),
        "counts": dict(counts),
        "v22_positive_f1": 2 * tp / denominator if denominator else 0.0,
        "positive_evidence_valid": all(
            row["source_ids"] for row in rows if row["v22"] == 1
        ),
        "manifest_diff": diff, "source_preflight": source_preflight,
        "per_notice": rows,
    }
    output = _resolved(raw["output_dir"]) / raw["evaluation"]["cohort"]
    atomic_json(output / "run_report.json", report)
    print(json.dumps({key: report[key] for key in (
        "status", "cohort", "records", "logical_calls", "reused_responses",
        "counts", "v22_positive_f1", "positive_evidence_valid",
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
