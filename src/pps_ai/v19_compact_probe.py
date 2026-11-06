"""One-target compact-serialization probe for the C005H v19 failure."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

from .config import CleanExperimentConfig
from .decisions.v19_compact_serialization import (
    adapt_compact_response,
    build_v19_compact_task,
)
from .decisions.v19_quote_resolution_v2 import parse_v19_observations_relaxed_quote
from .preflight import compare_manifests
from .runtime.openrouter import OpenRouterRuntime, atomic_json
from .runtime.tokenizer import GemmaTokenCounter
from .v19_quote_replay import V19QuoteReplay
from .v19_requirement_experiment import V19RequirementExperiment


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _compact_mock_response(task: dict[str, Any]) -> dict[str, Any]:
    source_ids = task["schema"]["properties"]["observations"]["required"]
    observations = {
        source_id: {
            "r": 5,
            "k": 3,
            "x": 0,
            "h": 0,
            "s": 0,
            "b": 0,
            "w": 0,
            "a": 0,
            "q": "N/A",
        }
        for source_id in source_ids
    }
    return {
        "content": json.dumps({"observations": observations}, ensure_ascii=False),
        "finish_reason": "stop",
        "invalid": False,
        "model": "mock",
        "usage": {},
        "latency_seconds": 0.0,
        "attempts": 1,
    }


class V19CompactSerializationProbe:
    """Change only response serialization for one reproducibly invalid task."""

    def __init__(self, config: CleanExperimentConfig) -> None:
        self.config = config
        self.output_dir = config.output_dir.resolve()
        policy = config.raw.get("v19_compact_probe")
        if not isinstance(policy, dict) or policy.get("module") != "v19-compact-serialization-v1":
            raise ValueError("C005HS compact serialization probe is not selected")
        self.target = str(policy["target_task_id"])
        if self.target != "PPS-DEV-192__p01":
            raise ValueError("unexpected C005HS target")
        if int(policy["max_new_calls"]) != 1:
            raise ValueError("C005HS permits exactly one new call")
        root = config.path.parents[2]
        self.base_output_dir = (root / str(policy["base_output_dir"])).resolve()
        self.response_dir = (root / str(policy["response_dir"])).resolve()
        self.adapted_dir = (root / str(policy["adapted_response_dir"])).resolve()
        if not (self.base_output_dir / "preflight.json").is_file():
            raise FileNotFoundError("C005H holdout preflight is required")
        self.counter = GemmaTokenCounter(config.tokenizer_dir)

    def prepare(self) -> dict[str, Any]:
        experiment = V19RequirementExperiment(
            self.config,
            cohort="holdout20",
            output_dir=self.output_dir / "_reconstructed",
        )
        records, _, tasks, task_candidates, audit = experiment.prepare()
        base_preflight = json.loads(
            (self.base_output_dir / "preflight.json").read_text(encoding="utf-8")
        )
        base_hashes = base_preflight["input_audit"]["task_hashes"]
        if audit["task_hashes"] != base_hashes:
            raise ValueError("C005HS reconstructed verbose task hashes differ from C005H")
        if self.target not in tasks:
            raise ValueError("C005HS target task is absent")

        unusable = []
        for task_id, candidates in task_candidates.items():
            response_path = self.base_output_dir / "responses" / f"{task_id}.json"
            response = json.loads(response_path.read_text(encoding="utf-8"))
            parsed, _ = parse_v19_observations_relaxed_quote(response, candidates)
            if parsed is None:
                unusable.append(task_id)
        if unusable != [self.target]:
            raise ValueError(f"C005HS unusable target set differs: {unusable}")

        notice_id = self.target.split("__p", 1)[0]
        record = next(record for record in records if record.notice_id == notice_id)
        verbose = tasks[self.target]
        candidates = task_candidates[self.target]
        compact = build_v19_compact_task(record.raw, candidates)
        user_identical = compact["messages"][1] == verbose["messages"][1]
        verbose_system = str(verbose["messages"][0]["content"])
        compact_system = str(compact["messages"][0]["content"])
        system_prefix_identical = compact_system.startswith(verbose_system)
        if not user_identical or not system_prefix_identical:
            raise ValueError("C005HS changed semantic prompt content")
        tokens = self.counter.count(compact["messages"])
        if tokens > self.config.prompt_budget:
            raise ValueError("C005HS compact target exceeds prompt budget")

        candidate_fingerprints = [
            {
                "source_id": candidate.source_id,
                "document_id": candidate.doc_id,
                "start": candidate.start,
                "end": candidate.end,
                "text_sha256": candidate.sha256,
            }
            for candidate in candidates
        ]
        rendered_path = self.output_dir / "rendered_inputs" / f"probe_{self.target}.json"
        atomic_json(rendered_path, {
            "task_id": self.target,
            "tokens": tokens,
            "messages": compact["messages"],
            "schema": compact["schema"],
            "candidate_fingerprints": candidate_fingerprints,
        })
        semantic_contract = {
            "status": "PASS",
            "target_task_id": self.target,
            "base_verbose_task_sha256": audit["task_hashes"][self.target],
            "expected_base_verbose_task_sha256": base_hashes[self.target],
            "user_message_identical": user_identical,
            "user_message_sha256": _sha256_text(str(compact["messages"][1]["content"])),
            "system_prefix_identical": system_prefix_identical,
            "semantic_system_prefix_sha256": _sha256_text(verbose_system),
            "compact_system_sha256": _sha256_text(compact_system),
            "candidate_fingerprints": candidate_fingerprints,
            "normal_responses_not_called": len(tasks) - 1,
        }
        return {
            "task": compact,
            "candidates": candidates,
            "tokens": tokens,
            "rendered_path": str(rendered_path),
            "semantic_contract": semantic_contract,
            "all_task_count": len(tasks),
        }

    def preflight_only(self) -> dict[str, Any]:
        manifest = compare_manifests(self.config.path, self.config.path.parents[2])
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")
        prepared = self.prepare()
        report = {
            "status": "PASS",
            "experiment_id": self.config.experiment_id,
            "cohort": "holdout20",
            "target_task_id": self.target,
            "logical_calls": 1,
            "max_new_calls": 1,
            "tokens": prepared["tokens"],
            "rendered_input": prepared["rendered_path"],
            "semantic_contract": prepared["semantic_contract"],
            "manifest_diff": manifest,
        }
        atomic_json(self.output_dir / "resolved_manifest.json", self.config.raw)
        atomic_json(self.output_dir / "semantic_contract.json", prepared["semantic_contract"])
        atomic_json(self.output_dir / "preflight.json", report)
        return report

    def run(self, *, mock: bool = False) -> dict[str, Any]:
        started = time.monotonic()
        preflight = self.preflight_only()
        prepared = self.prepare()
        response_path = (
            self.output_dir / "mock" / "probe_response" / f"{self.target}.json"
            if mock else self.response_dir / f"{self.target}.json"
        )
        adapted_path = (
            self.output_dir / "mock" / "adapted_response" / f"{self.target}.json"
            if mock else self.adapted_dir / f"{self.target}.json"
        )
        new_calls = 0
        if response_path.is_file():
            response = json.loads(response_path.read_text(encoding="utf-8"))
        elif mock:
            response = _compact_mock_response(prepared["task"])
            atomic_json(response_path, response)
        else:
            runtime = OpenRouterRuntime(
                self.config.provider,
                os.environ.get(self.config.provider.api_key_env, ""),
            )
            response = runtime.complete(prepared["task"])
            atomic_json(response_path, response)
            new_calls = 1
        adapted = adapt_compact_response(response, prepared["candidates"])
        if adapted is None:
            report = {
                "status": "INCOMPLETE",
                "experiment_id": self.config.experiment_id,
                "cohort": "holdout20",
                "target_task_id": self.target,
                "new_calls": new_calls,
                "normal_responses_not_called": prepared["all_task_count"] - 1,
                "compact_response_valid": False,
                "preflight_status": preflight["status"],
                "seconds": round(time.monotonic() - started, 3),
            }
            atomic_json(
                self.output_dir / ("run_report.mock.json" if mock else "run_report.json"),
                report,
            )
            return report
        parsed, reason = parse_v19_observations_relaxed_quote(
            adapted, prepared["candidates"],
        )
        if parsed is None:
            raise ValueError(f"compact adapter did not satisfy verbose parser: {reason}")
        atomic_json(adapted_path, adapted)

        if mock:
            report = {
                "status": "PASS",
                "experiment_id": self.config.experiment_id,
                "cohort": "holdout20",
                "target_task_id": self.target,
                "new_calls": 0,
                "normal_responses_not_called": prepared["all_task_count"] - 1,
                "compact_response_valid": True,
                "adapted_verbose_response_valid": True,
                "assembly_exercised": False,
                "preflight_status": preflight["status"],
                "seconds": round(time.monotonic() - started, 3),
            }
            atomic_json(self.output_dir / "run_report.mock.json", report)
            return report

        replay = V19QuoteReplay(self.config).run()
        report = {
            **replay,
            "new_calls": new_calls,
            "normal_responses_not_called": prepared["all_task_count"] - 1,
            "compact_response_valid": True,
            "adapted_verbose_response_valid": True,
            "preflight_status": preflight["status"],
            "seconds": round(time.monotonic() - started, 3),
        }
        atomic_json(self.output_dir / "run_report.json", report)
        return report
