"""Layered clean-room orchestration for the frozen L41 reference baseline."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

from .assembly import FINAL_OWNERS, validate_owner_matrix
from .config import CleanExperimentConfig
from .domain import NoticeRecord
from .evaluate import evaluate_rows
from .evidence import clean_final_rows
from .export import write_submission_csv
from .facts import ReferenceFactLayer
from .ingest import load_notice_records
from .reference import FrozenL41Reference
from .runtime.openrouter import OpenRouterRuntime, atomic_json
from .runtime.retrieval import build_reference_rankings
from .runtime.tokenizer import GemmaTokenCounter
from .views import ReferenceSourceViewLayer


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _schema_sample(schema: dict[str, Any]) -> Any:
    if "enum" in schema:
        return next((value for value in (None, "N", 0) if value in schema["enum"]), schema["enum"][0])
    kind = schema.get("type")
    if isinstance(kind, list):
        if "null" in kind:
            return None
        kind = kind[0]
    if kind == "object":
        return {key: _schema_sample(value) for key, value in schema["properties"].items()}
    if kind == "array":
        return []
    if kind == "integer":
        return 0
    if kind == "string":
        return ""
    if kind == "boolean":
        return False
    return None


def _label_ids(path: Path) -> set[str]:
    import csv

    with path.open(encoding="utf-8", newline="") as handle:
        return {row["id"] for row in csv.DictReader(handle)}


def _render_review_samples(
    tasks: dict[tuple[str, str], dict[str, Any]], records: list[dict[str, Any]],
    token_counts: dict[tuple[str, str], int], output_dir: Path,
) -> list[dict[str, Any]]:
    chars = {str(record["id"]): sum(len(str(doc["text"])) for doc in record["docs"]) for record in records}
    attachment_ids = [str(record["id"]) for record in records if len(record["docs"]) > 1]
    selected = {
        "short": min(chars, key=chars.get),
        "attachment": attachment_ids[0] if attachment_ids else min(chars, key=chars.get),
        "largest_prompt": max(tasks, key=lambda key: token_counts[key])[1],
    }
    review_dir = output_dir / "rendered_inputs"
    review_dir.mkdir(parents=True, exist_ok=True)
    report = []
    for role, notice_id in selected.items():
        payload = {
            arm: {
                "tokens": token_counts[arm, notice_id],
                "messages": tasks[arm, notice_id]["messages"],
                "schema": tasks[arm, notice_id]["schema"],
            }
            for arm in ("r10", "B", "C24")
        }
        destination = review_dir / f"{role}_{notice_id}.json"
        atomic_json(destination, payload)
        report.append({"role": role, "id": notice_id, "path": str(destination)})
    return report


class CleanReferencePipeline:
    def __init__(self, config: CleanExperimentConfig, *, output_dir: Path | None = None) -> None:
        self.config = config
        self.output_dir = (output_dir or config.output_dir).resolve()
        validate_owner_matrix()
        self.reference = FrozenL41Reference(
            config.reference_zip, config.reference_zip_sha256,
        )
        self.builder = self.reference.builder(config.data_dir)
        self.fact_layer = ReferenceFactLayer(self.builder)
        self.view_layer = ReferenceSourceViewLayer(self.reference.section_module)
        self.counter = GemmaTokenCounter(config.tokenizer_dir)

    def prepare(self, records: list[NoticeRecord]) -> tuple[
        dict[str, dict[str, Any]], dict[tuple[str, str], dict[str, Any]], dict[str, Any]
    ]:
        raw_records = [dict(record.raw) for record in records]
        fact_hashes: dict[str, str] = {}
        source_ledger: dict[str, list[dict[str, Any]]] = {}
        view_coverage: dict[str, Any] = {}
        prepared: dict[str, dict[str, Any]] = {}
        for record in raw_records:
            notice_id = str(record["id"])
            typed_record = next(item for item in records if item.notice_id == notice_id)
            source_ledger[notice_id] = [
                {
                    "doc_id": document.doc_id,
                    "type": document.document_type,
                    "order": document.order,
                    "characters": len(document.text),
                    "sha256": document.sha256,
                }
                for document in typed_record.documents
            ]
            facts = self.fact_layer.extract(record)
            view = self.view_layer.build(record)
            fact_hashes[notice_id] = hashlib.sha256(
                json.dumps(facts, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()
            candidate_docs = {
                str(candidate["doc_id"])
                for section in view["sections"].values()
                for candidate in section["candidates"]
            }
            view_coverage[notice_id] = {
                "supplied_documents": len(record["docs"]),
                "documents_with_candidates": len(candidate_docs),
                "candidate_count": sum(section["candidate_count"] for section in view["sections"].values()),
            }
            prepared[notice_id] = self.reference.pipeline.prepare_record(record, self.builder)
        tasks = self.reference.pipeline.make_tasks(prepared, str(self.config.data_dir))
        expected = {
            (arm, record.notice_id)
            for arm in ("r10", "B", "C24") for record in records
        }
        if set(tasks) != expected:
            raise ValueError("task coverage differs from 3 arms × records")
        token_counts = {key: self.counter.count(task["messages"]) for key, task in tasks.items()}
        over = {key: count for key, count in token_counts.items() if count > self.config.prompt_budget}
        if over:
            raise ValueError(f"prompt budget exceeded: {list(over.items())[:3]}")
        task_hashes = {f"{arm}/{notice_id}": self.counter.task_sha256(task) for (arm, notice_id), task in tasks.items()}
        audit = {
            "record_count": len(records),
            "task_count": len(tasks),
            "logical_calls": len(tasks),
            "calls_per_record": 3,
            "token_counts": {
                arm: {
                    "count": len(records),
                    "sum": sum(value for (task_arm, _), value in token_counts.items() if task_arm == arm),
                    "max": max(value for (task_arm, _), value in token_counts.items() if task_arm == arm),
                }
                for arm in ("r10", "B", "C24")
            },
            "fact_hashes": fact_hashes,
            "source_ledger": source_ledger,
            "view_coverage": view_coverage,
            "task_hashes": task_hashes,
            "owner_matrix": FINAL_OWNERS,
            "owner_coverage": len(FINAL_OWNERS),
        }
        audit["rendered_samples"] = _render_review_samples(
            tasks, raw_records, token_counts, self.output_dir,
        )
        return prepared, tasks, audit

    def _responses(
        self, tasks: dict[tuple[str, str], dict[str, Any]], mock: bool,
    ) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, Any]]:
        checkpoint_dir = self.output_dir / ("mock_responses" if mock else "responses")
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        responses: dict[tuple[str, str], dict[str, Any]] = {}
        pending: list[tuple[tuple[str, str], dict[str, Any]]] = []
        for key, task in sorted(tasks.items()):
            path = checkpoint_dir / key[0] / f"{key[1]}.json"
            if path.is_file():
                responses[key] = json.loads(path.read_text(encoding="utf-8"))
            else:
                pending.append((key, task))
        if mock:
            for key, task in pending:
                response = {
                    "content": json.dumps(_schema_sample(task["schema"]), ensure_ascii=False),
                    "finish_reason": "stop", "invalid": False,
                    "model": "mock", "usage": {}, "latency_seconds": 0.0, "attempts": 1,
                }
                atomic_json(checkpoint_dir / key[0] / f"{key[1]}.json", response)
                responses[key] = response
        elif pending:
            api_key = os.environ.get(self.config.provider.api_key_env, "")
            runtime = OpenRouterRuntime(self.config.provider, api_key)
            with ThreadPoolExecutor(max_workers=self.config.provider.concurrency) as executor:
                futures = {executor.submit(runtime.complete, task): (key, task) for key, task in pending}
                for number, future in enumerate(as_completed(futures), 1):
                    key, _ = futures[future]
                    response = future.result()
                    atomic_json(checkpoint_dir / key[0] / f"{key[1]}.json", response)
                    responses[key] = response
                    if number % 20 == 0:
                        print(json.dumps({"event": "inference_progress", "completed": number, "pending_at_start": len(pending)}), flush=True)
        if set(responses) != set(tasks):
            raise ValueError("response/task coverage differs")
        report = {
            "checkpoint_dir": str(checkpoint_dir),
            "resumed": len(tasks) - len(pending),
            "new": len(pending),
            "finish_reasons": {},
            "fallback_risk": {},
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "cost": 0.0},
        }
        for (arm, _), response in responses.items():
            reason = str(response.get("finish_reason"))
            report["finish_reasons"][reason] = report["finish_reasons"].get(reason, 0) + 1
            report["fallback_risk"][arm] = report["fallback_risk"].get(arm, 0) + int(
                reason != "stop" or response.get("invalid") is True
            )
            usage = response.get("usage") or {}
            for key in ("prompt_tokens", "completion_tokens", "cost"):
                value = usage.get(key, 0)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    report["usage"][key] += value
        return responses, report

    def run(self, *, mock: bool = False, limit: int | None = None) -> dict[str, Any]:
        started = time.monotonic()
        all_records = load_notice_records(self.config.input_path)
        if len(all_records) != 200:
            raise ValueError(f"dev baseline requires exactly 200 records, got {len(all_records)}")
        input_ids = {record.notice_id for record in all_records}
        label_ids = _label_ids(self.config.labels_path)
        if input_ids != label_ids:
            raise ValueError("dev input/label ID coverage differs before inference")
        records = all_records[:limit] if limit is not None else all_records
        if not mock and limit is not None:
            raise ValueError("paid run cannot use a partial dev selection")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        prepared, tasks, preflight = self.prepare(records)
        atomic_json(self.output_dir / "preflight.json", preflight)
        raw_records = {record.notice_id: dict(record.raw) for record in records}
        if mock:
            rankings = {record.notice_id: {"id": record.notice_id, "query": "", "ranked": []} for record in records}
            retrieval_report = {"mode": "mock-empty", "records": len(records)}
        else:
            rankings_path = self.output_dir / "rankings.json"
            retrieval_report_path = self.output_dir / "retrieval_report.json"
            if rankings_path.is_file() and retrieval_report_path.is_file():
                rankings = json.loads(rankings_path.read_text(encoding="utf-8"))
                retrieval_report = json.loads(retrieval_report_path.read_text(encoding="utf-8"))
            else:
                api_key = os.environ.get(self.config.provider.api_key_env, "")
                rankings, retrieval_report = build_reference_rankings(
                    list(raw_records.values()), self.builder, self.reference.catalog_module,
                    self.config.provider, api_key, self.config.retrieval_batch_size,
                    self.config.retrieval_top_k,
                )
                atomic_json(rankings_path, rankings)
                atomic_json(retrieval_report_path, retrieval_report)
        responses, inference_report = self._responses(tasks, mock)
        candidate, control, residual_control, raw, diagnostics = self.reference.pipeline.assemble(
            raw_records, prepared, responses, rankings, self.builder,
            data_dir=str(self.config.data_dir),
        )
        del control, residual_control, raw
        rows, evidence_report = clean_final_rows(list(raw_records.values()), candidate)
        output_name = "submission.mock.csv" if mock else "submission.csv"
        write_submission_csv(self.output_dir / output_name, rows)
        diagnostic_summary = {
            arm: sum(bool(diagnostics[arm, notice_id].get("fallback", not diagnostics[arm, notice_id].get("valid", True))) for notice_id in raw_records)
            for arm in ("r10", "B", "C24")
        }
        metrics = None
        if not mock and limit is None:
            metrics = evaluate_rows(rows, self.config.labels_path, {
                "fast20": self.config.fast_panel_path,
                "holdout20": self.config.holdout_panel_path,
            })
            atomic_json(self.output_dir / "metrics.json", metrics)
        report = {
            "experiment_id": self.config.experiment_id,
            "pipeline_id": self.config.pipeline_id,
            "mode": "mock" if mock else "openrouter",
            "records": len(records),
            "manifest_sha256": self.config.manifest_sha256,
            "reference_zip_sha256": _sha256(self.config.reference_zip),
            "reference_script_sha256": self.reference.script_sha256,
            "input_sha256": _sha256(self.config.input_path),
            "labels_sha256": _sha256(self.config.labels_path),
            "preflight": preflight,
            "retrieval": retrieval_report,
            "inference": inference_report,
            "fallbacks": diagnostic_summary,
            "evidence": evidence_report,
            "metrics": metrics,
            "total_seconds": round(time.monotonic() - started, 3),
            "status": "PASS",
            "limitations": [
                "OpenRouter transport is not evaluator vLLM/int8 runtime equivalence",
                "frozen L41 known defects are preserved for baseline parity",
            ],
        }
        atomic_json(self.output_dir / ("run_report.mock.json" if mock else "run_report.json"), report)
        return report
