"""Hash-checked replay of the integrated v3/v19 ownership policy."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import CleanExperimentConfig
from .decisions.v3_basis_reducer_v2 import decide_v3_basis_v2
from .decisions.v19_quote_resolution_v2 import (
    parse_v19_observations_relaxed_quote,
    reduce_v19_with_quote_resolution,
)
from .evaluate import evaluate_rows
from .evidence.validation import clean_final_rows
from .export import write_submission_csv
from .preflight import compare_manifests
from .runtime.openrouter import atomic_json
from .runtime.recovery import attempt_path
from .v3_monetary_experiment import V3MonetaryExperiment
from .v19_requirement_experiment import V19RequirementExperiment


def _read_rows(path: Path) -> dict[str, dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows: dict[str, dict[str, Any]] = {}
        for source in csv.DictReader(handle):
            row: dict[str, Any] = {"id": source["id"]}
            row.update({f"v{index}": int(source[f"v{index}"]) for index in range(1, 25)})
            row.update({f"e{index}": source[f"e{index}"] for index in range(1, 25)})
            rows[str(row["id"])] = row
        return rows


def _cell_differences(
    left: dict[str, dict[str, Any]], right: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    differences = []
    for notice_id in sorted(set(left) | set(right)):
        for field in ["id", *[f"v{i}" for i in range(1, 25)], *[f"e{i}" for i in range(1, 25)]]:
            before = str(left.get(notice_id, {}).get(field, "<MISSING>"))
            after = str(right.get(notice_id, {}).get(field, "<MISSING>"))
            if before != after:
                differences.append({"id": notice_id, "field": field, "expected": before, "actual": after})
    return differences


class IntegratedV3V19Replay:
    def __init__(self, config: CleanExperimentConfig) -> None:
        self.config = config
        self.root = config.path.parents[2]
        self.output_dir = config.output_dir.resolve()
        self.base_dir = self.root / "outputs/clean-reference-l41-openrouter-dev200-v1"
        self.v3_dir = self.root / "outputs/clean-exp-c004r-v3-keyed-full-fast-v11/dev200"
        self.v3_recovery_dir = self.root / "outputs/clean-exp-c004rr-v3-keyed-recovery-v1"
        self.v19_dir = self.root / "outputs/clean-exp-c005d-v19-dev200-promotion-v1/dev200"
        for path in (
            self.base_dir / "submission.csv",
            self.v3_dir / "preflight.json",
            self.v3_recovery_dir / "run_report.json",
            self.v19_dir / "preflight.json",
            self.v19_dir / "submission.csv",
        ):
            if not path.exists():
                raise FileNotFoundError(path)

    def run(self) -> dict[str, Any]:
        manifest = compare_manifests(self.config.path, self.root)
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")

        v3_experiment = V3MonetaryExperiment(
            self.config, cohort="dev200", output_dir=self.output_dir / "v3_task_audit",
        )
        records, v3_views, v3_tasks, v3_audit = v3_experiment.prepare()
        stored_v3_preflight = json.loads(
            (self.v3_dir / "preflight.json").read_text(encoding="utf-8")
        )
        if v3_audit["task_hashes"] != stored_v3_preflight["input_audit"]["task_hashes"]:
            raise ValueError("v3 task hashes differ from stored model responses")

        v19_experiment = V19RequirementExperiment(
            self.config, cohort="dev200", output_dir=self.output_dir / "v19_task_audit",
        )
        v19_records, v19_views, v19_tasks, v19_task_candidates, v19_audit = v19_experiment.prepare()
        stored_v19_preflight = json.loads(
            (self.v19_dir / "preflight.json").read_text(encoding="utf-8")
        )
        if v19_audit["task_hashes"] != stored_v19_preflight["input_audit"]["task_hashes"]:
            raise ValueError("v19 task hashes differ from stored model responses")

        rows = _read_rows(self.base_dir / "submission.csv")
        v3_recovery = json.loads(
            (self.v3_recovery_dir / "run_report.json").read_text(encoding="utf-8")
        )
        recovered_v3 = set(v3_recovery["targets"])
        v3_invalid = []
        for record in records:
            notice_id = record.notice_id
            if notice_id not in v3_tasks:
                continue
            response_path = self.v3_dir / "responses" / f"{notice_id}.json"
            if notice_id in recovered_v3:
                response_path = attempt_path(
                    self.v3_recovery_dir / "response_attempts", "V3", notice_id, 1,
                )
            response = json.loads(response_path.read_text(encoding="utf-8"))
            row = rows[notice_id]
            value, evidence, diagnostic = decide_v3_basis_v2(
                record.raw, v3_views[notice_id], response,
                int(row["v3"]), str(row["e3"]),
            )
            if not diagnostic["valid"]:
                v3_invalid.append(notice_id)
            row["v3"], row["e3"] = value, evidence

        v19_by_id = {record.notice_id: record for record in v19_records}
        v19_invalid = []
        v19_unresolved = []
        for notice_id, record in v19_by_id.items():
            candidates = tuple(v19_views[notice_id]["candidates"])
            if not candidates:
                continue
            task_ids = v19_audit["coverage"][notice_id]["task_ids"]
            parsed_rows = []
            failed = False
            for task_id in task_ids:
                response = json.loads(
                    (self.v19_dir / "responses" / f"{task_id}.json").read_text(encoding="utf-8")
                )
                parsed, _ = parse_v19_observations_relaxed_quote(
                    response, v19_task_candidates[task_id],
                )
                if parsed is None:
                    failed = True
                    break
                parsed_rows.extend(parsed)
            if failed:
                v19_invalid.append(notice_id)
                continue
            value, evidence, _ = reduce_v19_with_quote_resolution(candidates, parsed_rows)
            if value is None:
                v19_unresolved.append(notice_id)
                continue
            rows[notice_id]["v19"], rows[notice_id]["e19"] = value, evidence

        clean_rows, evidence = clean_final_rows(
            [dict(record.raw) for record in records], rows,
        )
        write_submission_csv(self.output_dir / "submission.csv", clean_rows)
        metrics = evaluate_rows(clean_rows, self.config.labels_path, {
            "fast20": self.config.fast_panel_path,
            "holdout20": self.config.holdout_panel_path,
        })
        atomic_json(self.output_dir / "metrics.json", metrics)
        current = {str(row["id"]): row for row in clean_rows}
        expected = _read_rows(self.v19_dir / "submission.csv")
        differences = _cell_differences(expected, current)
        report = {
            "status": "PASS" if not differences and not v3_invalid and not v19_invalid else "FAIL",
            "mode": "stored-response-task-hash-replay",
            "records": len(records),
            "initial_logical_calls": {
                "r10": len(records),
                "C24": len(records),
                "v19_owner": len(records),
                "v3_specialist": len(v3_tasks),
                "total": 3 * len(records) + len(v3_tasks),
            },
            "v3_task_hashes": "MATCH",
            "v19_task_hashes": "MATCH",
            "v3_recovered_attempt_1": sorted(recovered_v3),
            "v3_invalid": v3_invalid,
            "v19_invalid": v19_invalid,
            "v19_unresolved_positive_evidence": v19_unresolved,
            "expected_c005d_cell_differences": differences,
            "metrics": metrics,
            "evidence": evidence,
            "manifest_diff": manifest,
            "limitation": "stored actual model responses; not a fresh evaluator-vLLM runtime measurement",
        }
        atomic_json(self.output_dir / "run_report.json", report)
        return report
