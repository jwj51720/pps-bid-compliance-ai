"""Native v24 replacement experiment over immutable L41 baseline cells."""

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
from .decisions.v24_relation import V24_SCHEMA, build_v24_task, decide_v24
from .evaluate import evaluate_rows_for_ids
from .export import write_submission_csv
from .ingest import load_notice_records
from .preflight import compare_manifests
from .runtime.openrouter import OpenRouterRuntime, atomic_json
from .runtime.tokenizer import GemmaTokenCounter
from .views.v24_relation import build_v24_relation_view


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


def _cohort_ids(config: CleanExperimentConfig, cohort: str) -> set[str]:
    if cohort == "dev200":
        return {record.notice_id for record in load_notice_records(config.input_path)}
    path = config.fast_panel_path if cohort == "fast20" else config.holdout_panel_path
    if cohort not in {"fast20", "holdout20"}:
        raise ValueError(f"unsupported cohort: {cohort}")
    return set(json.loads(path.read_text(encoding="utf-8"))["ids"])


def _mock_response() -> dict[str, Any]:
    empty = {
        axis: {
            "comparable": "U", "different": "U", "meta_field": "NONE",
            "document_role": "UNKNOWN", "document_value": None, "source_id": None,
        }
        for axis in ("amount", "contract", "region", "industry")
    }
    return {
        "content": json.dumps(empty, ensure_ascii=False),
        "finish_reason": "stop", "invalid": False, "model": "mock",
        "usage": {}, "latency_seconds": 0.0, "attempts": 1,
    }


class NativeV24Experiment:
    def __init__(
        self, config: CleanExperimentConfig, *, cohort: str,
        output_dir: Path | None = None,
    ) -> None:
        self.config = config
        self.cohort = cohort
        self.output_dir = (output_dir or config.output_dir / cohort).resolve()
        policy = config.raw.get("v24_policy")
        if not isinstance(policy, dict) or policy.get("module") != "native-v24-relation-v1":
            raise ValueError("native v24 policy is not selected")
        self.max_axis_characters = int(policy["max_axis_characters"])
        if self.max_axis_characters < 1000:
            raise ValueError("v24 axis character budget is too small")
        self.base_output_dir = (
            config.path.parents[2] / str(policy["base_output_dir"])
        ).resolve()
        if not (self.base_output_dir / "submission.csv").is_file():
            raise FileNotFoundError("baseline submission is required")
        self.counter = GemmaTokenCounter(config.tokenizer_dir)

    def prepare(self) -> tuple[
        list[Any], dict[str, dict[str, Any]],
        dict[str, dict[str, Any]], dict[str, Any],
    ]:
        ids = _cohort_ids(self.config, self.cohort)
        records = [
            record for record in load_notice_records(self.config.input_path)
            if record.notice_id in ids
        ]
        if {record.notice_id for record in records} != ids:
            raise ValueError("cohort input coverage differs")
        views: dict[str, dict[str, Any]] = {}
        tasks: dict[str, dict[str, Any]] = {}
        coverage: dict[str, Any] = {}
        tokens: dict[str, int] = {}
        for record in records:
            raw = dict(record.raw)
            view = build_v24_relation_view(
                raw, max_axis_characters=self.max_axis_characters,
            )
            if len(view["document_coverage"]) != len(record.documents):
                raise ValueError(f"{record.notice_id}: not every document was inspected")
            if any(not item["inspected"] for item in view["document_coverage"]):
                raise ValueError(f"{record.notice_id}: uninspected document")
            task = build_v24_task(raw, view)
            count = self.counter.count(task["messages"])
            if count > self.config.prompt_budget:
                raise ValueError(f"{record.notice_id}: v24 prompt exceeds budget: {count}")
            views[record.notice_id] = view
            tasks[record.notice_id] = task
            tokens[record.notice_id] = count
            coverage[record.notice_id] = {
                "documents": view["document_coverage"],
                "selected_by_axis": {
                    axis: len(values) for axis, values in view["candidates"].items()
                },
            }
        sizes = {
            record.notice_id: sum(len(document.text) for document in record.documents)
            for record in records
        }
        attachment = next(
            (record.notice_id for record in records if len(record.documents) > 1),
            min(sizes, key=sizes.get),
        )
        sample_ids = {
            "short": min(sizes, key=sizes.get),
            "attachment": attachment,
            "largest": max(tokens, key=tokens.get),
        }
        rendered = []
        for role, notice_id in sample_ids.items():
            path = self.output_dir / "rendered_inputs" / f"{role}_{notice_id}.json"
            atomic_json(path, {
                "id": notice_id, "tokens": tokens[notice_id],
                "messages": tasks[notice_id]["messages"], "schema": V24_SCHEMA,
                "coverage": coverage[notice_id],
            })
            rendered.append({"role": role, "id": notice_id, "path": str(path)})
        audit = {
            "cohort": self.cohort, "records": len(records), "logical_calls": len(tasks),
            "tokens": {
                "sum": sum(tokens.values()), "max": max(tokens.values()),
                "min": min(tokens.values()),
            },
            "task_hashes": {
                notice_id: self.counter.task_sha256(task)
                for notice_id, task in tasks.items()
            },
            "coverage": coverage, "rendered_samples": rendered,
        }
        return records, views, tasks, audit

    def preflight_only(self) -> dict[str, Any]:
        manifest = compare_manifests(self.config.path, self.config.path.parents[2])
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")
        records, _, _, audit = self.prepare()
        report = {
            "status": "PASS", "manifest_diff": manifest,
            "records": len(records), "input_audit": audit,
        }
        atomic_json(self.output_dir / "preflight.json", report)
        return report

    def run(self, *, mock: bool = False) -> dict[str, Any]:
        started = time.monotonic()
        manifest = compare_manifests(self.config.path, self.config.path.parents[2])
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")
        records, views, tasks, audit = self.prepare()
        atomic_json(self.output_dir / "preflight.json", {
            "status": "PASS", "manifest_diff": manifest, "input_audit": audit,
        })
        response_dir = self.output_dir / ("mock_responses" if mock else "responses")
        responses: dict[str, dict[str, Any]] = {}
        pending = []
        for notice_id in tasks:
            path = response_dir / f"{notice_id}.json"
            if path.is_file():
                responses[notice_id] = json.loads(path.read_text(encoding="utf-8"))
            else:
                pending.append(notice_id)
        if mock:
            for notice_id in pending:
                response = _mock_response()
                atomic_json(response_dir / f"{notice_id}.json", response)
                responses[notice_id] = response
        elif pending:
            runtime = OpenRouterRuntime(
                self.config.provider,
                os.environ.get(self.config.provider.api_key_env, ""),
            )
            with ThreadPoolExecutor(max_workers=self.config.provider.concurrency) as executor:
                futures = {
                    executor.submit(runtime.complete, tasks[notice_id]): notice_id
                    for notice_id in pending
                }
                for future in as_completed(futures):
                    notice_id = futures[future]
                    response = future.result()
                    atomic_json(response_dir / f"{notice_id}.json", response)
                    responses[notice_id] = response
        base_rows = _read_rows(self.base_output_dir / "submission.csv")
        rows = []
        observations = []
        fallback = 0
        for record in records:
            notice_id = record.notice_id
            row = dict(base_rows[notice_id])
            value, evidence, diagnostic = decide_v24(
                dict(record.raw), views[notice_id], responses[notice_id],
            )
            row["v24"], row["e24"] = value, evidence
            rows.append(row)
            observations.append({
                "id": notice_id, "v24": value, "e24": evidence,
                "diagnostic": diagnostic,
            })
            fallback += int(diagnostic["fallback"])
            for index in range(1, 24):
                if row[f"v{index}"] != base_rows[notice_id][f"v{index}"]:
                    raise ValueError(f"{notice_id}/v{index}: non-owner label changed")
                if row[f"e{index}"] != base_rows[notice_id][f"e{index}"]:
                    raise ValueError(f"{notice_id}/e{index}: non-owner evidence changed")
        write_submission_csv(
            self.output_dir / ("submission.mock.csv" if mock else "submission.csv"), rows,
        )
        observations_path = self.output_dir / ("observations.mock.json" if mock else "observations.json")
        atomic_json(observations_path, observations)
        metrics = evaluate_rows_for_ids(
            rows, self.config.labels_path, {record.notice_id for record in records}, self.cohort,
        )
        if not mock:
            atomic_json(self.output_dir / "metrics.json", {self.cohort: metrics})
        report = {
            "status": "PASS" if fallback == 0 else "INCOMPLETE",
            "experiment_id": self.config.experiment_id, "cohort": self.cohort,
            "records": len(records), "logical_calls": len(tasks),
            "resumed": len(tasks) - len(pending), "new": len(pending),
            "fallbacks": fallback, "metrics": metrics,
            "non_v24_changed_cells": 0,
            "seconds": round(time.monotonic() - started, 3),
        }
        atomic_json(
            self.output_dir / ("run_report.mock.json" if mock else "run_report.json"), report,
        )
        return report
