"""Exact-task positive-only repeat diagnostic for the native v19 owner."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Mapping, Sequence

from .config import CleanExperimentConfig
from .decisions.v19_quote_resolution_v2 import (
    parse_v19_observations_relaxed_quote,
    reduce_v19_with_quote_resolution,
)
from .evaluate import evaluate_rows_for_ids
from .export import write_submission_csv
from .preflight import compare_manifests
from .runtime.openrouter import OpenRouterRuntime, atomic_json
from .v19_requirement_experiment import V19RequirementExperiment, _mock_response


def _read_rows(path: Path) -> dict[str, dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        result: dict[str, dict[str, Any]] = {}
        for source in csv.DictReader(handle):
            row: dict[str, Any] = {"id": source["id"]}
            for index in range(1, 25):
                row[f"v{index}"] = int(source[f"v{index}"])
            for index in range(1, 25):
                row[f"e{index}"] = source[f"e{index}"]
            result[str(row["id"])] = row
        return result


def _read_labels(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {str(row["id"]): row for row in csv.DictReader(handle)}


def _preflight_hashes(path: Path) -> dict[str, str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(task_id): str(digest)
        for task_id, digest in value["input_audit"]["task_hashes"].items()
    }


def positive_f1(tp: int, fp: int, fn: int) -> float:
    denominator = 2 * tp + fp + fn
    return 2 * tp / denominator if denominator else 0.0


JSON_FENCE = re.compile(
    r"\A```(?:json)?[ \t]*\r?\n([\s\S]*?)\r?\n```\Z",
    flags=re.IGNORECASE,
)


def adapt_single_json_fence(
    response: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Remove one outer JSON fence without changing its inner JSON payload."""
    adapted = dict(response)
    content = response.get("content")
    if not isinstance(content, str):
        return adapted, {"recovered": False, "reason": "non_string_content"}
    match = JSON_FENCE.fullmatch(content)
    if match is None:
        return adapted, {"recovered": False, "reason": "no_single_outer_fence"}
    inner = match.group(1)
    try:
        parsed = json.loads(inner)
    except (TypeError, ValueError):
        return adapted, {"recovered": False, "reason": "invalid_inner_json"}
    if not isinstance(parsed, dict):
        return adapted, {"recovered": False, "reason": "inner_json_not_object"}
    adapted["content"] = inner
    return adapted, {
        "recovered": True,
        "reason": "single_outer_json_fence",
        "inner_object_exact": json.loads(str(adapted["content"])) == parsed,
    }


def repeat_gate(
    rows: Sequence[Mapping[str, Any]], *, baseline_f1: float,
) -> dict[str, Any]:
    tp_total = sum(int(row["truth"] == 1) for row in rows)
    fp_total = sum(int(row["truth"] == 0) for row in rows)
    tp_kept = sum(int(row["truth"] == 1 and row["repeat_value"] == 1) for row in rows)
    fp_kept = sum(int(row["truth"] == 0 and row["repeat_value"] == 1) for row in rows)
    fn = tp_total - tp_kept
    f1 = positive_f1(tp_kept, fp_kept, fn)
    checks = {
        "all_semantic_valid": all(bool(row["semantic_valid"]) for row in rows),
        "tp_repeat_positive_at_least_5_of_6": tp_total == 6 and tp_kept >= 5,
        "fp_repeat_positive_at_most_3_of_4": fp_total == 4 and fp_kept <= 3,
        "consensus_f1_strictly_improves": f1 > baseline_f1,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "primary_positive_truth_counts": {"positive": tp_total, "negative": fp_total},
        "consensus": {"tp": tp_kept, "fp": fp_kept, "fn": fn, "f1": f1},
        "baseline_f1": baseline_f1,
    }


class V19PositiveRepeatDiagnostic:
    def __init__(self, config: CleanExperimentConfig) -> None:
        self.config = config
        self.root = config.path.parents[2]
        self.output_dir = config.output_dir.resolve()
        policy = config.raw.get("v19_positive_repeat_diagnostic")
        if not isinstance(policy, dict):
            raise ValueError("v19 positive-repeat policy is required")
        self.policy = policy
        self.selected_task_ids = tuple(str(value) for value in policy["selected_task_ids"])
        if len(self.selected_task_ids) != 10 or len(set(self.selected_task_ids)) != 10:
            raise ValueError("S016 requires exactly ten unique predeclared tasks")
        self.paths = {
            key: (self.root / str(value)).resolve()
            for key, value in policy.items()
            if key.endswith("_path") or key.endswith("_dir")
        }
        self.existing_repeat_paths = {
            str(task_id): (self.root / str(value)).resolve()
            for task_id, value in policy["existing_repeat_responses"].items()
        }
        replay = config.raw.get("json_fence_serialization_recovery")
        self.replay_policy = replay if isinstance(replay, dict) else None
        self.replay_source_dir: Path | None = None
        if self.replay_policy is not None:
            if self.replay_policy.get("module") != "single-outer-json-fence-adapter-v1":
                raise ValueError("unsupported JSON fence recovery module")
            if int(self.replay_policy.get("llm_calls", -1)) != 0:
                raise ValueError("JSON fence replay must use zero LLM calls")
            self.replay_source_dir = (
                self.root / str(self.replay_policy["source_response_dir"])
            ).resolve()
        self.experiment = V19RequirementExperiment(
            config, cohort="dev200", output_dir=self.output_dir,
        )

    def _prepare(self) -> dict[str, Any]:
        for path in (*self.paths.values(), *self.existing_repeat_paths.values()):
            if not path.exists():
                raise FileNotFoundError(path)
        if self.replay_source_dir is not None and not self.replay_source_dir.is_dir():
            raise FileNotFoundError(self.replay_source_dir)
        records, views, tasks, task_candidates, audit = self.experiment.prepare()
        selected = set(self.selected_task_ids)
        if not selected <= set(tasks):
            raise ValueError("selected task is absent from regenerated C005D tasks")
        source_hashes = _preflight_hashes(self.paths["primary_preflight_path"])
        repeat_hashes = _preflight_hashes(self.paths["existing_repeat_preflight_path"])
        current_hashes = audit["task_hashes"]
        primary_rows = _read_rows(self.paths["primary_submission_path"])
        final_rows = _read_rows(self.paths["final_submission_path"])
        record_by_id = {record.notice_id: record for record in records}
        selected_rows = []
        for task_id in self.selected_task_ids:
            notice_id = task_id.split("__p", 1)[0]
            notice_tasks = audit["coverage"][notice_id]["task_ids"]
            if notice_tasks != [task_id]:
                raise ValueError(f"{notice_id}: selected positive is not a single complete task")
            if current_hashes[task_id] != source_hashes.get(task_id):
                raise ValueError(f"{task_id}: regenerated task hash differs from C005D")
            if int(primary_rows[notice_id]["v19"]) != 1:
                raise ValueError(f"{task_id}: not a primary v19 positive")
            if int(final_rows[notice_id]["v19"]) != 1:
                raise ValueError(f"{task_id}: not an S001 final v19 positive")
            coverage = audit["coverage"][notice_id]
            if any(not row["inspected"] for row in coverage["documents"]):
                raise ValueError(f"{task_id}: source document was not inspected")
            tokens = self.experiment.counter.count(tasks[task_id]["messages"])
            if tokens > self.config.prompt_budget:
                raise ValueError(f"{task_id}: task exceeds tokenizer budget")
            selected_rows.append({
                "task_id": task_id,
                "id": notice_id,
                "task_hash": current_hashes[task_id],
                "tokens": tokens,
                "document_count": len(record_by_id[notice_id].documents),
                "documents": coverage["documents"],
                "candidate_source_ids": [
                    candidate.source_id for candidate in task_candidates[task_id]
                ],
            })
        for task_id, path in self.existing_repeat_paths.items():
            if task_id not in selected:
                raise ValueError(f"{task_id}: undeclared existing repeat")
            if current_hashes[task_id] != repeat_hashes.get(task_id):
                raise ValueError(f"{task_id}: existing repeat task hash differs")
            if not path.is_file():
                raise FileNotFoundError(path)
        self._write_selected_rendered(tasks, task_candidates, selected_rows)
        return {
            "records": records,
            "views": views,
            "tasks": tasks,
            "task_candidates": task_candidates,
            "audit": audit,
            "selected_rows": selected_rows,
            "primary_rows": primary_rows,
            "final_rows": final_rows,
        }

    def _write_selected_rendered(
        self,
        tasks: Mapping[str, Mapping[str, Any]],
        task_candidates: Mapping[str, Sequence[Any]],
        selected_rows: Sequence[Mapping[str, Any]],
    ) -> None:
        shortest = min(selected_rows, key=lambda row: int(row["tokens"]))["task_id"]
        largest = max(selected_rows, key=lambda row: int(row["tokens"]))["task_id"]
        attachment = next(
            (row["task_id"] for row in selected_rows if int(row["document_count"]) > 1),
            shortest,
        )
        roles = {shortest: "short", attachment: "attachment", largest: "largest"}
        semantic_rows = []
        for row in selected_rows:
            task_id = str(row["task_id"])
            task = tasks[task_id]
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
                "source_only_no_final_label": (
                    "최종 위반 여부나 v19 0/1은 출력하지 않는다" in system
                ),
                "all_candidate_ids_rendered": all(
                    f"[{candidate.source_id} |" in user
                    for candidate in task_candidates[task_id]
                ),
            }
            status = "PASS" if all(checks.values()) else "FAIL"
            semantic_rows.append({"task_id": task_id, "checks": checks, "status": status})
            atomic_json(self.output_dir / "rendered_inputs" / f"selected_{task_id}.json", {
                **dict(row),
                "review_role": roles.get(task_id, "selected"),
                "messages": task["messages"],
                "schema": task["schema"],
            })
        atomic_json(self.output_dir / "selected_semantic_contract.json", {
            "active_item": "v19",
            "inherited_items": [f"v{index}" for index in range(1, 25) if index != 19],
            "inherited_contract": "S001 stored rows; no new prompt or policy",
            "overflow_selected": False,
            "overflow_note": "C005D selected positives each fit one complete tokenizer-admitted task.",
            "rendered_tasks": semantic_rows,
            "status": "PASS" if all(row["status"] == "PASS" for row in semantic_rows) else "FAIL",
        })

    def preflight_only(self) -> dict[str, Any]:
        manifest = compare_manifests(self.config.path, self.root)
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")
        prepared = self._prepare()
        semantic = json.loads(
            (self.output_dir / "selected_semantic_contract.json").read_text(encoding="utf-8")
        )
        report = {
            "status": "PASS" if semantic["status"] == "PASS" else "FAIL",
            "manifest_diff": manifest,
            "selected_tasks": prepared["selected_rows"],
            "new_calls_planned": len(self.selected_task_ids) - len(self.existing_repeat_paths),
            "existing_repeats_reused": sorted(self.existing_repeat_paths),
            "semantic_contract": semantic["status"],
            "prompt_policy": "byte-identical C005D task",
            "other_items": "S001 stored rows; no calls and no changes",
            "json_fence_replay": self.replay_policy,
        }
        atomic_json(self.output_dir / "preflight.json", report)
        atomic_json(self.output_dir / "resolved_manifest.json", self.config.raw)
        return report

    def _parse_repeat(
        self,
        response: Mapping[str, Any], candidates: Sequence[Any],
    ) -> tuple[bool, int | None, str, dict[str, Any]]:
        parsed, reason = parse_v19_observations_relaxed_quote(response, candidates)
        if parsed is None:
            return False, None, "", {"reason": reason, "observations": []}
        value, evidence, diagnostic = reduce_v19_with_quote_resolution(candidates, parsed)
        return True, value, evidence, diagnostic

    def _complete_with_semantic_retries(
        self,
        runtime: OpenRouterRuntime,
        task_id: str,
        task: Mapping[str, Any],
        candidates: Sequence[Any],
    ) -> dict[str, Any]:
        attempts = int(self.policy["invalid_response_retries"]) + 1
        last: dict[str, Any] | None = None
        for attempt in range(1, attempts + 1):
            try:
                response = runtime.complete(dict(task))
            except Exception as error:  # isolate one failed task from the remaining batch
                response = {
                    "content": "",
                    "finish_reason": "transport_error",
                    "invalid": True,
                    "error": f"{type(error).__name__}: {error}",
                    "usage": {},
                    "latency_seconds": 0.0,
                    "attempts": 0,
                }
            atomic_json(
                self.output_dir / "attempts" / f"{task_id}__a{attempt:02d}.json",
                response,
            )
            last = response
            valid, _, _, _ = self._parse_repeat(response, candidates)
            if valid:
                break
        if last is None:
            raise RuntimeError(f"{task_id}: no response attempt was made")
        return last

    def _write_intermediate(
        self,
        responses: Mapping[str, Mapping[str, Any]],
        task_candidates: Mapping[str, Sequence[Any]],
        *,
        mock: bool,
        started: float,
    ) -> None:
        rows = []
        for task_id in self.selected_task_ids:
            response = responses.get(task_id)
            if response is None:
                rows.append({"task_id": task_id, "state": "pending"})
                continue
            valid, value, _, diagnostic = self._parse_repeat(
                response, task_candidates[task_id],
            )
            rows.append({
                "task_id": task_id,
                "state": "complete",
                "semantic_valid": valid,
                "repeat_value": value,
                "decision": diagnostic.get("decision"),
            })
        atomic_json(self.output_dir / ("intermediate.mock.json" if mock else "intermediate_report.json"), {
            "selected": len(self.selected_task_ids),
            "complete": sum(row["state"] == "complete" for row in rows),
            "pending": sum(row["state"] == "pending" for row in rows),
            "rows": rows,
            "seconds": round(time.monotonic() - started, 3),
        })

    def run(self, *, mock: bool = False) -> dict[str, Any]:
        started = time.monotonic()
        preflight = self.preflight_only()
        if preflight["status"] != "PASS":
            raise ValueError("S016 preflight failed")
        prepared = self._prepare()
        tasks = prepared["tasks"]
        task_candidates = prepared["task_candidates"]
        response_dir = self.output_dir / ("mock_responses" if mock else "responses")
        responses: dict[str, dict[str, Any]] = {
            task_id: json.loads(path.read_text(encoding="utf-8"))
            for task_id, path in self.existing_repeat_paths.items()
        }
        pending: list[str] = []
        resumed = 0
        replay_audits: dict[str, dict[str, Any]] = {}
        for task_id in self.selected_task_ids:
            if task_id in responses:
                continue
            if self.replay_source_dir is not None and not mock:
                source = self.replay_source_dir / f"{task_id}.json"
                if not source.is_file():
                    raise FileNotFoundError(source)
                raw_bytes = source.read_bytes()
                raw_response = json.loads(raw_bytes.decode("utf-8"))
                adapted, adaptation = adapt_single_json_fence(raw_response)
                adaptation.update({
                    "source_path": str(source),
                    "source_sha256": hashlib.sha256(raw_bytes).hexdigest(),
                })
                replay_audits[task_id] = adaptation
                atomic_json(
                    self.output_dir / "adapted_responses" / f"{task_id}.json",
                    adapted,
                )
                responses[task_id] = adapted
                resumed += 1
                continue
            path = response_dir / f"{task_id}.json"
            if path.is_file():
                responses[task_id] = json.loads(path.read_text(encoding="utf-8"))
                resumed += 1
            else:
                pending.append(task_id)
        self._write_intermediate(
            responses, task_candidates, mock=mock, started=started,
        )
        if mock:
            for task_id in pending:
                response = _mock_response(task_candidates[task_id])
                atomic_json(response_dir / f"{task_id}.json", response)
                responses[task_id] = response
                self._write_intermediate(
                    responses, task_candidates, mock=True, started=started,
                )
        elif pending:
            runtime = OpenRouterRuntime(
                self.config.provider,
                os.environ.get(self.config.provider.api_key_env, ""),
            )
            with ThreadPoolExecutor(max_workers=self.config.provider.concurrency) as executor:
                futures = {
                    executor.submit(
                        self._complete_with_semantic_retries,
                        runtime,
                        task_id,
                        tasks[task_id],
                        task_candidates[task_id],
                    ): task_id
                    for task_id in pending
                }
                for future in as_completed(futures):
                    task_id = futures[future]
                    response = future.result()
                    atomic_json(response_dir / f"{task_id}.json", response)
                    responses[task_id] = response
                    self._write_intermediate(
                        responses, task_candidates, mock=False, started=started,
                    )
        if set(responses) != set(self.selected_task_ids):
            raise ValueError("selected repeat response coverage differs")
        if self.replay_policy is not None and not mock:
            expected = set(str(value) for value in self.replay_policy["expected_fenced_task_ids"])
            recovered = {
                task_id for task_id, row in replay_audits.items() if row["recovered"]
            }
            if recovered != expected:
                raise ValueError(
                    f"JSON fence recovery set differs: expected={sorted(expected)}, "
                    f"actual={sorted(recovered)}"
                )
            if not all(
                not row["recovered"] or row.get("inner_object_exact") is True
                for row in replay_audits.values()
            ):
                raise ValueError("JSON fence adapter changed an inner object")

        labels = _read_labels(self.config.labels_path)
        repeat_rows = []
        for selected in prepared["selected_rows"]:
            task_id = str(selected["task_id"])
            notice_id = str(selected["id"])
            valid, value, evidence, diagnostic = self._parse_repeat(
                responses[task_id], task_candidates[task_id],
            )
            repeat_rows.append({
                "id": notice_id,
                "task_id": task_id,
                "truth": int(labels[notice_id]["v19"]),
                "semantic_valid": valid,
                "repeat_value": value,
                "repeat_evidence": evidence,
                "repeat_decision": diagnostic.get("decision"),
                "response_source": (
                    "existing_independent_repeat"
                    if task_id in self.existing_repeat_paths else (
                        "s016_json_fence_replay"
                        if self.replay_policy is not None else "s016"
                    )
                ),
            })

        final_rows = prepared["final_rows"]
        baseline_rows = [final_rows[notice_id] for notice_id in sorted(final_rows)]
        consensus_rows = [dict(row) for row in baseline_rows]
        repeat_by_id = {row["id"]: row for row in repeat_rows}
        for row in consensus_rows:
            repeated = repeat_by_id.get(str(row["id"]))
            if repeated is not None and repeated["repeat_value"] != 1:
                row["v19"] = 0
                row["e19"] = ""
        ids = set(final_rows)
        baseline_metrics = evaluate_rows_for_ids(
            baseline_rows, self.config.labels_path, ids, "dev200",
        )
        consensus_metrics = evaluate_rows_for_ids(
            consensus_rows, self.config.labels_path, ids, "dev200",
        )
        gate = repeat_gate(
            repeat_rows,
            baseline_f1=float(baseline_metrics["per_item"]["v19"]["f1"]),
        )
        output_name = "submission.consensus.mock.csv" if mock else "submission.consensus.csv"
        write_submission_csv(self.output_dir / output_name, consensus_rows)
        atomic_json(
            self.output_dir / ("repeat_rows.mock.json" if mock else "repeat_rows.json"),
            repeat_rows,
        )
        usage = [response.get("usage") or {} for response in responses.values()]
        expected_native_tasks = float(self.policy["expected_test_native_tasks"])
        report = {
            "status": "PASS" if mock or all(row["semantic_valid"] for row in repeat_rows) else "INCOMPLETE",
            "experiment_id": self.config.experiment_id,
            "mode": "adaptive-dev-v19-positive-only-exact-repeat-diagnostic",
            "selected_tasks": len(self.selected_task_ids),
            "existing_repeats_reused": len(self.existing_repeat_paths),
            "resumed_new_responses": resumed,
            "new_calls_started": len(pending),
            "semantic_invalid": sum(not row["semantic_valid"] for row in repeat_rows),
            "json_fence_recovery": replay_audits,
            "repeat_rows": repeat_rows,
            "baseline_metrics": baseline_metrics,
            "consensus_metrics": consensus_metrics,
            "gate": gate,
            "usage": {
                "prompt_tokens_sum": sum(int(row.get("prompt_tokens") or 0) for row in usage),
                "completion_tokens_sum": sum(int(row.get("completion_tokens") or 0) for row in usage),
            },
            "runtime_projection": {
                "dev_candidate_tasks": 165,
                "dev_positive_tasks": 10,
                "positive_rate": 10 / 165,
                "expected_test_native_tasks": expected_native_tasks,
                "expected_extra_test_calls": expected_native_tasks * 10 / 165,
                "sequential_second_wave": True,
            },
            "calls": {"llm_new": 0 if mock else len(pending), "embedding": 0},
            "adaptive_limitation": (
                "The target set and gate use repeatedly inspected dev200; this is not independent "
                "generalization evidence or a submission promotion result."
            ),
            "seconds": round(time.monotonic() - started, 3),
        }
        atomic_json(
            self.output_dir / ("run_report.mock.json" if mock else "run_report.json"),
            report,
        )
        return report
