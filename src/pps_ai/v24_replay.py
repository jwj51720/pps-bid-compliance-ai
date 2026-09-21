"""Offline replay of a versioned v24 reducer over immutable responses."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from .config import CleanExperimentConfig
from .decisions.v24_code_provenance_v21 import decide_v24_code_provenance_v21
from .evaluate import evaluate_rows_for_ids
from .evidence.validation import clean_final_rows
from .export import write_submission_csv
from .ingest import load_notice_records
from .preflight import compare_manifests
from .runtime.openrouter import atomic_json
from .views.v24_multi_observation import build_v24_multi_observation_view


def _read_rows(path: Path) -> dict[str, dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        result = {}
        for source in csv.DictReader(handle):
            row: dict[str, Any] = {"id": source["id"]}
            for index in range(1, 25):
                row[f"v{index}"] = int(source[f"v{index}"])
            for index in range(1, 25):
                row[f"e{index}"] = source[f"e{index}"]
            result[str(row["id"])] = row
        return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class V24ReducerReplay:
    def __init__(self, config: CleanExperimentConfig, *, cohort: str = "fast20") -> None:
        if cohort != "fast20":
            raise ValueError("C002RA is approved only for fast20 offline replay")
        self.config = config
        self.cohort = cohort
        self.output_dir = (config.output_dir / cohort).resolve()
        policy = config.raw.get("v24_policy")
        if not isinstance(policy, dict) or policy.get("module") != "native-v24-code-provenance-v2.1":
            raise ValueError("v24 code-provenance v2.1 policy is not selected")
        root = config.path.parents[2]
        self.response_dir = (root / str(policy["source_response_dir"])).resolve()
        self.previous_output_dir = (root / str(policy["previous_output_dir"])).resolve()
        self.base_output_dir = (root / str(policy["base_output_dir"])).resolve()
        self.max_axis_characters = int(policy["max_axis_characters"])

    def run(self) -> dict[str, Any]:
        manifest = compare_manifests(self.config.path, self.config.path.parents[2])
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")
        ids = set(json.loads(self.config.fast_panel_path.read_text(encoding="utf-8"))["ids"])
        records = [
            record for record in load_notice_records(self.config.input_path)
            if record.notice_id in ids
        ]
        if {record.notice_id for record in records} != ids:
            raise ValueError("fast20 input coverage differs")
        base_rows = _read_rows(self.base_output_dir / "submission.csv")
        previous_rows = _read_rows(self.previous_output_dir / "submission.csv")
        candidate: dict[str, dict[str, Any]] = {}
        observations = []
        response_ledger = []
        fallback = 0
        for record in records:
            notice_id = record.notice_id
            response_path = self.response_dir / f"{notice_id}.json"
            if not response_path.is_file():
                raise FileNotFoundError(f"missing replay response: {response_path}")
            response = json.loads(response_path.read_text(encoding="utf-8"))
            view = build_v24_multi_observation_view(
                dict(record.raw), max_axis_characters=self.max_axis_characters,
            )
            value, evidence, diagnostic = decide_v24_code_provenance_v21(
                dict(record.raw), view, response,
            )
            row = dict(base_rows[notice_id])
            row["v24"], row["e24"] = value, evidence
            candidate[notice_id] = row
            fallback += int(diagnostic["fallback"])
            observations.append({
                "id": notice_id,
                "previous_v24": previous_rows[notice_id]["v24"],
                "v24": value,
                "e24": evidence,
                "diagnostic": diagnostic,
            })
            response_ledger.append({
                "id": notice_id,
                "path": str(response_path),
                "sha256": _sha256(response_path),
                "finish_reason": response.get("finish_reason"),
            })
        rows, evidence_report = clean_final_rows(
            [dict(record.raw) for record in records], candidate,
        )
        for row in rows:
            baseline = base_rows[str(row["id"])]
            for index in range(1, 24):
                if row[f"v{index}"] != baseline[f"v{index}"]:
                    raise ValueError(f"{row['id']}/v{index}: replay changed non-owner label")
                if row[f"e{index}"] != baseline[f"e{index}"]:
                    raise ValueError(f"{row['id']}/e{index}: replay changed non-owner evidence")
        write_submission_csv(self.output_dir / "submission.csv", rows)
        atomic_json(self.output_dir / "resolved_manifest.json", self.config.raw)
        atomic_json(self.output_dir / "response_ledger.json", response_ledger)
        atomic_json(self.output_dir / "observations.json", observations)
        metrics = evaluate_rows_for_ids(rows, self.config.labels_path, ids, self.cohort)
        atomic_json(self.output_dir / "metrics.json", {self.cohort: metrics})
        changes = [
            {
                "id": row["id"],
                "before": previous_rows[str(row["id"])]["v24"],
                "after": row["v24"],
            }
            for row in rows
            if previous_rows[str(row["id"])]["v24"] != row["v24"]
        ]
        report = {
            "status": "PASS" if fallback == 1 else "UNEXPECTED",
            "experiment_id": self.config.experiment_id,
            "cohort": self.cohort,
            "records": len(records),
            "external_calls": 0,
            "responses_replayed": len(response_ledger),
            "fallbacks": fallback,
            "prediction_changes": changes,
            "non_v24_changed_cells": 0,
            "evidence_validation": evidence_report,
            "metrics": metrics,
            "manifest_diff": manifest,
        }
        atomic_json(self.output_dir / "run_report.json", report)
        return report
