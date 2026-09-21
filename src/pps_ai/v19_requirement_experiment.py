"""Clean v19 requirement-instance replacement over the C004S baseline."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import json
import os
from pathlib import Path
import time
from typing import Any, Sequence

from .config import CleanExperimentConfig
from .decisions.v19_requirements import (
    build_v19_task,
    parse_v19_observations,
    reduce_v19_observations,
)
from .evaluate import evaluate_rows_for_ids
from .evidence.validation import clean_final_rows
from .export import write_submission_csv
from .ingest import load_notice_records
from .preflight import compare_manifests
from .runtime.openrouter import OpenRouterRuntime, atomic_json
from .runtime.tokenizer import GemmaTokenCounter
from .views.v19_requirements import (
    V19RequirementCandidate,
    build_v19_requirement_view,
)


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


def _percentile_95(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)]


def _mock_response(candidates: Sequence[V19RequirementCandidate]) -> dict[str, Any]:
    observations = {}
    for candidate in candidates:
        quote = candidate.text[:500]
        if not quote:
            raise ValueError("empty v19 candidate cannot be mocked")
        observations[candidate.source_id] = {
            "requirement_role": "OTHER",
            "document_kind": "OTHER_DOCUMENT",
            "external_issuer_explicit": "NO",
            "bidder_must_obtain_or_hold": "NO",
            "bidder_must_submit": "NO",
            "obtain_before_bid_deadline": "NO",
            "submit_with_bid_or_proposal": "NO",
            "submit_after_bid_or_contract": "NO",
            "quoted_text": quote,
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


class V19RequirementExperiment:
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
        policy = config.raw.get("v19_policy")
        if not isinstance(policy, dict):
            raise ValueError("v19 policy is required")
        if policy.get("module") != "v19-requirement-instance-observation-reducer-v1":
            raise ValueError("C005 v19 policy is not selected")
        self.base_output_dir = (
            config.path.parents[2] / str(policy["base_output_dir"])
        ).resolve()
        if not (self.base_output_dir / "submission.csv").is_file():
            raise FileNotFoundError("C004S baseline submission is required")
        self.review_notice_ids = tuple(str(value) for value in policy["review_notice_ids"])
        self.counter = GemmaTokenCounter(config.tokenizer_dir)

    def _pack_tasks(
        self,
        record: dict[str, Any],
        candidates: Sequence[V19RequirementCandidate],
    ) -> list[tuple[tuple[V19RequirementCandidate, ...], dict[str, Any], int]]:
        packs: list[tuple[tuple[V19RequirementCandidate, ...], dict[str, Any], int]] = []
        current: list[V19RequirementCandidate] = []
        for candidate in candidates:
            trial = tuple([*current, candidate])
            task = build_v19_task(record, trial)
            count = self.counter.count(task["messages"])
            if count <= self.config.prompt_budget:
                current.append(candidate)
                continue
            if not current:
                raise ValueError(
                    f"{record['id']}/{candidate.source_id}: one v19 candidate exceeds budget"
                )
            frozen = tuple(current)
            frozen_task = build_v19_task(record, frozen)
            frozen_count = self.counter.count(frozen_task["messages"])
            packs.append((frozen, frozen_task, frozen_count))
            current = [candidate]
            single_task = build_v19_task(record, tuple(current))
            single_count = self.counter.count(single_task["messages"])
            if single_count > self.config.prompt_budget:
                raise ValueError(
                    f"{record['id']}/{candidate.source_id}: one v19 candidate exceeds budget"
                )
        if current:
            frozen = tuple(current)
            task = build_v19_task(record, frozen)
            packs.append((frozen, task, self.counter.count(task["messages"])))
        return packs

    def prepare(self) -> tuple[
        list[Any],
        dict[str, dict[str, Any]],
        dict[str, dict[str, Any]],
        dict[str, tuple[V19RequirementCandidate, ...]],
        dict[str, Any],
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
        task_candidates: dict[str, tuple[V19RequirementCandidate, ...]] = {}
        coverage: dict[str, Any] = {}
        tokens: dict[str, int] = {}
        notice_task_ids: dict[str, list[str]] = {}
        for record in records:
            raw = dict(record.raw)
            view = build_v19_requirement_view(raw)
            if len(view["document_coverage"]) != len(record.documents):
                raise ValueError(f"{record.notice_id}: not every document was inspected")
            if any(not row["inspected"] for row in view["document_coverage"]):
                raise ValueError(f"{record.notice_id}: uninspected document")
            views[record.notice_id] = view
            packs = self._pack_tasks(raw, view["candidates"]) if view["candidates"] else []
            notice_task_ids[record.notice_id] = []
            for part, (candidates, task, count) in enumerate(packs, 1):
                task_id = f"{record.notice_id}__p{part:02d}"
                tasks[task_id] = task
                task_candidates[task_id] = candidates
                tokens[task_id] = count
                notice_task_ids[record.notice_id].append(task_id)
            coverage[record.notice_id] = {
                "documents": view["document_coverage"],
                "candidate_count": len(view["candidates"]),
                "candidate_source_ids": [value.source_id for value in view["candidates"]],
                "task_ids": notice_task_ids[record.notice_id],
                "overflow_passes": max(0, len(packs) - 1),
            }
        rendered = self._write_rendered_samples(
            records, tasks, task_candidates, coverage, tokens, notice_task_ids,
        )
        all_documents = [row for item in coverage.values() for row in item["documents"]]
        audit = {
            "cohort": self.cohort,
            "records": len(records),
            "documents_inspected": len(all_documents),
            "documents_uninspected": sum(not row["inspected"] for row in all_documents),
            "candidate_notices": sum(bool(value["candidate_count"]) for value in coverage.values()),
            "candidate_count": sum(value["candidate_count"] for value in coverage.values()),
            "specialist_logical_calls": len(tasks),
            "overflow_passes": sum(value["overflow_passes"] for value in coverage.values()),
            "tokens": {
                "sum": sum(tokens.values()),
                "min": min(tokens.values(), default=0),
                "max": max(tokens.values(), default=0),
                "p95": _percentile_95(list(tokens.values())),
            },
            "task_hashes": {
                task_id: self.counter.task_sha256(task) for task_id, task in tasks.items()
            },
            "coverage": coverage,
            "rendered_samples": rendered,
        }
        return records, views, tasks, task_candidates, audit

    def _write_rendered_samples(
        self,
        records: list[Any],
        tasks: dict[str, dict[str, Any]],
        task_candidates: dict[str, tuple[V19RequirementCandidate, ...]],
        coverage: dict[str, Any],
        tokens: dict[str, int],
        notice_task_ids: dict[str, list[str]],
    ) -> list[dict[str, Any]]:
        task_records = [record for record in records if notice_task_ids[record.notice_id]]
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
        largest_task = max(tokens, key=tokens.get)
        largest_notice = largest_task.split("__p", 1)[0]
        samples: list[tuple[str, str]] = [
            ("short", min(sizes, key=sizes.get)),
            ("attachment", attachment),
            ("largest", largest_notice),
        ]
        samples.extend(
            ("error_panel", notice_id)
            for notice_id in self.review_notice_ids
            if notice_task_ids.get(notice_id)
        )
        rendered = []
        seen: set[tuple[str, str]] = set()
        semantic_rows = []
        for role, notice_id in samples:
            if (role, notice_id) in seen:
                continue
            seen.add((role, notice_id))
            for task_id in notice_task_ids[notice_id]:
                path = self.output_dir / "rendered_inputs" / f"{role}_{task_id}.json"
                task = tasks[task_id]
                atomic_json(path, {
                    "id": notice_id,
                    "task_id": task_id,
                    "role": role,
                    "tokens": tokens[task_id],
                    "messages": task["messages"],
                    "schema": task["schema"],
                    "candidate_source_ids": [
                        value.source_id for value in task_candidates[task_id]
                    ],
                    "coverage": coverage[notice_id],
                })
                rendered.append({
                    "role": role, "id": notice_id, "task_id": task_id,
                    "path": str(path),
                })
                system = str(task["messages"][0]["content"])
                user = str(task["messages"][1]["content"])
                checks = {
                    "applicability_external_party": "외부 제조사·공급사·기술지원사" in user,
                    "one_condition_prebid_hold": "제출 전에 발급·보유" in user,
                    "one_condition_bid_submission": "입찰·제안 제출과 함께" in user,
                    "zero_capable_only": "제출 가능한 업체" in user,
                    "zero_unspecified": "시점 없는 언급" in user,
                    "zero_post_contract": "낙찰·계약 후에만 제출" in user,
                    "zero_status_certificate": "제조자·대리점 지위 증명" in user,
                    "zero_self_promise": "입찰자 자신의 이행약속" in user,
                    "no_final_label_request": "최종 위반 여부나 v19 0/1은 출력하지 않는다" in system,
                    "all_candidate_ids_rendered": all(
                        f"[{value.source_id} |" in user
                        for value in task_candidates[task_id]
                    ),
                }
                semantic_rows.append({
                    "task_id": task_id,
                    "checks": checks,
                    "status": "PASS" if all(checks.values()) else "FAIL",
                })
        atomic_json(self.output_dir / "semantic_contract.json", {
            "active_item": "v19",
            "rendered_tasks": semantic_rows,
            "status": "PASS" if semantic_rows and all(
                row["status"] == "PASS" for row in semantic_rows
            ) else "FAIL",
        })
        return rendered

    def _write_static_audit(self, audit: dict[str, Any]) -> None:
        atomic_json(self.output_dir / "resolved_manifest.json", self.config.raw)
        atomic_json(self.output_dir / "source_coverage.json", {
            key: audit[key]
            for key in (
                "cohort", "records", "documents_inspected", "documents_uninspected",
                "candidate_notices", "candidate_count", "specialist_logical_calls",
                "overflow_passes", "coverage",
            )
        })

    def preflight_only(self) -> dict[str, Any]:
        manifest = compare_manifests(self.config.path, self.config.path.parents[2])
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")
        records, _, _, _, audit = self.prepare()
        self._write_static_audit(audit)
        semantic = json.loads(
            (self.output_dir / "semantic_contract.json").read_text(encoding="utf-8")
        )
        status = "PASS" if semantic["status"] == "PASS" else "FAIL"
        report = {
            "status": status,
            "manifest_diff": manifest,
            "records": len(records),
            "input_audit": audit,
            "semantic_contract": semantic["status"],
        }
        atomic_json(self.output_dir / "preflight.json", report)
        return report

    def run(self, *, mock: bool = False) -> dict[str, Any]:
        started = time.monotonic()
        manifest = compare_manifests(self.config.path, self.config.path.parents[2])
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")
        records, views, tasks, task_candidates, audit = self.prepare()
        self._write_static_audit(audit)
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
        output_observations = []
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
                failure_reason = None
                for task_id in task_ids:
                    parsed, reason = parse_v19_observations(
                        responses[task_id], task_candidates[task_id],
                    )
                    if parsed is None:
                        failure_reason = f"{task_id}:{reason}"
                        break
                    parsed_rows.extend(parsed)
                if failure_reason is not None:
                    diagnostic = {
                        "valid": False, "fallback": True, "decision": "BASELINE",
                        "reason": failure_reason, "observations": [],
                    }
                    invalid += 1
                    fallback += 1
                else:
                    value, evidence, diagnostic = reduce_v19_observations(
                        candidates, parsed_rows,
                    )
                    row["v19"], row["e19"] = value, evidence
            candidate_rows[notice_id] = row
            output_observations.append({
                "id": notice_id, "v19": row["v19"], "e19": row["e19"],
                "diagnostic": diagnostic,
            })
            for index in range(1, 25):
                if index == 19:
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
                if index == 19:
                    continue
                if row[f"v{index}"] != base[f"v{index}"]:
                    raise ValueError(f"{row['id']}/v{index}: validation changed non-owner label")
                if row[f"e{index}"] != base[f"e{index}"]:
                    raise ValueError(f"{row['id']}/e{index}: validation changed non-owner evidence")
        output_name = "submission.mock.csv" if mock else "submission.csv"
        write_submission_csv(self.output_dir / output_name, rows)
        atomic_json(
            self.output_dir / ("observations.mock.json" if mock else "observations.json"),
            output_observations,
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
            "non_v19_changed_cells": 0,
            "evidence_validation": evidence_report,
            "v19_positive_without_evidence": sum(
                int(row["v19"] == 1 and not row["e19"]) for row in rows
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
