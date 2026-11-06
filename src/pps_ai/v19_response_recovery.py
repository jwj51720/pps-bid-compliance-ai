"""Append-only exact-task recovery for unusable C005H v19 responses."""

from __future__ import annotations

import json
import os
from typing import Any

from .config import CleanExperimentConfig
from .decisions.v19_quote_resolution_v2 import parse_v19_observations_relaxed_quote
from .runtime.openrouter import OpenRouterRuntime, atomic_json
from .v19_quote_replay import V19QuoteReplay
from .v19_requirement_experiment import V19RequirementExperiment


class V19ResponseRecovery:
    def __init__(self, config: CleanExperimentConfig) -> None:
        self.config = config
        policy = config.raw.get("v19_response_recovery")
        if not isinstance(policy, dict) or policy.get("module") != "v19-exact-task-recovery-v1":
            raise ValueError("C005HR response recovery is not selected")
        self.cohort = str(policy["cohort"])
        self.targets = tuple(str(value) for value in policy["expected_targets"])
        if self.targets != ("PPS-DEV-192__p01",):
            raise ValueError("unexpected C005HR recovery target")
        if int(policy["max_new_calls"]) != 1:
            raise ValueError("C005HR permits exactly one new recovery call")
        root = config.path.parents[2]
        self.base_output_dir = (root / str(policy["base_output_dir"])).resolve()
        self.attempt_dir = (root / str(policy["attempt_dir"])).resolve()

    def run(self) -> dict[str, Any]:
        experiment = V19RequirementExperiment(
            self.config,
            cohort=self.cohort,
            output_dir=self.config.output_dir / "_reconstructed",
        )
        _, _, tasks, task_candidates, audit = experiment.prepare()
        base_preflight = json.loads(
            (self.base_output_dir / "preflight.json").read_text(encoding="utf-8")
        )
        if audit["task_hashes"] != base_preflight["input_audit"]["task_hashes"]:
            raise ValueError("C005HR task hashes differ from C005H")
        unusable = []
        for task_id in tasks:
            response = json.loads(
                (self.base_output_dir / "responses" / f"{task_id}.json").read_text(
                    encoding="utf-8"
                )
            )
            parsed, _ = parse_v19_observations_relaxed_quote(
                response, task_candidates[task_id],
            )
            if parsed is None:
                unusable.append(task_id)
        if tuple(unusable) != self.targets:
            raise ValueError(f"C005HR unusable target set differs: {unusable}")

        new_calls = 0
        resumed = 0
        for task_id in self.targets:
            path = self.attempt_dir / f"{task_id}.json"
            if path.is_file():
                response = json.loads(path.read_text(encoding="utf-8"))
                resumed += 1
            else:
                runtime = OpenRouterRuntime(
                    self.config.provider,
                    os.environ.get(self.config.provider.api_key_env, ""),
                )
                response = runtime.complete(tasks[task_id])
                atomic_json(path, response)
                new_calls += 1
            parsed, reason = parse_v19_observations_relaxed_quote(
                response, task_candidates[task_id],
            )
            if parsed is None:
                report = {
                    "status": "INCOMPLETE",
                    "experiment_id": self.config.experiment_id,
                    "cohort": self.cohort,
                    "task_hash_identity": "MATCH",
                    "expected_targets": list(self.targets),
                    "new_recovery_calls": new_calls,
                    "resumed_recovery_calls": resumed,
                    "reason": f"{task_id}:{reason}",
                }
                atomic_json(self.config.output_dir / "run_report.json", report)
                return report

        replay_report = V19QuoteReplay(self.config).run()
        replay_report.update({
            "new_recovery_calls": new_calls,
            "resumed_recovery_calls": resumed,
            "normal_responses_not_replayed": len(tasks) - len(self.targets),
            "recovery_targets": list(self.targets),
        })
        atomic_json(self.config.output_dir / "run_report.json", replay_report)
        return replay_report
