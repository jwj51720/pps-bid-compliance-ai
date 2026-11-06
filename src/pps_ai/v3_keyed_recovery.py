"""Append-only exact-task recovery for invalid keyed v3 responses."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import json
import os
from pathlib import Path
import time
from typing import Any

from .config import CleanExperimentConfig
from .decisions.v3_keyed_serialization import decide_v3_keyed
from .evaluate import evaluate_rows_for_ids
from .evidence.validation import clean_final_rows
from .export import write_submission_csv
from .ingest import load_notice_records
from .preflight import compare_manifests
from .runtime.openrouter import OpenRouterRuntime, atomic_json
from .runtime.recovery import attempt_path, write_attempt
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


class V3KeyedResponseRecovery:
    def __init__(self, config: CleanExperimentConfig) -> None:
        self.config = config
        self.output_dir = config.output_dir.resolve()
        recovery = config.raw.get("v3_recovery")
        if not isinstance(recovery, dict):
            raise ValueError("v3 recovery policy is required")
        root = config.path.parents[2]
        self.base_output_dir = (root / str(recovery["base_output_dir"])).resolve()
        self.expected_targets = tuple(sorted(str(value) for value in recovery["expected_targets"]))
        self.attempt_number = int(recovery["attempt_number"])
        self.max_replays = int(recovery["invalid_structured_response_retry"])
        if self.attempt_number != 1 or self.max_replays != 1:
            raise ValueError("C004RR permits exactly one append-only replay")
        required = (
            self.base_output_dir / "preflight.json",
            self.base_output_dir / "submission.csv",
            self.base_output_dir / "responses",
        )
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise FileNotFoundError("missing C004R dev200 artifacts: " + ", ".join(missing))
        self.experiment = V3MonetaryExperiment(
            config, cohort="dev200", output_dir=self.output_dir / "task_audit",
        )

    def _prepare(self) -> tuple[
        list[Any], dict[str, dict[str, Any]], dict[str, dict[str, Any]],
        dict[str, dict[str, Any]], dict[str, Any], list[str],
    ]:
        manifest = compare_manifests(self.config.path, self.config.path.parents[2])
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")
        records, views, tasks, audit = self.experiment.prepare()
        base_preflight = json.loads(
            (self.base_output_dir / "preflight.json").read_text(encoding="utf-8")
        )
        if audit["task_hashes"] != base_preflight["input_audit"]["task_hashes"]:
            raise ValueError("recovery task hashes differ from C004R dev200")
        base_rows = _read_rows(self.base_output_dir / "submission.csv")
        responses: dict[str, dict[str, Any]] = {}
        targets = []
        by_id = {record.notice_id: record for record in records}
        for notice_id in tasks:
            path = self.base_output_dir / "responses" / f"{notice_id}.json"
            if not path.is_file():
                raise FileNotFoundError(f"missing base response: {path}")
            response = json.loads(path.read_text(encoding="utf-8"))
            responses[notice_id] = response
            row = base_rows[notice_id]
            _, _, diagnostic = decide_v3_keyed(
                by_id[notice_id].raw, views[notice_id], response,
                int(row["v3"]), str(row["e3"]),
            )
            if not diagnostic["valid"]:
                targets.append(notice_id)
        targets.sort()
        if tuple(targets) != self.expected_targets:
            raise ValueError(
                f"expected invalid targets {self.expected_targets}, got {tuple(targets)}"
            )
        return records, views, tasks, responses, {
            "manifest_diff": manifest,
            "task_hashes": audit["task_hashes"],
            "base_task_hashes": base_preflight["input_audit"]["task_hashes"],
        }, targets

    def preflight_only(self) -> dict[str, Any]:
        records, _, tasks, _, identity, targets = self._prepare()
        report = {
            "status": "PASS",
            "records": len(records),
            "specialist_tasks": len(tasks),
            "task_identity": "MATCH",
            "targets": targets,
            "target_count": len(targets),
            "normal_responses_not_selected": len(tasks) - len(targets),
            "max_replays": self.max_replays,
            "attempt_number": self.attempt_number,
            "manifest_diff": identity["manifest_diff"],
        }
        atomic_json(self.output_dir / "resolved_manifest.json", self.config.raw)
        atomic_json(self.output_dir / "recovery_preflight.json", report)
        return report

    def run(self) -> dict[str, Any]:
        started = time.monotonic()
        records, views, tasks, responses, identity, targets = self._prepare()
        attempt_root = self.output_dir / "response_attempts"
        pending = []
        for notice_id in targets:
            path = attempt_path(attempt_root, "V3", notice_id, self.attempt_number)
            if path.is_file():
                responses[notice_id] = json.loads(path.read_text(encoding="utf-8"))
            else:
                pending.append(notice_id)
        runtime = OpenRouterRuntime(
            self.config.provider,
            os.environ.get(self.config.provider.api_key_env, ""),
        )

        def replay(notice_id: str) -> tuple[str, dict[str, Any]]:
            response = runtime.complete(tasks[notice_id])
            write_attempt(attempt_root, "V3", notice_id, self.attempt_number, response)
            return notice_id, response

        if pending:
            with ThreadPoolExecutor(max_workers=min(len(pending), self.config.provider.concurrency)) as executor:
                futures = {executor.submit(replay, notice_id): notice_id for notice_id in pending}
                for future in as_completed(futures):
                    notice_id, response = future.result()
                    responses[notice_id] = response

        base_rows = _read_rows(self.base_output_dir / "submission.csv")
        by_id = {record.notice_id: record for record in records}
        selected = []
        recovered = 0
        candidate_rows = {notice_id: dict(row) for notice_id, row in base_rows.items()}
        for notice_id in targets:
            row = candidate_rows[notice_id]
            value, evidence, diagnostic = decide_v3_keyed(
                by_id[notice_id].raw, views[notice_id], responses[notice_id],
                int(row["v3"]), str(row["e3"]),
            )
            recovered += int(bool(diagnostic["valid"]))
            row["v3"], row["e3"] = value, evidence
            selected.append({
                "id": notice_id, "v3": value, "e3": evidence,
                "diagnostic": diagnostic,
            })
        raw_records = [record.raw for record in records]
        rows, evidence_report = clean_final_rows(raw_records, candidate_rows)
        write_submission_csv(self.output_dir / "submission.csv", rows)
        metrics = evaluate_rows_for_ids(
            rows, self.config.labels_path, {record.notice_id for record in records}, "dev200",
        )
        atomic_json(self.output_dir / "metrics.json", {"dev200": metrics})
        current = {str(row["id"]): row for row in rows}
        forbidden = []
        permitted = []
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
                    if notice_id in targets and index == 3:
                        permitted.append(change)
                    else:
                        forbidden.append(change)
        if forbidden:
            raise ValueError(f"recovery changed forbidden cells: {forbidden[:3]}")
        status = "PASS" if recovered == len(targets) else "INCOMPLETE"
        report = {
            "status": status,
            "base_output_dir": str(self.base_output_dir),
            "targets": targets,
            "target_count": len(targets),
            "new_attempts": len(pending),
            "resumed_attempts": len(targets) - len(pending),
            "recovered_valid": recovered,
            "remaining_invalid": len(targets) - recovered,
            "normal_responses_replayed": 0,
            "task_identity": "MATCH" if identity["task_hashes"] == identity["base_task_hashes"] else "DIFF",
            "permitted_v3_changes": permitted,
            "forbidden_changes": forbidden,
            "metrics": metrics,
            "evidence_validation": evidence_report,
            "selected_observations": selected,
            "seconds": round(time.monotonic() - started, 3),
        }
        atomic_json(self.output_dir / "run_report.json", report)
        return report

