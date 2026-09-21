"""Clean v4 requirement-instance specialist over the fixed C005D rows."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import json
import os
from pathlib import Path
import time
from typing import Any, Mapping, Sequence

from .config import CleanExperimentConfig
from .decisions.v4_requirements import (
    build_v4_task,
    parse_v4_observations,
    reduce_v4_observations,
)
from .evaluate import evaluate_rows_for_ids
from .evidence.validation import clean_final_rows
from .export import write_submission_csv
from .ingest import load_notice_records
from .preflight import compare_manifests
from .runtime.openrouter import OpenRouterRuntime, atomic_json
from .runtime.tokenizer import GemmaTokenCounter
from .views.v4_requirements import V4RequirementCandidate, build_v4_requirement_view


def _read_rows(path: Path) -> dict[str, dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows: dict[str, dict[str, Any]] = {}
        for source in csv.DictReader(handle):
            row: dict[str, Any] = {"id": source["id"]}
            for index in range(1, 25):
                row[f"v{index}"] = int(source[f"v{index}"])
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


def _p95(values: list[int]) -> int:
    ordered = sorted(values)
    return ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)] if ordered else 0


def _mock_response(candidates: Sequence[V4RequirementCandidate]) -> dict[str, Any]:
    return {
        "content": json.dumps({
            "observations": {
                candidate.source_id: {
                    "r": "U", "m": "U", "x": "U", "a": "U", "n": "U", "q": None,
                }
                for candidate in candidates
            },
        }, ensure_ascii=False),
        "finish_reason": "stop",
        "invalid": False,
        "model": "mock",
        "usage": {},
        "latency_seconds": 0.0,
        "attempts": 1,
    }


class V4RequirementExperiment:
    def __init__(
        self, config: CleanExperimentConfig, *, cohort: str,
        output_dir: Path | None = None,
    ) -> None:
        self.config = config
        self.cohort = cohort
        self.output_dir = (output_dir or config.output_dir / cohort).resolve()
        policy = config.raw.get("v4_policy")
        if not isinstance(policy, dict):
            raise ValueError("v4 policy is required")
        if policy.get("module") != "native-v4-requirement-instances-v1":
            raise ValueError("C007B v4 policy is not selected")
        self.base_output_dir = (
            config.path.parents[2] / str(policy["base_output_dir"])
        ).resolve()
        if not (self.base_output_dir / "submission.csv").is_file():
            raise FileNotFoundError("C005D baseline submission is required")
        self.source_audit_report = (
            config.path.parents[2] / str(policy["source_audit_report"])
        ).resolve()
        if not self.source_audit_report.is_file():
            raise FileNotFoundError("C007B source audit report is required")
        self.review_notice_ids = tuple(str(value) for value in policy["review_notice_ids"])
        self.counter = GemmaTokenCounter(config.tokenizer_dir)

    def _pack(
        self, record: Mapping[str, Any], candidates: Sequence[V4RequirementCandidate],
    ) -> list[tuple[tuple[V4RequirementCandidate, ...], dict[str, Any], int]]:
        packs: list[tuple[tuple[V4RequirementCandidate, ...], dict[str, Any], int]] = []
        current: list[V4RequirementCandidate] = []
        for candidate in candidates:
            trial = tuple([*current, candidate])
            task = build_v4_task(record, trial)
            count = self.counter.count(task["messages"])
            if count <= self.config.prompt_budget:
                current.append(candidate)
                continue
            if not current:
                raise ValueError(f"{record['id']}/{candidate.source_id}: candidate exceeds budget")
            frozen = tuple(current)
            frozen_task = build_v4_task(record, frozen)
            packs.append((frozen, frozen_task, self.counter.count(frozen_task["messages"])))
            current = [candidate]
            single_task = build_v4_task(record, tuple(current))
            if self.counter.count(single_task["messages"]) > self.config.prompt_budget:
                raise ValueError(f"{record['id']}/{candidate.source_id}: candidate exceeds budget")
        if current:
            frozen = tuple(current)
            task = build_v4_task(record, frozen)
            packs.append((frozen, task, self.counter.count(task["messages"])))
        return packs

    def prepare(self) -> tuple[
        list[Any], dict[str, dict[str, Any]], dict[str, dict[str, Any]],
        dict[str, tuple[V4RequirementCandidate, ...]], dict[str, Any],
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
        task_candidates: dict[str, tuple[V4RequirementCandidate, ...]] = {}
        coverage: dict[str, Any] = {}
        tokens: dict[str, int] = {}
        for record in records:
            view = build_v4_requirement_view(record.raw)
            if len(view["document_coverage"]) != len(record.documents):
                raise ValueError(f"{record.notice_id}: document coverage differs")
            if any(not row["inspected"] for row in view["document_coverage"]):
                raise ValueError(f"{record.notice_id}: uninspected document")
            views[record.notice_id] = view
            packs = self._pack(record.raw, view["candidates"]) if view["candidates"] else []
            task_ids = []
            for part, (candidates, task, count) in enumerate(packs, 1):
                task_id = f"{record.notice_id}__p{part:02d}"
                tasks[task_id] = task
                task_candidates[task_id] = candidates
                tokens[task_id] = count
                task_ids.append(task_id)
            coverage[record.notice_id] = {
                "documents": view["document_coverage"],
                "candidate_count": len(view["candidates"]),
                "candidate_source_ids": [value.source_id for value in view["candidates"]],
                "task_ids": task_ids,
                "overflow_passes": max(0, len(packs) - 1),
            }
        task_hashes = {task_id: self.counter.task_sha256(task) for task_id, task in tasks.items()}
        source_audit = json.loads(self.source_audit_report.read_text(encoding="utf-8"))
        audited_hashes = source_audit["admitted_tasks"]["task_hashes"]
        mismatches = {
            task_id: {"prepared": digest, "audited": audited_hashes.get(task_id)}
            for task_id, digest in task_hashes.items()
            if audited_hashes.get(task_id) != digest
        }
        if mismatches:
            raise ValueError(f"task hashes differ from source audit: {list(mismatches)[:3]}")
        rendered = self._write_rendered(records, tasks, task_candidates, coverage, tokens)
        all_documents = [row for item in coverage.values() for row in item["documents"]]
        audit = {
            "cohort": self.cohort,
            "records": len(records),
            "documents_inspected": len(all_documents),
            "documents_uninspected": sum(not row["inspected"] for row in all_documents),
            "candidate_notices": sum(bool(item["candidate_count"]) for item in coverage.values()),
            "candidate_count": sum(item["candidate_count"] for item in coverage.values()),
            "specialist_logical_calls": len(tasks),
            "overflow_passes": sum(item["overflow_passes"] for item in coverage.values()),
            "tokens": {
                "sum": sum(tokens.values()),
                "min": min(tokens.values(), default=0),
                "p95": _p95(list(tokens.values())),
                "max": max(tokens.values(), default=0),
            },
            "task_hashes": task_hashes,
            "source_audit_hash_match": len(task_hashes),
            "coverage": coverage,
            "rendered_samples": rendered,
        }
        return records, views, tasks, task_candidates, audit

    def _write_rendered(
        self, records: list[Any], tasks: Mapping[str, dict[str, Any]],
        task_candidates: Mapping[str, tuple[V4RequirementCandidate, ...]],
        coverage: Mapping[str, Any], tokens: Mapping[str, int],
    ) -> list[dict[str, Any]]:
        candidate_records = [record for record in records if coverage[record.notice_id]["task_ids"]]
        if not candidate_records:
            return []
        sizes = {
            record.notice_id: sum(len(document.text) for document in record.documents)
            for record in candidate_records
        }
        attachment = next(
            (record.notice_id for record in candidate_records if len(record.documents) > 1),
            min(sizes, key=sizes.get),
        )
        largest_task = max(tokens, key=tokens.get)
        samples = [
            ("short", min(sizes, key=sizes.get)),
            ("attachment", attachment),
            ("largest", largest_task.split("__p", 1)[0]),
        ]
        samples.extend(
            ("error_panel", notice_id)
            for notice_id in self.review_notice_ids
            if coverage.get(notice_id, {}).get("task_ids")
        )
        result = []
        semantic = []
        seen: set[tuple[str, str]] = set()
        for role, notice_id in samples:
            if (role, notice_id) in seen:
                continue
            seen.add((role, notice_id))
            for task_id in coverage[notice_id]["task_ids"]:
                task = tasks[task_id]
                path = self.output_dir / "rendered_inputs" / f"{role}_{task_id}.json"
                atomic_json(path, {
                    "id": notice_id,
                    "task_id": task_id,
                    "role": role,
                    "tokens": tokens[task_id],
                    "messages": task["messages"],
                    "schema": task["schema"],
                    "candidate_source_ids": [
                        candidate.source_id for candidate in task_candidates[task_id]
                    ],
                    "coverage": coverage[notice_id],
                })
                result.append({"role": role, "id": notice_id, "task_id": task_id, "path": str(path)})
                system = str(task["messages"][0]["content"])
                user = str(task["messages"][1]["content"])
                checks = {
                    "qualification": "실제 입찰 참가자격" in user,
                    "one_relation": "특정 발주기관군" in user and "특정 사업명·대상·방식" in user,
                    "allowance": "민간·해외·동등·일반 유사실적 허용" in user,
                    "necessity": "구체적 필요" in user,
                    "zero_roles": "평가·가점, 증빙서식, 계약 후 조건" in user,
                    "no_final": "최종 v4나 위반 0/1은 출력하지 않는다" in system,
                    "all_candidates": all(
                        f"[{candidate.source_id} |" in user
                        for candidate in task_candidates[task_id]
                    ),
                }
                semantic.append({
                    "task_id": task_id,
                    "checks": checks,
                    "status": "PASS" if all(checks.values()) else "FAIL",
                })
        contract = {
            "active_item": "v4",
            "inherited_items": [f"v{index}" for index in range(1, 25) if index != 4],
            "inherited_contract": "C005D byte-identical stored rows; no new prompt",
            "rendered_tasks": semantic,
            "status": "PASS" if semantic and all(row["status"] == "PASS" for row in semantic) else "FAIL",
        }
        atomic_json(self.output_dir / "semantic_contract.json", contract)
        return result

    def preflight_only(self) -> dict[str, Any]:
        manifest = compare_manifests(self.config.path, self.config.path.parents[2])
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")
        records, _, _, _, audit = self.prepare()
        contract = json.loads((self.output_dir / "semantic_contract.json").read_text(encoding="utf-8"))
        report = {
            "status": "PASS" if contract["status"] == "PASS" else "FAIL",
            "manifest_diff": manifest,
            "records": len(records),
            "input_audit": audit,
            "semantic_contract": contract["status"],
        }
        atomic_json(self.output_dir / "preflight.json", report)
        return report

    def run(self, *, mock: bool = False) -> dict[str, Any]:
        started = time.monotonic()
        manifest = compare_manifests(self.config.path, self.config.path.parents[2])
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")
        records, views, tasks, task_candidates, audit = self.prepare()
        response_dir = self.output_dir / ("mock_responses" if mock else "responses")
        responses: dict[str, dict[str, Any]] = {}
        pending = []
        for task_id in tasks:
            path = response_dir / f"{task_id}.json"
            if path.is_file():
                responses[task_id] = json.loads(path.read_text(encoding="utf-8"))
            else:
                pending.append(task_id)
        if mock:
            for task_id in pending:
                response = _mock_response(task_candidates[task_id])
                atomic_json(response_dir / f"{task_id}.json", response)
                responses[task_id] = response
        elif pending:
            runtime = OpenRouterRuntime(
                self.config.provider,
                os.environ.get(self.config.provider.api_key_env, ""),
            )
            with ThreadPoolExecutor(max_workers=self.config.provider.concurrency) as executor:
                futures = {
                    executor.submit(runtime.complete, tasks[task_id]): task_id
                    for task_id in pending
                }
                for future in as_completed(futures):
                    task_id = futures[future]
                    response = future.result()
                    atomic_json(response_dir / f"{task_id}.json", response)
                    responses[task_id] = response

        base_rows = _read_rows(self.base_output_dir / "submission.csv")
        candidate_rows: dict[str, dict[str, Any]] = {}
        observation_output = []
        invalid = 0
        fallback = 0
        for record in records:
            notice_id = record.notice_id
            row = dict(base_rows[notice_id])
            candidates = tuple(views[notice_id]["candidates"])
            task_ids = audit["coverage"][notice_id]["task_ids"]
            if not candidates:
                diagnostic = {
                    "valid": True, "fallback": True, "decision": "BASELINE",
                    "reason": "no_candidate", "observations": [],
                }
                fallback += 1
            else:
                parsed_rows = []
                failure = None
                for task_id in task_ids:
                    parsed, reason = parse_v4_observations(
                        responses[task_id], task_candidates[task_id],
                    )
                    if parsed is None:
                        failure = f"{task_id}:{reason}"
                        break
                    parsed_rows.extend(parsed)
                if failure:
                    diagnostic = {
                        "valid": False, "fallback": True, "decision": "BASELINE",
                        "reason": failure, "observations": [],
                    }
                    invalid += 1
                    fallback += 1
                else:
                    value, evidence, diagnostic = reduce_v4_observations(
                        parsed_rows, candidates, row["v4"], row["e4"],
                    )
                    row["v4"], row["e4"] = value, evidence
                    fallback += int(bool(diagnostic["fallback"]))
            candidate_rows[notice_id] = row
            observation_output.append({
                "id": notice_id, "v4": row["v4"], "e4": row["e4"],
                "diagnostic": diagnostic,
            })
            for index in range(1, 25):
                if index == 4:
                    continue
                if row[f"v{index}"] != base_rows[notice_id][f"v{index}"]:
                    raise ValueError(f"{notice_id}/v{index}: non-owner label changed")
                if row[f"e{index}"] != base_rows[notice_id][f"e{index}"]:
                    raise ValueError(f"{notice_id}/e{index}: non-owner evidence changed")

        rows, evidence_report = clean_final_rows(
            [dict(record.raw) for record in records], candidate_rows,
        )
        for row in rows:
            base = base_rows[str(row["id"])]
            for index in range(1, 25):
                if index == 4:
                    continue
                if row[f"v{index}"] != base[f"v{index}"] or row[f"e{index}"] != base[f"e{index}"]:
                    raise ValueError(f"{row['id']}/v{index}: validation changed non-owner cell")
        output_name = "submission.mock.csv" if mock else "submission.csv"
        write_submission_csv(self.output_dir / output_name, rows)
        atomic_json(
            self.output_dir / ("observations.mock.json" if mock else "observations.json"),
            observation_output,
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
        report = {
            "status": "PASS" if invalid == 0 else "INCOMPLETE",
            "experiment_id": self.config.experiment_id,
            "cohort": self.cohort,
            "records": len(records),
            "stored_base_calls_replayed": 0,
            "specialist_logical_calls": len(tasks),
            "resumed_specialist_calls": len(tasks) - len(pending),
            "new_specialist_calls": len(pending),
            "candidate_notices": audit["candidate_notices"],
            "overflow_passes": audit["overflow_passes"],
            "invalid_responses": invalid,
            "fallbacks": fallback,
            "metrics": metrics,
            "non_v4_changed_cells": 0,
            "evidence_validation": evidence_report,
            "v4_positive_without_evidence": sum(
                int(row["v4"] == 1 and not row["e4"]) for row in rows
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
