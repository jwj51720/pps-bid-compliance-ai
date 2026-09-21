"""Offline replay of the source-concordant v3 requirement-basis reducer."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import CleanExperimentConfig
from .decisions.v3_basis_reducer_v2 import decide_v3_basis_v2
from .evaluate import evaluate_rows
from .evidence.validation import clean_final_rows
from .export import write_submission_csv
from .preflight import compare_manifests
from .runtime.openrouter import atomic_json
from .runtime.recovery import attempt_path
from .v3_monetary_experiment import V3MonetaryExperiment


def _read_rows(path: Path) -> dict[str, dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = {}
        for source in csv.DictReader(handle):
            row: dict[str, Any] = {"id": source["id"]}
            for index in range(1, 25):
                row[f"v{index}"] = int(source[f"v{index}"])
            for index in range(1, 25):
                row[f"e{index}"] = source[f"e{index}"]
            rows[str(row["id"])] = row
        return rows


class V3BasisReducerReplay:
    def __init__(self, config: CleanExperimentConfig) -> None:
        self.config = config
        self.output_dir = config.output_dir.resolve()
        policy = config.raw.get("v3_basis_replay")
        if not isinstance(policy, dict) or policy.get("module") != "v3-basis-reducer-v2":
            raise ValueError("v3 basis replay policy is not selected")
        root = config.path.parents[2]
        self.semantic_output = (root / str(policy["semantic_output_dir"])).resolve()
        self.recovery_output = (root / str(policy["recovery_output_dir"])).resolve()
        self.base_final_output = (root / str(policy["base_final_output_dir"])).resolve()
        self.expected_changed_v3 = int(policy["expected_changed_v3_cells"])
        required = (
            self.semantic_output / "preflight.json",
            self.semantic_output / "responses",
            self.recovery_output / "run_report.json",
            self.base_final_output / "submission.csv",
        )
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise FileNotFoundError("missing C004S replay inputs: " + ", ".join(missing))
        self.experiment = V3MonetaryExperiment(
            config, cohort="dev200", output_dir=self.output_dir / "task_audit",
        )

    def run(self) -> dict[str, Any]:
        manifest = compare_manifests(self.config.path, self.config.path.parents[2])
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")
        records, views, tasks, audit = self.experiment.prepare()
        semantic_preflight = json.loads(
            (self.semantic_output / "preflight.json").read_text(encoding="utf-8")
        )
        if audit["task_hashes"] != semantic_preflight["input_audit"]["task_hashes"]:
            raise ValueError("offline replay task hashes differ")
        recovery_report = json.loads(
            (self.recovery_output / "run_report.json").read_text(encoding="utf-8")
        )
        if recovery_report.get("remaining_invalid") != 0:
            raise ValueError("recovery output still has invalid responses")
        responses = {}
        for notice_id in tasks:
            path = self.semantic_output / "responses" / f"{notice_id}.json"
            responses[notice_id] = json.loads(path.read_text(encoding="utf-8"))
        for notice_id in recovery_report["targets"]:
            path = attempt_path(self.recovery_output / "response_attempts", "V3", notice_id, 1)
            responses[notice_id] = json.loads(path.read_text(encoding="utf-8"))

        base_rows = _read_rows(self.base_final_output / "submission.csv")
        candidate_rows = {notice_id: dict(row) for notice_id, row in base_rows.items()}
        observations = []
        invalid = 0
        for record in records:
            notice_id = record.notice_id
            if notice_id not in tasks:
                continue
            row = candidate_rows[notice_id]
            value, evidence, diagnostic = decide_v3_basis_v2(
                record.raw, views[notice_id], responses[notice_id],
                int(row["v3"]), str(row["e3"]),
            )
            invalid += int(not diagnostic["valid"])
            row["v3"], row["e3"] = value, evidence
            observations.append({
                "id": notice_id, "v3": value, "e3": evidence,
                "diagnostic": diagnostic,
            })
        if invalid:
            raise ValueError(f"offline replay produced {invalid} invalid observations")
        rows, evidence_report = clean_final_rows(
            [record.raw for record in records], candidate_rows,
        )
        current = {str(row["id"]): row for row in rows}
        v3_changes = []
        forbidden = []
        for notice_id, base in base_rows.items():
            row = current[notice_id]
            for index in range(1, 25):
                for prefix in ("v", "e"):
                    field = f"{prefix}{index}"
                    if str(row[field]) == str(base[field]):
                        continue
                    change = {
                        "id": notice_id, "field": field,
                        "before": str(base[field]), "after": str(row[field]),
                    }
                    if index == 3:
                        v3_changes.append(change)
                    else:
                        forbidden.append(change)
        changed_v3_labels = sum(change["field"] == "v3" for change in v3_changes)
        if forbidden:
            raise ValueError(f"basis replay changed forbidden cells: {forbidden[:3]}")
        if changed_v3_labels != self.expected_changed_v3:
            raise ValueError(
                f"expected {self.expected_changed_v3} v3 label changes, got {changed_v3_labels}"
            )
        write_submission_csv(self.output_dir / "submission.csv", rows)
        metrics = evaluate_rows(rows, self.config.labels_path, {
            "fast20": self.config.fast_panel_path,
            "holdout20": self.config.holdout_panel_path,
        })
        atomic_json(self.output_dir / "metrics.json", metrics)
        atomic_json(self.output_dir / "observations.json", observations)
        report = {
            "status": "PASS",
            "calls": 0,
            "task_identity": "MATCH",
            "responses": len(responses),
            "recovery_attempts_selected": len(recovery_report["targets"]),
            "invalid_responses": invalid,
            "v3_changes": v3_changes,
            "forbidden_changes": forbidden,
            "metrics": metrics,
            "evidence_validation": evidence_report,
            "manifest_diff": manifest,
        }
        atomic_json(self.output_dir / "resolved_manifest.json", self.config.raw)
        atomic_json(self.output_dir / "run_report.json", report)
        return report

