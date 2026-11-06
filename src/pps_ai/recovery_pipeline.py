"""Serialization-only replay of unusable frozen-baseline responses."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

from .config import CleanExperimentConfig
from .evaluate import evaluate_rows
from .evidence import clean_final_rows
from .export import write_submission_csv
from .ingest import load_notice_records
from .pipeline import CleanReferencePipeline
from .runtime.openrouter import OpenRouterRuntime, atomic_json
from .runtime.recovery import attempt_path, response_is_usable, write_attempt


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_csv(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["id"]: row for row in csv.DictReader(handle)}


class CleanResponseRecoveryPipeline:
    """Replay only unusable responses while holding semantic inputs fixed."""

    def __init__(self, config: CleanExperimentConfig) -> None:
        self.config = config
        recovery = config.raw.get("recovery")
        if not isinstance(recovery, dict):
            raise ValueError("recovery experiment requires a recovery object")
        root = config.path.parents[2]
        self.base_output_dir = (root / str(recovery["base_output_dir"])).resolve()
        self.target_arm = str(recovery["target_arm"])
        self.max_replays = int(recovery["invalid_structured_response_retry"])
        self.expected_targets = int(recovery["expected_invalid_targets"])
        self.attempt_number = int(recovery.get("attempt_number", 1))
        self.prior_attempt_dirs = tuple(
            (root / str(path)).resolve()
            for path in recovery.get("prior_attempt_dirs", [])
        )
        if self.target_arm not in {"r10", "B", "C24"}:
            raise ValueError("unsupported recovery target arm")
        if self.max_replays != 1 or self.attempt_number < 1:
            raise ValueError("EXP-C001 permits exactly one structured replay")
        required = (
            self.base_output_dir / "preflight.json",
            self.base_output_dir / "rankings.json",
            self.base_output_dir / "submission.csv",
        )
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise FileNotFoundError("missing baseline recovery artifacts: " + ", ".join(missing))
        self.reference_pipeline = CleanReferencePipeline(config)

    def _load_base_responses(
        self, tasks: dict[tuple[str, str], dict[str, Any]],
    ) -> dict[tuple[str, str], dict[str, Any]]:
        responses: dict[tuple[str, str], dict[str, Any]] = {}
        for arm, notice_id in tasks:
            path = self.base_output_dir / "responses" / arm / f"{notice_id}.json"
            if not path.is_file():
                raise FileNotFoundError(f"missing baseline response: {path}")
            responses[arm, notice_id] = json.loads(path.read_text(encoding="utf-8"))
        for prior_dir in self.prior_attempt_dirs:
            if not prior_dir.is_dir():
                raise FileNotFoundError(f"missing prior attempt directory: {prior_dir}")
            for path in prior_dir.glob("*/*/attempt_*.json"):
                key = (path.parent.parent.name, path.parent.name)
                if key not in responses:
                    raise ValueError(f"prior attempt has foreign task: {path}")
                candidate = json.loads(path.read_text(encoding="utf-8"))
                if response_is_usable(candidate):
                    responses[key] = candidate
        return responses

    def _verify_task_identity(self, preflight: dict[str, Any]) -> None:
        base = json.loads((self.base_output_dir / "preflight.json").read_text(encoding="utf-8"))
        if preflight["task_hashes"] != base["task_hashes"]:
            raise ValueError("recovery task hashes differ from frozen baseline")
        if preflight["owner_matrix"] != base["owner_matrix"]:
            raise ValueError("recovery owner matrix differs from frozen baseline")

    def _prepare(self) -> tuple[
        list[Any], dict[str, dict[str, Any]],
        dict[tuple[str, str], dict[str, Any]], dict[str, Any],
        dict[tuple[str, str], dict[str, Any]], list[tuple[str, str]],
    ]:
        records = load_notice_records(self.config.input_path)
        if len(records) != 200:
            raise ValueError("serialization recovery requires full dev200")
        prepared, tasks, preflight = self.reference_pipeline.prepare(records)
        self._verify_task_identity(preflight)
        responses = self._load_base_responses(tasks)
        targets = sorted(
            key for key, response in responses.items()
            if key[0] == self.target_arm and not response_is_usable(response)
        )
        if len(targets) != self.expected_targets:
            raise ValueError(
                f"expected {self.expected_targets} unusable targets, got {len(targets)}"
            )
        return records, prepared, tasks, preflight, responses, targets

    def preflight_only(self) -> dict[str, Any]:
        records, _, tasks, preflight, _, targets = self._prepare()
        report = {
            "experiment_id": self.config.experiment_id,
            "records": len(records),
            "task_count": len(tasks),
            "task_identity": "MATCH",
            "owner_identity": "MATCH",
            "target_arm": self.target_arm,
            "targets": [notice_id for _, notice_id in targets],
            "target_count": len(targets),
            "normal_responses_not_selected": len(tasks) - len(targets),
            "max_replays": self.max_replays,
            "attempt_number": self.attempt_number,
            "prior_attempt_dirs": [str(path) for path in self.prior_attempt_dirs],
            "status": "PASS",
        }
        atomic_json(self.config.output_dir / "recovery_preflight.json", report)
        return report

    def run(self) -> dict[str, Any]:
        started = time.monotonic()
        output_dir = self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        records, prepared, tasks, preflight, responses, targets = self._prepare()
        atomic_json(output_dir / "preflight.json", preflight)
        attempt_root = output_dir / "response_attempts"
        pending: list[tuple[str, str]] = []
        for arm, notice_id in targets:
            path = attempt_path(attempt_root, arm, notice_id, self.attempt_number)
            if path.is_file():
                responses[arm, notice_id] = json.loads(path.read_text(encoding="utf-8"))
            else:
                pending.append((arm, notice_id))
        api_key = os.environ.get(self.config.provider.api_key_env, "")
        runtime = OpenRouterRuntime(self.config.provider, api_key)

        def replay(key: tuple[str, str]) -> tuple[tuple[str, str], dict[str, Any]]:
            response = runtime.complete(tasks[key])
            write_attempt(
                attempt_root, key[0], key[1], self.attempt_number, response,
            )
            return key, response

        if pending:
            with ThreadPoolExecutor(max_workers=min(len(pending), self.config.provider.concurrency)) as executor:
                futures = {executor.submit(replay, key): key for key in pending}
                for future in as_completed(futures):
                    key, response = future.result()
                    responses[key] = response
        raw_records = {record.notice_id: dict(record.raw) for record in records}
        rankings = json.loads((self.base_output_dir / "rankings.json").read_text(encoding="utf-8"))
        candidate, _, _, _, diagnostics = self.reference_pipeline.reference.pipeline.assemble(
            raw_records, prepared, responses, rankings, self.reference_pipeline.builder,
            data_dir=str(self.config.data_dir),
        )
        rows, evidence_report = clean_final_rows(list(raw_records.values()), candidate)
        write_submission_csv(output_dir / "submission.csv", rows)
        metrics = evaluate_rows(rows, self.config.labels_path, {
            "fast20": self.config.fast_panel_path,
            "holdout20": self.config.holdout_panel_path,
        })
        atomic_json(output_dir / "metrics.json", metrics)
        baseline_rows = _read_csv(self.base_output_dir / "submission.csv")
        current_rows = {str(row["id"]): row for row in rows}
        target_ids = {notice_id for _, notice_id in targets}
        forbidden_changes: list[dict[str, str]] = []
        permitted_v24_changes: list[dict[str, str]] = []
        for notice_id, base_row in baseline_rows.items():
            row = current_rows[notice_id]
            for index in range(1, 25):
                item = f"v{index}"
                evidence = f"e{index}"
                if (
                    str(row[item]) == base_row[item]
                    and str(row[evidence]) == base_row[evidence]
                ):
                    continue
                change = {
                    "id": notice_id, "field": item,
                    "before": base_row[item], "after": str(row[item]),
                }
                if item == "v24" and notice_id in target_ids:
                    permitted_v24_changes.append(change)
                else:
                    forbidden_changes.append(change)
        if forbidden_changes:
            raise ValueError(f"serialization recovery changed forbidden cells: {forbidden_changes[:3]}")
        recovered = sum(response_is_usable(responses[key]) for key in targets)
        report = {
            "experiment_id": self.config.experiment_id,
            "base_output_dir": str(self.base_output_dir),
            "base_submission_sha256": _sha256(self.base_output_dir / "submission.csv"),
            "target_arm": self.target_arm,
            "attempt_number": self.attempt_number,
            "prior_attempt_dirs": [str(path) for path in self.prior_attempt_dirs],
            "targets": [notice_id for _, notice_id in targets],
            "target_count": len(targets),
            "resumed_attempts": len(targets) - len(pending),
            "new_attempts": len(pending),
            "recovered_usable": recovered,
            "remaining_unusable": len(targets) - recovered,
            "permitted_v24_changes": permitted_v24_changes,
            "forbidden_changes": forbidden_changes,
            "metrics": metrics,
            "evidence": evidence_report,
            "fallbacks": {
                arm: sum(
                    bool(diagnostics[arm, notice_id].get(
                        "fallback", not diagnostics[arm, notice_id].get("valid", True)
                    ))
                    for notice_id in raw_records
                )
                for arm in ("r10", "B", "C24")
            },
            "seconds": round(time.monotonic() - started, 3),
            "status": "PASS" if recovered == len(targets) else "INCOMPLETE",
        }
        atomic_json(output_dir / "run_report.json", report)
        return report
