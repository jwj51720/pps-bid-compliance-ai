"""Compact response recovery for semantically invalid v19 primary tasks."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .config import CleanExperimentConfig
from .decisions.v19_compact_serialization import (
    adapt_compact_response,
    build_v19_compact_task,
)
from .decisions.v19_quote_resolution_v2 import parse_v19_observations_relaxed_quote
from .runtime.openrouter import OpenRouterRuntime, atomic_json
from .runtime.tokenizer import GemmaTokenCounter
from .views.v19_requirements import V19RequirementCandidate


Completion = Callable[[dict[str, Any]], dict[str, Any]]


def invalid_v19_task_ids(
    responses: Mapping[str, Mapping[str, Any]],
    task_candidates: Mapping[str, Sequence[V19RequirementCandidate]],
) -> list[str]:
    invalid = []
    for task_id, candidates in task_candidates.items():
        parsed, _ = parse_v19_observations_relaxed_quote(
            responses[task_id], candidates,
        )
        if parsed is None:
            invalid.append(task_id)
    return invalid


class V19SerializationRecovery:
    """Retry only invalid verbose tasks once with a compact isomorphic schema."""

    def __init__(
        self,
        config: CleanExperimentConfig,
        *,
        output_dir: Path,
    ) -> None:
        self.config = config
        self.output_dir = output_dir.resolve()
        policy = config.raw.get("v19_serialization_recovery")
        if (
            not isinstance(policy, dict)
            or policy.get("module") != "v19-invalid-only-compact-recovery-v1"
        ):
            raise ValueError("v19 compact serialization recovery is not selected")
        if int(policy.get("max_retries_per_invalid_task", -1)) != 1:
            raise ValueError("v19 compact recovery permits one retry per invalid task")
        self.counter = GemmaTokenCounter(config.tokenizer_dir)

    def apply(
        self,
        *,
        records: Sequence[Any],
        primary_tasks: Mapping[str, dict[str, Any]],
        task_candidates: Mapping[str, Sequence[V19RequirementCandidate]],
        responses: Mapping[str, dict[str, Any]],
        complete: Completion | None = None,
    ) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
        effective = dict(responses)
        invalid_before = invalid_v19_task_ids(effective, task_candidates)
        records_by_id = {record.notice_id: record for record in records}
        runtime: OpenRouterRuntime | None = None
        new_calls = 0
        resumed_calls = 0
        recovered = []
        unresolved = []
        task_audits = []

        for task_id in invalid_before:
            notice_id = task_id.split("__p", 1)[0]
            primary = primary_tasks[task_id]
            candidates = task_candidates[task_id]
            compact = build_v19_compact_task(records_by_id[notice_id].raw, candidates)
            user_identical = compact["messages"][1] == primary["messages"][1]
            primary_system = str(primary["messages"][0]["content"])
            system_prefix_identical = str(
                compact["messages"][0]["content"]
            ).startswith(primary_system)
            if not user_identical or not system_prefix_identical:
                raise ValueError(f"{task_id}: compact recovery changed semantic prompt")
            tokens = self.counter.count(compact["messages"])
            if tokens > self.config.prompt_budget:
                raise ValueError(f"{task_id}: compact recovery exceeds prompt budget")

            raw_path = self.output_dir / "compact_recovery_responses" / f"{task_id}.json"
            if raw_path.is_file():
                compact_response = json.loads(raw_path.read_text(encoding="utf-8"))
                resumed_calls += 1
            else:
                if complete is None:
                    if runtime is None:
                        runtime = OpenRouterRuntime(
                            self.config.provider,
                            os.environ.get(self.config.provider.api_key_env, ""),
                        )
                    complete = runtime.complete
                compact_response = complete(compact)
                atomic_json(raw_path, compact_response)
                new_calls += 1

            adapted = adapt_compact_response(compact_response, candidates)
            valid = False
            reason = "compact_adapter_invalid"
            if adapted is not None:
                parsed, reason = parse_v19_observations_relaxed_quote(adapted, candidates)
                valid = parsed is not None
                if valid:
                    adapted_path = (
                        self.output_dir / "adapted_recovery_responses" / f"{task_id}.json"
                    )
                    atomic_json(adapted_path, adapted)
                    effective[task_id] = adapted
                    recovered.append(task_id)
            if not valid:
                unresolved.append(task_id)
            task_audits.append({
                "task_id": task_id,
                "user_message_identical": user_identical,
                "system_prefix_identical": system_prefix_identical,
                "tokens": tokens,
                "candidate_source_ids": [candidate.source_id for candidate in candidates],
                "candidate_sha256": [candidate.sha256 for candidate in candidates],
                "valid": valid,
                "reason": reason,
            })

        invalid_after = invalid_v19_task_ids(effective, task_candidates)
        report = {
            "module": "v19-invalid-only-compact-recovery-v1",
            "primary_invalid_task_ids": invalid_before,
            "primary_invalid_tasks": len(invalid_before),
            "new_compact_recovery_calls": new_calls,
            "resumed_compact_recovery_calls": resumed_calls,
            "recovered_task_ids": recovered,
            "unresolved_recovery_task_ids": unresolved,
            "invalid_after_recovery_task_ids": invalid_after,
            "invalid_after_recovery": len(invalid_after),
            "task_audits": task_audits,
        }
        atomic_json(self.output_dir / "serialization_recovery.json", report)
        return effective, report
