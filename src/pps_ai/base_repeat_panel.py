"""Hash-fixed exact-repeat micro panel for frozen r10/B/C24 tasks."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import json
import os
from pathlib import Path
import time
from typing import Any, Mapping, Sequence

from .config import CleanExperimentConfig
from .evaluate import evaluate_rows_for_ids
from .evidence import clean_final_rows
from .export import COLUMNS, write_submission_csv
from .ingest import load_notice_records
from .pipeline import CleanReferencePipeline, _schema_sample
from .preflight import compare_manifests
from .runtime.openrouter import OpenRouterRuntime, atomic_json
from .v19_positive_repeat import adapt_single_json_fence


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


def _read_labels(path: Path) -> dict[str, dict[str, int]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {
            str(row["id"]): {f"v{index}": int(row[f"v{index}"]) for index in range(1, 25)}
            for row in csv.DictReader(handle)
        }


def compare_prediction_rows(
    before: Mapping[str, Mapping[str, Any]],
    after: Mapping[str, Mapping[str, Any]],
    labels: Mapping[str, Mapping[str, int]],
) -> dict[str, Any]:
    """Describe label/evidence changes and their correctness direction."""
    if set(before) != set(after) or set(before) != set(labels):
        raise ValueError("row comparison ID coverage differs")
    label_changes = []
    evidence_changes = []
    direction_counts = {
        "correct_to_wrong": 0,
        "wrong_to_correct": 0,
        "wrong_to_different_wrong": 0,
    }
    for notice_id in sorted(before):
        for index in range(1, 25):
            item = f"v{index}"
            left = int(before[notice_id][item])
            right = int(after[notice_id][item])
            if left != right:
                truth = int(labels[notice_id][item])
                if left == truth and right != truth:
                    direction = "correct_to_wrong"
                elif left != truth and right == truth:
                    direction = "wrong_to_correct"
                else:
                    direction = "wrong_to_different_wrong"
                direction_counts[direction] += 1
                label_changes.append({
                    "id": notice_id,
                    "item": item,
                    "before": left,
                    "after": right,
                    "truth": truth,
                    "direction": direction,
                })
            evidence = f"e{index}"
            if str(before[notice_id][evidence]) != str(after[notice_id][evidence]):
                evidence_changes.append({
                    "id": notice_id,
                    "item": evidence,
                    "before": str(before[notice_id][evidence]),
                    "after": str(after[notice_id][evidence]),
                })
    return {
        "label_changed_cells": len(label_changes),
        "evidence_changed_cells": len(evidence_changes),
        "direction_counts": direction_counts,
        "label_changes": label_changes,
        "evidence_changes": evidence_changes,
    }


class BaseArmExactRepeatPanel:
    def __init__(self, config: CleanExperimentConfig) -> None:
        self.config = config
        self.root = config.path.parents[2]
        self.output_dir = config.output_dir.resolve()
        policy = config.raw.get("base_exact_repeat_panel")
        if not isinstance(policy, dict):
            raise ValueError("base exact-repeat panel policy is required")
        if policy.get("module") != "reference-base-arm-exact-task-repeat-panel-v1":
            raise ValueError("unsupported base repeat module")
        self.policy = policy
        self.notice_ids = tuple(str(value) for value in policy["selected_notice_ids"])
        self.arms = tuple(str(value) for value in policy["selected_arms"])
        if self.notice_ids != ("PPS-DEV-21", "PPS-DEV-04"):
            raise ValueError("S017 selected notice panel differs")
        if self.arms != ("r10", "B", "C24"):
            raise ValueError("S017 requires all three frozen base arms")
        self.selected_keys = tuple(
            (arm, notice_id) for notice_id in self.notice_ids for arm in self.arms
        )
        self.paths = {
            key: (self.root / str(value)).resolve()
            for key, value in policy.items()
            if key.endswith("_path") or key.endswith("_dir")
        }
        replay = config.raw.get("base_repeat_json_fence_replay")
        self.replay_policy = replay if isinstance(replay, dict) else None
        self.replay_source_dir: Path | None = None
        if self.replay_policy is not None:
            if self.replay_policy.get("module") != "single-outer-json-fence-adapter-v1":
                raise ValueError("unsupported base repeat fence adapter")
            if int(self.replay_policy.get("llm_calls", -1)) != 0:
                raise ValueError("base repeat fence replay must use zero LLM calls")
            self.replay_source_dir = (
                self.root / str(self.replay_policy["source_response_dir"])
            ).resolve()
        self.pipeline = CleanReferencePipeline(config, output_dir=self.output_dir)

    def _prepare(self) -> dict[str, Any]:
        for path in self.paths.values():
            if not path.exists():
                raise FileNotFoundError(path)
        if self.replay_source_dir is not None and not self.replay_source_dir.is_dir():
            raise FileNotFoundError(self.replay_source_dir)
        records = load_notice_records(self.config.input_path)
        prepared, tasks, audit = self.pipeline.prepare(records)
        if len(tasks) != 600:
            raise ValueError("frozen baseline task coverage differs")
        source_preflight = json.loads(
            self.paths["source_preflight_path"].read_text(encoding="utf-8")
        )
        source_hashes = source_preflight["task_hashes"]
        expected_tokens = {
            str(key): int(value) for key, value in self.policy["expected_tokens"].items()
        }
        record_by_id = {record.notice_id: record for record in records}
        selected = []
        semantic_rows = []
        for arm, notice_id in self.selected_keys:
            key = f"{arm}/{notice_id}"
            task = tasks[arm, notice_id]
            digest = self.pipeline.counter.task_sha256(task)
            tokens = self.pipeline.counter.count(task["messages"])
            if digest != source_hashes.get(key):
                raise ValueError(f"{key}: task hash differs from frozen baseline")
            if tokens != expected_tokens.get(key):
                raise ValueError(f"{key}: token count differs from predeclared selection")
            if tokens > self.config.prompt_budget:
                raise ValueError(f"{key}: tokenizer budget exceeded")
            ledger = audit["source_ledger"][notice_id]
            if len(ledger) != len(record_by_id[notice_id].documents):
                raise ValueError(f"{key}: source ledger omitted a document")
            message_text = "\n".join(str(row["content"]) for row in task["messages"])
            source_lines = [
                line.strip()
                for document in record_by_id[notice_id].documents
                for line in document.text.splitlines()
                if 30 <= len(line.strip()) <= 300
            ]
            checks = {
                "notice_id_rendered": notice_id in message_text,
                "actual_notice_span_rendered": any(line in message_text for line in source_lines),
                "system_and_user_present": (
                    len(task["messages"]) >= 2
                    and all(str(row.get("content") or "") for row in task["messages"])
                ),
                "schema_object": task["schema"].get("type") == "object",
                "token_admitted": tokens <= self.config.prompt_budget,
            }
            semantic_rows.append({
                "task_id": key,
                "checks": checks,
                "status": "PASS" if all(checks.values()) else "FAIL",
            })
            row = {
                "task_id": key,
                "arm": arm,
                "id": notice_id,
                "tokens": tokens,
                "task_hash": digest,
                "documents": ledger,
                "stratum": self.policy["selected_strata"][notice_id],
            }
            selected.append(row)
            atomic_json(
                self.output_dir / "rendered_inputs" / f"{arm}_{notice_id}.json",
                {**row, "messages": task["messages"], "schema": task["schema"]},
            )
        semantic = {
            "mode": "exact-repeat-of-frozen-base-contract",
            "active_arms": list(self.arms),
            "items": [f"v{index}" for index in range(1, 25)],
            "policy_change": False,
            "rendered_tasks": semantic_rows,
            "status": "PASS" if all(row["status"] == "PASS" for row in semantic_rows) else "FAIL",
        }
        atomic_json(self.output_dir / "semantic_contract.json", semantic)
        atomic_json(self.output_dir / "source_coverage.json", {
            "selected_tasks": selected,
            "all_selected_notice_documents_ledgered": True,
        })
        return {
            "records": records,
            "prepared": prepared,
            "tasks": tasks,
            "audit": audit,
            "selected": selected,
            "semantic": semantic,
        }

    def preflight_only(self) -> dict[str, Any]:
        manifest = compare_manifests(self.config.path, self.root)
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")
        prepared = self._prepare()
        report = {
            "status": prepared["semantic"]["status"],
            "manifest_diff": manifest,
            "selected_tasks": prepared["selected"],
            "semantic_contract": prepared["semantic"]["status"],
            "new_calls_planned": len(self.selected_keys),
            "selection_uses_labels_or_responses": False,
            "json_fence_replay": self.replay_policy,
        }
        atomic_json(self.output_dir / "preflight.json", report)
        atomic_json(self.output_dir / "resolved_manifest.json", self.config.raw)
        return report

    def _load_original_responses(self) -> dict[tuple[str, str], dict[str, Any]]:
        response_dir = self.paths["source_response_dir"]
        responses = {}
        for arm in self.arms:
            for path in (response_dir / arm).glob("*.json"):
                responses[arm, path.stem] = json.loads(path.read_text(encoding="utf-8"))
        if len(responses) != 600:
            raise ValueError("stored frozen response coverage differs")
        return responses

    def _assemble(
        self,
        prepared: Mapping[str, Mapping[str, Any]],
        records: Sequence[Any],
        responses: Mapping[tuple[str, str], Mapping[str, Any]],
        rankings: Mapping[str, Any],
    ) -> tuple[dict[str, dict[str, Any]], Mapping[tuple[str, str], Any], dict[str, Any]]:
        raw_records = {record.notice_id: dict(record.raw) for record in records}
        candidate, _, _, _, diagnostics = self.pipeline.reference.pipeline.assemble(
            raw_records,
            dict(prepared),
            dict(responses),
            dict(rankings),
            self.pipeline.builder,
            data_dir=str(self.config.data_dir),
        )
        rows, evidence = clean_final_rows(list(raw_records.values()), candidate)
        return {str(row["id"]): row for row in rows}, diagnostics, evidence

    @staticmethod
    def _s001_overlay(
        base_rows: Mapping[str, Mapping[str, Any]],
        s001_rows: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        result = {notice_id: dict(row) for notice_id, row in base_rows.items()}
        for notice_id, row in result.items():
            for index in (3, 19):
                row[f"v{index}"] = s001_rows[notice_id][f"v{index}"]
                row[f"e{index}"] = s001_rows[notice_id][f"e{index}"]
        return result

    def _write_intermediate(
        self, responses: Mapping[tuple[str, str], Mapping[str, Any]], *, mock: bool,
        started: float,
    ) -> None:
        rows = []
        for arm, notice_id in self.selected_keys:
            response = responses.get((arm, notice_id))
            rows.append({
                "task_id": f"{arm}/{notice_id}",
                "state": "complete" if response is not None else "pending",
                "finish_reason": None if response is None else response.get("finish_reason"),
                "invalid": None if response is None else response.get("invalid"),
            })
        atomic_json(
            self.output_dir / ("intermediate.mock.json" if mock else "intermediate_report.json"),
            {
                "complete": sum(row["state"] == "complete" for row in rows),
                "pending": sum(row["state"] == "pending" for row in rows),
                "rows": rows,
                "seconds": round(time.monotonic() - started, 3),
            },
        )

    def run(self, *, mock: bool = False) -> dict[str, Any]:
        started = time.monotonic()
        preflight = self.preflight_only()
        if preflight["status"] != "PASS":
            raise ValueError("S017 preflight failed")
        prepared = self._prepare()
        tasks = prepared["tasks"]
        repeat_dir = self.output_dir / ("mock_responses" if mock else "responses")
        repeat_responses: dict[tuple[str, str], dict[str, Any]] = {}
        replay_audits: dict[str, dict[str, Any]] = {}
        pending = []
        for key in self.selected_keys:
            if self.replay_source_dir is not None and not mock:
                source = self.replay_source_dir / key[0] / f"{key[1]}.json"
                if not source.is_file():
                    raise FileNotFoundError(source)
                raw_response = json.loads(source.read_text(encoding="utf-8"))
                adapted, adaptation = adapt_single_json_fence(raw_response)
                replay_audits[f"{key[0]}/{key[1]}"] = {
                    **adaptation,
                    "source_path": str(source),
                }
                atomic_json(
                    self.output_dir / "adapted_responses" / key[0] / f"{key[1]}.json",
                    adapted,
                )
                repeat_responses[key] = adapted
                continue
            path = repeat_dir / key[0] / f"{key[1]}.json"
            if path.is_file():
                repeat_responses[key] = json.loads(path.read_text(encoding="utf-8"))
            else:
                pending.append(key)
        self._write_intermediate(repeat_responses, mock=mock, started=started)
        if mock:
            for key in pending:
                task = tasks[key]
                response = {
                    "content": json.dumps(_schema_sample(task["schema"]), ensure_ascii=False),
                    "finish_reason": "stop",
                    "invalid": False,
                    "model": "mock",
                    "usage": {},
                    "latency_seconds": 0.0,
                    "attempts": 1,
                }
                atomic_json(repeat_dir / key[0] / f"{key[1]}.json", response)
                repeat_responses[key] = response
                self._write_intermediate(repeat_responses, mock=True, started=started)
        elif pending:
            runtime = OpenRouterRuntime(
                self.config.provider,
                os.environ.get(self.config.provider.api_key_env, ""),
            )
            with ThreadPoolExecutor(max_workers=self.config.provider.concurrency) as executor:
                futures = {
                    executor.submit(runtime.complete, tasks[key]): key for key in pending
                }
                for future in as_completed(futures):
                    key = futures[future]
                    try:
                        response = future.result()
                    except Exception as error:  # preserve all other completed tasks
                        response = {
                            "content": "",
                            "finish_reason": "transport_error",
                            "invalid": True,
                            "error": f"{type(error).__name__}: {error}",
                            "usage": {},
                            "latency_seconds": 0.0,
                            "attempts": 0,
                        }
                    atomic_json(repeat_dir / key[0] / f"{key[1]}.json", response)
                    repeat_responses[key] = response
                    self._write_intermediate(
                        repeat_responses, mock=False, started=started,
                    )
        if set(repeat_responses) != set(self.selected_keys):
            raise ValueError("repeat response coverage differs")
        if self.replay_policy is not None and not mock:
            expected = set(str(value) for value in self.replay_policy["expected_fenced_task_ids"])
            recovered = {
                task_id for task_id, row in replay_audits.items() if row["recovered"]
            }
            if recovered != expected:
                raise ValueError(
                    f"base fence recovery differs: expected={sorted(expected)}, "
                    f"actual={sorted(recovered)}"
                )
            if not all(
                not row["recovered"] or row.get("inner_object_exact") is True
                for row in replay_audits.values()
            ):
                raise ValueError("base fence adapter changed inner JSON")

        original_responses = self._load_original_responses()
        rankings = json.loads(self.paths["source_rankings_path"].read_text(encoding="utf-8"))
        baseline_rows, baseline_diagnostics, _ = self._assemble(
            prepared["prepared"], prepared["records"], original_responses, rankings,
        )
        source_rows = _read_rows(self.paths["source_submission_path"])
        if baseline_rows != source_rows:
            raise ValueError("reassembled frozen baseline differs from stored submission")
        s001_rows = _read_rows(self.paths["s001_submission_path"])
        baseline_s001 = self._s001_overlay(baseline_rows, s001_rows)
        if baseline_s001 != s001_rows:
            raise ValueError("v3/v19 overlay does not reproduce S001 stored submission")

        labels = _read_labels(self.config.labels_path)
        ids = set(labels)
        baseline_metrics = evaluate_rows_for_ids(
            list(baseline_s001.values()), self.config.labels_path, ids, "dev200",
        )
        task_results = []
        for key in self.selected_keys:
            counterfactual_responses = dict(original_responses)
            counterfactual_responses[key] = repeat_responses[key]
            changed_base, changed_diagnostics, _ = self._assemble(
                prepared["prepared"], prepared["records"], counterfactual_responses, rankings,
            )
            changed_s001 = self._s001_overlay(changed_base, s001_rows)
            comparison = compare_prediction_rows(baseline_s001, changed_s001, labels)
            affected_ids = {
                row["id"] for row in comparison["label_changes"] + comparison["evidence_changes"]
            }
            if not affected_ids <= {key[1]}:
                raise ValueError(f"{key}: repeat changed a foreign notice")
            metrics = evaluate_rows_for_ids(
                list(changed_s001.values()), self.config.labels_path, ids, "dev200",
            )
            original = original_responses[key]
            repeat = repeat_responses[key]
            task_results.append({
                "task_id": f"{key[0]}/{key[1]}",
                "arm": key[0],
                "id": key[1],
                "raw_content_equal": original.get("content") == repeat.get("content"),
                "finish_reasons": [original.get("finish_reason"), repeat.get("finish_reason")],
                "invalid_flags": [original.get("invalid"), repeat.get("invalid")],
                "original_diagnostic": baseline_diagnostics[key],
                "repeat_diagnostic": changed_diagnostics[key],
                "comparison": comparison,
                "macro_positive_f1": metrics["macro_positive_f1"],
                "macro_delta": metrics["macro_positive_f1"] - baseline_metrics["macro_positive_f1"],
                "usage": repeat.get("usage") or {},
                "latency_seconds": repeat.get("latency_seconds"),
            })

        joint_responses = dict(original_responses)
        joint_responses.update(repeat_responses)
        joint_base, joint_diagnostics, joint_evidence = self._assemble(
            prepared["prepared"], prepared["records"], joint_responses, rankings,
        )
        joint_s001 = self._s001_overlay(joint_base, s001_rows)
        joint_comparison = compare_prediction_rows(baseline_s001, joint_s001, labels)
        joint_metrics = evaluate_rows_for_ids(
            list(joint_s001.values()), self.config.labels_path, ids, "dev200",
        )
        write_submission_csv(
            self.output_dir / ("submission.joint.mock.csv" if mock else "submission.joint.csv"),
            [joint_s001[notice_id] for notice_id in sorted(joint_s001)],
        )
        usage = [response.get("usage") or {} for response in repeat_responses.values()]
        report = {
            "status": "PASS",
            "experiment_id": self.config.experiment_id,
            "mode": "hash-fixed-base-arm-exact-repeat-micro-panel",
            "selected_tasks": len(self.selected_keys),
            "resumed_calls": len(self.selected_keys) - len(pending),
            "new_calls_started": 0 if mock else len(pending),
            "json_fence_recovery": replay_audits,
            "baseline_metrics": baseline_metrics,
            "task_results": task_results,
            "joint": {
                "comparison": joint_comparison,
                "metrics": joint_metrics,
                "macro_delta": (
                    joint_metrics["macro_positive_f1"]
                    - baseline_metrics["macro_positive_f1"]
                ),
                "selected_diagnostics": {
                    f"{arm}/{notice_id}": joint_diagnostics[arm, notice_id]
                    for arm, notice_id in self.selected_keys
                },
                "evidence_validation": joint_evidence,
            },
            "usage": {
                "prompt_tokens_sum": sum(int(row.get("prompt_tokens") or 0) for row in usage),
                "completion_tokens_sum": sum(int(row.get("completion_tokens") or 0) for row in usage),
            },
            "calls": {"llm_new": 0 if mock else len(pending), "embedding": 0},
            "limitations": [
                "The two-notice panel estimates generation propagation, not public accuracy.",
                "Selection is label-blind but the correctness analysis uses adaptive dev200 labels.",
                "OpenRouter generation does not prove evaluator INT8 vLLM stability.",
            ],
            "seconds": round(time.monotonic() - started, 3),
        }
        atomic_json(
            self.output_dir / ("run_report.mock.json" if mock else "run_report.json"),
            report,
        )
        return report
