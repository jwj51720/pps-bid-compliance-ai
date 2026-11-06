"""Clean v3 monetary replacement over immutable L41 baseline cells."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import json
import os
from pathlib import Path
import time
from typing import Any

from .config import CleanExperimentConfig
from .decisions.v3_monetary import (
    build_v3_monetary_task,
    decide_v3_monetary,
)
from .decisions.v3_keyed_serialization import build_v3_keyed_task, decide_v3_keyed
from .evaluate import evaluate_rows_for_ids
from .evidence.validation import clean_final_rows
from .export import write_submission_csv
from .ingest import load_notice_records
from .preflight import compare_manifests
from .runtime.openrouter import OpenRouterRuntime, atomic_json
from .runtime.tokenizer import GemmaTokenCounter
from .views.v3_monetary import build_v3_monetary_view


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
    if cohort not in {"fast20", "holdout20"}:
        raise ValueError(f"unsupported cohort: {cohort}")
    path = config.fast_panel_path if cohort == "fast20" else config.holdout_panel_path
    return set(json.loads(path.read_text(encoding="utf-8"))["ids"])


def _mock_response(view: dict[str, Any], serialization: str) -> dict[str, Any]:
    values = {
        candidate.source_id: {
            "role": "OTHER",
            "requirement_basis": "UNKNOWN",
            "mandatory": "UNKNOWN",
            "amount_surface": None,
        }
        for candidate in view["candidates"]
    }
    if serialization == "candidate-keyed-object-v11":
        observations: Any = values
    else:
        observations = [
            {"source_id": source_id, **value} for source_id, value in values.items()
        ]
    return {
        "content": json.dumps({"observations": observations}, ensure_ascii=False),
        "finish_reason": "stop",
        "invalid": False,
        "model": "mock",
        "usage": {},
        "latency_seconds": 0.0,
        "attempts": 1,
    }


def _percentile_95(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)]


class V3MonetaryExperiment:
    def __init__(
        self,
        config: CleanExperimentConfig,
        *,
        cohort: str,
        output_dir: Path | None = None,
    ) -> None:
        self.config = config
        self.cohort = cohort
        self.output_dir = (output_dir or config.output_dir / cohort).resolve()
        policy = config.raw.get("v3_policy")
        if not isinstance(policy, dict) or policy.get("module") != "native-v3-monetary-v1":
            raise ValueError("native v3 monetary policy is not selected")
        self.base_output_dir = (
            config.path.parents[2] / str(policy["base_output_dir"])
        ).resolve()
        if not (self.base_output_dir / "submission.csv").is_file():
            raise FileNotFoundError("baseline submission is required")
        serialization = config.raw.get("v3_serialization") or {
            "module": "source-id-array-v1",
        }
        if not isinstance(serialization, dict):
            raise ValueError("v3 serialization policy must be an object")
        self.serialization = str(serialization.get("module"))
        if self.serialization not in {"source-id-array-v1", "candidate-keyed-object-v11"}:
            raise ValueError("unsupported v3 serialization policy")
        self.review_notice_ids = tuple(str(value) for value in policy["review_notice_ids"])
        self.counter = GemmaTokenCounter(config.tokenizer_dir)

    def prepare(self) -> tuple[
        list[Any], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any],
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
            view = build_v3_monetary_view(raw)
            if len(view["document_coverage"]) != len(record.documents):
                raise ValueError(f"{record.notice_id}: not every document was inspected")
            if any(not row["inspected"] for row in view["document_coverage"]):
                raise ValueError(f"{record.notice_id}: uninspected document")
            views[record.notice_id] = view
            coverage[record.notice_id] = {
                "documents": view["document_coverage"],
                "candidate_count": len(view["candidates"]),
                "candidate_source_ids": [value.source_id for value in view["candidates"]],
            }
            if not view["candidates"]:
                continue
            task = (
                build_v3_keyed_task(raw, view)
                if self.serialization == "candidate-keyed-object-v11"
                else build_v3_monetary_task(raw, view)
            )
            count = self.counter.count(task["messages"])
            if count > self.config.prompt_budget:
                raise ValueError(f"{record.notice_id}: v3 prompt exceeds budget: {count}")
            tasks[record.notice_id] = task
            tokens[record.notice_id] = count

        rendered = self._write_rendered_samples(records, views, tasks, coverage, tokens)
        all_documents = [
            row for notice in coverage.values() for row in notice["documents"]
        ]
        audit = {
            "cohort": self.cohort,
            "records": len(records),
            "baseline_logical_calls": 3 * len(records),
            "specialist_logical_calls": len(tasks),
            "total_logical_calls": 3 * len(records) + len(tasks),
            "documents_inspected": len(all_documents),
            "documents_uninspected": sum(not row["inspected"] for row in all_documents),
            "candidate_notices": len(tasks),
            "candidate_count": sum(value["candidate_count"] for value in coverage.values()),
            "tokens": {
                "sum": sum(tokens.values()),
                "max": max(tokens.values(), default=0),
                "min": min(tokens.values(), default=0),
                "p95": _percentile_95(list(tokens.values())),
            },
            "task_hashes": {
                notice_id: self.counter.task_sha256(task)
                for notice_id, task in tasks.items()
            },
            "coverage": coverage,
            "rendered_samples": rendered,
        }
        return records, views, tasks, audit

    def _write_rendered_samples(
        self,
        records: list[Any],
        views: dict[str, dict[str, Any]],
        tasks: dict[str, dict[str, Any]],
        coverage: dict[str, Any],
        tokens: dict[str, int],
    ) -> list[dict[str, Any]]:
        task_records = [record for record in records if record.notice_id in tasks]
        if not task_records:
            return []
        sizes = {
            record.notice_id: sum(len(document.text) for document in record.documents)
            for record in task_records
        }
        attachment = next(
            (record.notice_id for record in task_records if len(record.documents) > 1),
            min(sizes, key=sizes.get),
        )
        samples: list[tuple[str, str]] = [
            ("short", min(sizes, key=sizes.get)),
            ("attachment", attachment),
            ("largest", max(tokens, key=tokens.get)),
        ]
        samples.extend(
            ("error_panel", notice_id)
            for notice_id in self.review_notice_ids if notice_id in tasks
        )
        rendered = []
        seen: set[tuple[str, str]] = set()
        for role, notice_id in samples:
            if (role, notice_id) in seen:
                continue
            seen.add((role, notice_id))
            path = self.output_dir / "rendered_inputs" / f"{role}_{notice_id}.json"
            atomic_json(path, {
                "id": notice_id,
                "role": role,
                "tokens": tokens[notice_id],
                "messages": tasks[notice_id]["messages"],
                "schema": tasks[notice_id]["schema"],
                "coverage": coverage[notice_id],
            })
            rendered.append({"role": role, "id": notice_id, "path": str(path)})
        return rendered

    def _write_static_audit(self, audit: dict[str, Any]) -> None:
        atomic_json(self.output_dir / "resolved_manifest.json", self.config.raw)
        atomic_json(self.output_dir / "source_coverage.json", {
            "cohort": self.cohort,
            "documents_inspected": audit["documents_inspected"],
            "documents_uninspected": audit["documents_uninspected"],
            "candidate_notices": audit["candidate_notices"],
            "candidate_count": audit["candidate_count"],
            "coverage": audit["coverage"],
        })

    def preflight_only(self) -> dict[str, Any]:
        manifest = compare_manifests(self.config.path, self.config.path.parents[2])
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")
        records, _, _, audit = self.prepare()
        self._write_static_audit(audit)
        report = {
            "status": "PASS",
            "manifest_diff": manifest,
            "records": len(records),
            "input_audit": audit,
        }
        atomic_json(self.output_dir / "preflight.json", report)
        return report

    def run(self, *, mock: bool = False) -> dict[str, Any]:
        started = time.monotonic()
        manifest = compare_manifests(self.config.path, self.config.path.parents[2])
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")
        records, views, tasks, audit = self.prepare()
        self._write_static_audit(audit)
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
                response = _mock_response(views[notice_id], self.serialization)
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
        candidate_rows: dict[str, dict[str, Any]] = {}
        observations = []
        fallback = 0
        for record in records:
            notice_id = record.notice_id
            row = dict(base_rows[notice_id])
            if notice_id in tasks:
                decide = (
                    decide_v3_keyed
                    if self.serialization == "candidate-keyed-object-v11"
                    else decide_v3_monetary
                )
                value, evidence, diagnostic = decide(
                    dict(record.raw), views[notice_id], responses[notice_id],
                    int(row["v3"]), str(row["e3"]),
                )
                row["v3"], row["e3"] = value, evidence
                fallback += int(diagnostic["fallback"])
            else:
                diagnostic = {
                    "valid": True, "fallback": True, "decision": "BASELINE",
                    "reason": "no_monetary_candidate", "observations": [],
                }
            candidate_rows[notice_id] = row
            observations.append({
                "id": notice_id, "v3": row["v3"], "e3": row["e3"],
                "diagnostic": diagnostic,
            })
            for index in range(1, 25):
                if index == 3:
                    continue
                if row[f"v{index}"] != base_rows[notice_id][f"v{index}"]:
                    raise ValueError(f"{notice_id}/v{index}: non-owner label changed")
                if row[f"e{index}"] != base_rows[notice_id][f"e{index}"]:
                    raise ValueError(f"{notice_id}/e{index}: non-owner evidence changed")

        raw_records = [dict(record.raw) for record in records]
        rows, evidence_report = clean_final_rows(raw_records, candidate_rows)
        for row in rows:
            base = base_rows[str(row["id"])]
            for index in range(1, 25):
                if index == 3:
                    continue
                if row[f"v{index}"] != base[f"v{index}"]:
                    raise ValueError(f"{row['id']}/v{index}: validation changed non-owner label")
                if row[f"e{index}"] != base[f"e{index}"]:
                    raise ValueError(f"{row['id']}/e{index}: validation changed non-owner evidence")
        output_name = "submission.mock.csv" if mock else "submission.csv"
        write_submission_csv(self.output_dir / output_name, rows)
        atomic_json(
            self.output_dir / ("observations.mock.json" if mock else "observations.json"),
            observations,
        )
        metrics = evaluate_rows_for_ids(
            rows, self.config.labels_path,
            {record.notice_id for record in records}, self.cohort,
        )
        if not mock:
            atomic_json(self.output_dir / "metrics.json", {self.cohort: metrics})
        prompt_tokens = [
            int((response.get("usage") or {}).get("prompt_tokens") or 0)
            for response in responses.values()
        ]
        completion_tokens = [
            int((response.get("usage") or {}).get("completion_tokens") or 0)
            for response in responses.values()
        ]
        invalid_responses = sum(
            int(not observation["diagnostic"].get("valid", False))
            for observation in observations
            if observation["id"] in tasks
        )
        semantic_fallbacks = sum(
            int(
                observation["diagnostic"].get("valid", False)
                and observation["diagnostic"].get("fallback", False)
            )
            for observation in observations
            if observation["id"] in tasks
        )
        if self.serialization == "candidate-keyed-object-v11":
            status = "PASS" if invalid_responses == 0 else "INCOMPLETE"
        else:
            status = "PASS" if mock or fallback == 0 else "INCOMPLETE"
        report = {
            "status": status,
            "experiment_id": self.config.experiment_id,
            "cohort": self.cohort,
            "records": len(records),
            "baseline_logical_calls": audit["baseline_logical_calls"],
            "specialist_logical_calls": len(tasks),
            "total_logical_calls": audit["total_logical_calls"],
            "resumed_specialist_calls": len(tasks) - len(pending),
            "new_specialist_calls": len(pending),
            "fallbacks_on_candidate_notices": fallback,
            "invalid_responses": invalid_responses,
            "semantic_fallbacks": semantic_fallbacks,
            "serialization": self.serialization,
            "metrics": metrics,
            "non_v3_changed_cells": 0,
            "evidence_validation": evidence_report,
            "v3_positive_without_evidence": sum(
                int(row["v3"] == 1 and not row["e3"]) for row in rows
            ),
            "usage": {
                "prompt_tokens_sum": sum(prompt_tokens),
                "prompt_tokens_max": max(prompt_tokens, default=0),
                "completion_tokens_sum": sum(completion_tokens),
                "completion_tokens_max": max(completion_tokens, default=0),
            },
            "seconds": round(time.monotonic() - started, 3),
        }
        atomic_json(
            self.output_dir / ("run_report.mock.json" if mock else "run_report.json"),
            report,
        )
        return report
