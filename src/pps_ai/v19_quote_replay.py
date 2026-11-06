"""Zero-call replay of C005 responses with positive-only quote resolution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import CleanExperimentConfig
from .decisions.v19_quote_resolution_v2 import (
    parse_v19_observations_relaxed_quote,
    reduce_v19_with_quote_resolution,
)
from .evaluate import evaluate_rows_for_ids
from .evidence.validation import clean_final_rows
from .export import write_submission_csv
from .preflight import compare_manifests
from .runtime.openrouter import atomic_json
from .v19_requirement_experiment import (
    V19RequirementExperiment,
    _read_rows,
)


class V19QuoteReplay:
    def __init__(self, config: CleanExperimentConfig) -> None:
        self.config = config
        self.output_dir = config.output_dir.resolve()
        policy = config.raw.get("v19_quote_replay")
        if not isinstance(policy, dict) or policy.get("module") != "v19-positive-quote-resolution-v2":
            raise ValueError("C005R quote replay is not selected")
        if int(policy.get("calls", -1)) != 0:
            raise ValueError("v19 quote replay must itself make zero calls")
        self.cohort = str(policy.get("cohort"))
        if self.cohort not in {"fast20", "holdout20", "dev200"}:
            raise ValueError("unsupported v19 quote replay cohort")
        root = config.path.parents[2]
        self.base_output_dir = (root / str(policy["base_output_dir"])).resolve()
        self.expected_tasks = int(policy["expected_tasks"])
        override_value = policy.get("response_override_dir")
        self.response_override_dir = (
            (root / str(override_value)).resolve() if override_value else None
        )
        self.override_targets = set(str(value) for value in policy.get("override_targets", []))
        if not (self.base_output_dir / "preflight.json").is_file():
            raise FileNotFoundError("C005 fast preflight is required")

    def run(self) -> dict[str, Any]:
        manifest = compare_manifests(self.config.path, self.config.path.parents[2])
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")
        experiment = V19RequirementExperiment(
            self.config,
            cohort=self.cohort,
            output_dir=self.output_dir / "_rendered_reconstruction",
        )
        records, views, tasks, task_candidates, audit = experiment.prepare()
        if len(tasks) != self.expected_tasks:
            raise ValueError("C005R task count differs")
        base_preflight = json.loads(
            (self.base_output_dir / "preflight.json").read_text(encoding="utf-8")
        )
        base_hashes = base_preflight["input_audit"]["task_hashes"]
        if audit["task_hashes"] != base_hashes:
            raise ValueError("C005R task hashes differ from stored C005 tasks")
        responses = {}
        response_hashes = {}
        import hashlib

        for task_id in tasks:
            if task_id in self.override_targets:
                if self.response_override_dir is None:
                    raise ValueError("v19 response override directory is missing")
                path = self.response_override_dir / f"{task_id}.json"
            else:
                path = self.base_output_dir / "responses" / f"{task_id}.json"
            if not path.is_file():
                raise FileNotFoundError(f"missing stored C005 response: {task_id}")
            payload = path.read_bytes()
            response_hashes[task_id] = hashlib.sha256(payload).hexdigest()
            responses[task_id] = json.loads(payload)

        policy = self.config.raw["v19_policy"]
        base_rows = _read_rows(
            (self.config.path.parents[2] / str(policy["base_output_dir"]) / "submission.csv").resolve()
        )
        candidate_rows = {}
        observations = []
        invalid = 0
        fallback = 0
        for record in records:
            notice_id = record.notice_id
            row = dict(base_rows[notice_id])
            candidates = tuple(views[notice_id]["candidates"])
            task_ids = audit["coverage"][notice_id]["task_ids"]
            if not candidates:
                diagnostic = {
                    "valid": True, "fallback": True, "decision": "BASELINE",
                    "reason": "no_candidate", "observations": [],
                }
                fallback += 1
            else:
                parsed_rows = []
                failure_reason = None
                for task_id in task_ids:
                    parsed, reason = parse_v19_observations_relaxed_quote(
                        responses[task_id], task_candidates[task_id],
                    )
                    if parsed is None:
                        failure_reason = f"{task_id}:{reason}"
                        break
                    parsed_rows.extend(parsed)
                if failure_reason is not None:
                    diagnostic = {
                        "valid": False, "fallback": True, "decision": "BASELINE",
                        "reason": failure_reason, "observations": [],
                    }
                    invalid += 1
                    fallback += 1
                else:
                    value, evidence, diagnostic = reduce_v19_with_quote_resolution(
                        candidates, parsed_rows,
                    )
                    if value is None:
                        fallback += 1
                    else:
                        row["v19"], row["e19"] = value, evidence
            candidate_rows[notice_id] = row
            observations.append({
                "id": notice_id, "v19": row["v19"], "e19": row["e19"],
                "diagnostic": diagnostic,
            })
            for index in range(1, 25):
                if index == 19:
                    continue
                if row[f"v{index}"] != base_rows[notice_id][f"v{index}"]:
                    raise ValueError(f"{notice_id}/v{index}: non-owner label changed")
                if row[f"e{index}"] != base_rows[notice_id][f"e{index}"]:
                    raise ValueError(f"{notice_id}/e{index}: non-owner evidence changed")

        rows, evidence_report = clean_final_rows(
            [dict(record.raw) for record in records], candidate_rows,
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        atomic_json(self.output_dir / "resolved_manifest.json", self.config.raw)
        atomic_json(self.output_dir / "preflight.json", {
            "status": "PASS",
            "manifest_diff": manifest,
            "task_hash_identity": "MATCH",
            "task_hashes": audit["task_hashes"],
            "response_hashes": response_hashes,
        })
        atomic_json(self.output_dir / "observations.json", observations)
        write_submission_csv(self.output_dir / "submission.csv", rows)
        metrics = evaluate_rows_for_ids(
            rows, self.config.labels_path,
            {record.notice_id for record in records}, self.cohort,
        )
        atomic_json(self.output_dir / "metrics.json", {self.cohort: metrics})
        report = {
            "status": "PASS" if invalid == 0 else "INCOMPLETE",
            "experiment_id": self.config.experiment_id,
            "cohort": self.cohort,
            "records": len(records),
            "provider_calls": 0,
            "stored_responses_replayed": len(responses),
            "task_hash_identity": "MATCH",
            "invalid_responses": invalid,
            "fallbacks": fallback,
            "metrics": metrics,
            "non_v19_changed_cells": 0,
            "evidence_validation": evidence_report,
            "v19_positive_without_evidence": sum(
                int(row["v19"] == 1 and not row["e19"]) for row in rows
            ),
        }
        atomic_json(self.output_dir / "run_report.json", report)
        return report
