"""Two-record serialization probe for candidate-keyed v3 output."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import time
from typing import Any

from .config import CleanExperimentConfig
from .decisions.v3_keyed_serialization import build_v3_keyed_task, decide_v3_keyed
from .decisions.v3_monetary import build_v3_monetary_task
from .ingest import load_notice_records
from .preflight import compare_manifests
from .runtime.openrouter import OpenRouterRuntime, atomic_json
from .runtime.tokenizer import GemmaTokenCounter
from .views.v3_monetary import build_v3_monetary_view


def _base_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["id"]: row for row in csv.DictReader(handle)}


class V3KeyedSerializationProbe:
    def __init__(self, config: CleanExperimentConfig) -> None:
        self.config = config
        self.output_dir = config.output_dir.resolve()
        policy = config.raw.get("v3_serialization_probe")
        if not isinstance(policy, dict) or policy.get("module") != "v3-keyed-serialization-v11":
            raise ValueError("v3 keyed serialization probe is not selected")
        self.notice_ids = tuple(str(value) for value in policy["notice_ids"])
        if self.notice_ids != ("PPS-DEV-165", "PPS-DEV-169"):
            raise ValueError("probe notice set differs from the two C004 serialization failures")
        root = config.path.parents[2]
        self.base_output_dir = (root / str(policy["base_output_dir"])).resolve()
        self.base_response_dir = (root / str(policy["base_response_dir"])).resolve()
        if not (self.base_output_dir / "submission.csv").is_file():
            raise FileNotFoundError("C004 fast20 submission is required")
        missing_responses = [
            notice_id for notice_id in self.notice_ids
            if not (self.base_response_dir / f"{notice_id}.json").is_file()
        ]
        if missing_responses:
            raise FileNotFoundError(f"missing C004 failed responses: {missing_responses}")
        self.counter = GemmaTokenCounter(config.tokenizer_dir)

    def prepare(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        records = {
            record.notice_id: record
            for record in load_notice_records(self.config.input_path)
            if record.notice_id in self.notice_ids
        }
        if set(records) != set(self.notice_ids):
            raise ValueError("probe input coverage differs")
        views: dict[str, Any] = {}
        tasks: dict[str, Any] = {}
        rendered = []
        semantic_contract = []
        for notice_id in self.notice_ids:
            record = records[notice_id]
            view = build_v3_monetary_view(record.raw)
            if not view["candidates"]:
                raise ValueError(f"{notice_id}: probe has no candidates")
            base_task = build_v3_monetary_task(record.raw, view)
            task = build_v3_keyed_task(record.raw, view)
            user_identical = task["messages"][1] == base_task["messages"][1]
            system_change_is_serialization_only = (
                task["messages"][0]["content"].replace(
                    "observations 객체에는 아래의 모든 candidate ID를 각각 정확히 한 번 key로 사용한다.\n"
                    "각 key의 value에는 그 candidate의 분류만 출력하며 source_id 필드를 다시 쓰지 않는다.",
                    "아래의 모든 candidate를 source_id별로 정확히 한 번씩\n"
                    "분류한다. candidate를 빠뜨리거나 같은 source_id를 중복 출력하지 않는다.",
                )
                == base_task["messages"][0]["content"]
            )
            if not user_identical or not system_change_is_serialization_only:
                raise ValueError(f"{notice_id}: keyed task changed semantic prompt content")
            tokens = self.counter.count(task["messages"])
            if tokens > self.config.prompt_budget:
                raise ValueError(f"{notice_id}: keyed task exceeds budget")
            path = self.output_dir / "rendered_inputs" / f"probe_{notice_id}.json"
            atomic_json(path, {
                "id": notice_id,
                "tokens": tokens,
                "messages": task["messages"],
                "schema": task["schema"],
                "candidate_source_ids": [value.source_id for value in view["candidates"]],
            })
            views[notice_id] = view
            tasks[notice_id] = task
            rendered.append({"id": notice_id, "tokens": tokens, "path": str(path)})
            semantic_contract.append({
                "id": notice_id,
                "user_message_identical": user_identical,
                "system_change_is_serialization_only": system_change_is_serialization_only,
                "candidate_source_ids": [value.source_id for value in view["candidates"]],
                "base_response_path": str(self.base_response_dir / f"{notice_id}.json"),
            })
        audit = {
            "records": len(records),
            "logical_calls": len(tasks),
            "rendered_inputs": rendered,
            "semantic_contract": semantic_contract,
            "task_hashes": {
                notice_id: self.counter.task_sha256(task)
                for notice_id, task in tasks.items()
            },
        }
        return records, views, {"tasks": tasks, "audit": audit}

    def preflight_only(self) -> dict[str, Any]:
        manifest = compare_manifests(self.config.path, self.config.path.parents[2])
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")
        _, _, prepared = self.prepare()
        report = {
            "status": "PASS",
            "records": len(self.notice_ids),
            "manifest_diff": manifest,
            "input_audit": prepared["audit"],
        }
        atomic_json(self.output_dir / "resolved_manifest.json", self.config.raw)
        atomic_json(self.output_dir / "preflight.json", report)
        return report

    def run(self) -> dict[str, Any]:
        started = time.monotonic()
        preflight = self.preflight_only()
        records, views, prepared = self.prepare()
        tasks = prepared["tasks"]
        response_dir = self.output_dir / "responses"
        runtime = OpenRouterRuntime(
            self.config.provider,
            os.environ.get(self.config.provider.api_key_env, ""),
        )
        responses: dict[str, dict[str, Any]] = {}
        new_calls = 0
        for notice_id in self.notice_ids:
            path = response_dir / f"{notice_id}.json"
            if path.is_file():
                responses[notice_id] = json.loads(path.read_text(encoding="utf-8"))
                continue
            response = runtime.complete(tasks[notice_id])
            atomic_json(path, response)
            responses[notice_id] = response
            new_calls += 1

        base_rows = _base_rows(self.base_output_dir / "submission.csv")
        observations = []
        valid = 0
        same_final = 0
        for notice_id in self.notice_ids:
            row = base_rows[notice_id]
            value, evidence, diagnostic = decide_v3_keyed(
                records[notice_id].raw,
                views[notice_id],
                responses[notice_id],
                int(row["v3"]),
                row["e3"],
            )
            valid += int(bool(diagnostic["valid"]))
            unchanged = value == int(row["v3"]) and evidence == row["e3"]
            same_final += int(unchanged)
            observations.append({
                "id": notice_id,
                "v3": value,
                "e3": evidence,
                "same_as_c004_final": unchanged,
                "diagnostic": diagnostic,
            })
        status = "PASS" if valid == len(self.notice_ids) and same_final == len(self.notice_ids) else "FAIL"
        report = {
            "status": status,
            "records": len(self.notice_ids),
            "logical_calls": len(self.notice_ids),
            "new_calls": new_calls,
            "valid_keyed_responses": valid,
            "same_as_c004_final": same_final,
            "preflight_status": preflight["status"],
            "seconds": round(time.monotonic() - started, 3),
        }
        atomic_json(self.output_dir / "observations.json", observations)
        atomic_json(self.output_dir / "run_report.json", report)
        return report
