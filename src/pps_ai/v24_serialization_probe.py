"""One-record paid diagnostic for the C002RB serialization contract."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .config import CleanExperimentConfig
from .decisions.v24_serialization_v22 import (
    build_v24_serialization_task,
    decide_v24_serialization_v22,
)
from .ingest import load_notice_records
from .preflight import compare_manifests
from .runtime.openrouter import OpenRouterRuntime, atomic_json
from .runtime.tokenizer import GemmaTokenCounter
from .views.v24_multi_observation import build_v24_multi_observation_view


def _mock_response() -> dict[str, Any]:
    return {
        "content": json.dumps({
            "amount": [], "contract": [], "region": [], "industry": [],
        }),
        "finish_reason": "stop",
        "invalid": False,
        "model": "mock",
        "usage": {},
        "latency_seconds": 0.0,
        "attempts": 1,
    }


class V24SerializationProbe:
    def __init__(self, config: CleanExperimentConfig) -> None:
        self.config = config
        self.output_dir = config.output_dir.resolve()
        policy = config.raw.get("v24_policy")
        if not isinstance(policy, dict) or policy.get("module") != "native-v24-distinct-serialization-v2.2":
            raise ValueError("v24 distinct serialization v2.2 is not selected")
        ids = policy.get("diagnostic_probe_ids")
        if not isinstance(ids, list) or len(ids) != 1 or not isinstance(ids[0], str):
            raise ValueError("C002RB requires exactly one versioned diagnostic probe ID")
        self.notice_id = ids[0]
        self.max_axis_characters = int(policy["max_axis_characters"])
        self.counter = GemmaTokenCounter(config.tokenizer_dir)

    def prepare(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], int]:
        record_object = next(
            (record for record in load_notice_records(self.config.input_path)
             if record.notice_id == self.notice_id),
            None,
        )
        if record_object is None:
            raise ValueError("diagnostic probe ID is absent from input")
        record = dict(record_object.raw)
        view = build_v24_multi_observation_view(
            record, max_axis_characters=self.max_axis_characters,
        )
        if len(view["document_coverage"]) != len(record_object.documents):
            raise ValueError("probe did not inspect every document")
        task = build_v24_serialization_task(record, view)
        tokens = self.counter.count(task["messages"])
        if tokens > self.config.prompt_budget:
            raise ValueError(f"probe prompt exceeds budget: {tokens}")
        atomic_json(self.output_dir / "rendered_input.json", {
            "id": self.notice_id,
            "tokens": tokens,
            "messages": task["messages"],
            "schema": task["schema"],
            "coverage": {
                "documents": view["document_coverage"],
                "axes": view["axis_coverage"],
                "selected_by_axis": {
                    axis: len(values) for axis, values in view["candidates"].items()
                },
            },
        })
        return record, view, task, tokens

    def preflight_only(self) -> dict[str, Any]:
        manifest = compare_manifests(self.config.path, self.config.path.parents[2])
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")
        _, view, task, tokens = self.prepare()
        report = {
            "status": "PASS",
            "manifest_diff": manifest,
            "records": 1,
            "logical_calls": 1,
            "notice_id": self.notice_id,
            "tokens": tokens,
            "task_hash": self.counter.task_sha256(task),
            "documents_inspected": len(view["document_coverage"]),
        }
        atomic_json(self.output_dir / "resolved_manifest.json", self.config.raw)
        atomic_json(self.output_dir / "preflight.json", report)
        return report

    def run(self, *, mock: bool = False) -> dict[str, Any]:
        preflight = self.preflight_only()
        record, view, task, tokens = self.prepare()
        response_path = self.output_dir / ("response.mock.json" if mock else "response.json")
        if response_path.is_file():
            response = json.loads(response_path.read_text(encoding="utf-8"))
            external_calls = 0
            resumed = True
        elif mock:
            response = _mock_response()
            atomic_json(response_path, response)
            external_calls = 0
            resumed = False
        else:
            runtime = OpenRouterRuntime(
                self.config.provider,
                os.environ.get(self.config.provider.api_key_env, ""),
            )
            response = runtime.complete(task)
            atomic_json(response_path, response)
            external_calls = 1
            resumed = False
        value, evidence, diagnostic = decide_v24_serialization_v22(record, view, response)
        completion_tokens = int((response.get("usage") or {}).get("completion_tokens") or 0)
        success = bool(
            response.get("finish_reason") == "stop"
            and not diagnostic["fallback"]
            and completion_tokens < self.config.provider.max_tokens
        )
        report = {
            "status": "PASS" if success else "FAIL",
            "experiment_id": self.config.experiment_id,
            "diagnostic_probe": True,
            "performance_result": False,
            "records": 1,
            "logical_calls": 1,
            "external_calls": external_calls,
            "resumed": resumed,
            "notice_id": self.notice_id,
            "prompt_tokens": tokens,
            "completion_tokens": completion_tokens,
            "finish_reason": response.get("finish_reason"),
            "v24": value,
            "e24": evidence,
            "diagnostic": diagnostic,
            "preflight_status": preflight["status"],
        }
        atomic_json(self.output_dir / ("run_report.mock.json" if mock else "run_report.json"), report)
        return report
