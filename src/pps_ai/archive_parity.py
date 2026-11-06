"""Replay a packaged submission with hash-checked stored model responses."""

from __future__ import annotations

from collections import defaultdict
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
from typing import Any, Mapping, Sequence
import zipfile

from .config import CleanExperimentConfig
from .evaluate import evaluate_rows
from .preflight import compare_manifests
from .runtime.openrouter import atomic_json
from .runtime.tokenizer import GemmaTokenCounter


FIELDS = ["id", *[f"v{i}" for i in range(1, 25)], *[f"e{i}" for i in range(1, 25)]]


def _fingerprint(messages: Sequence[Mapping[str, str]], schema: Mapping[str, Any]) -> str:
    payload = {"messages": list(messages), "schema": schema}
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = []
        for source in csv.DictReader(handle):
            row: dict[str, Any] = {"id": source["id"]}
            row.update({f"v{i}": int(source[f"v{i}"]) for i in range(1, 25)})
            row.update({f"e{i}": source[f"e{i}"] for i in range(1, 25)})
            rows.append(row)
        return rows


def _cell_differences(
    expected: Sequence[Mapping[str, Any]], actual: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    left = {str(row["id"]): row for row in expected}
    right = {str(row["id"]): row for row in actual}
    differences = []
    for notice_id in sorted(set(left) | set(right)):
        for field in FIELDS:
            before = str(left.get(notice_id, {}).get(field, "<MISSING>"))
            after = str(right.get(notice_id, {}).get(field, "<MISSING>"))
            if before != after:
                differences.append({
                    "id": notice_id, "field": field,
                    "expected": before, "actual": after,
                })
    return differences


class StoredResponseRunner:
    """Archive runner adapter keyed by the exact rendered message and schema."""

    load_seconds = 0.0

    def __init__(
        self,
        counter: GemmaTokenCounter,
        response_queues: Mapping[str, Sequence[Mapping[str, Any]]],
    ) -> None:
        self.counter = counter
        self.queues = {key: [dict(value) for value in values] for key, values in response_queues.items()}
        self.positions: dict[str, int] = defaultdict(int)
        self.requests = 0
        self.missing: list[str] = []

    def count_tokens(self, messages: Sequence[Mapping[str, str]]) -> int:
        return self.counter.count(list(messages))

    def chat(
        self, batch: Sequence[Sequence[Mapping[str, str]]], schema: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        values = []
        for messages in batch:
            key = _fingerprint(messages, schema)
            queue = self.queues.get(key)
            if not queue:
                self.missing.append(key)
                raise KeyError(f"no stored response for task fingerprint {key}")
            position = self.positions[key]
            values.append(dict(queue[min(position, len(queue) - 1)]))
            self.positions[key] += 1
            self.requests += 1
        return values


class ArchiveStoredResponseParity:
    def __init__(self, config: CleanExperimentConfig) -> None:
        self.config = config
        self.root = config.path.parents[2]
        self.output_dir = config.output_dir.resolve()
        policy = config.raw["archive_stored_response_parity_audit"]
        self.archive_path = self.root / policy["archive_path"]
        self.expected_path = self.root / policy["expected_submission_path"]
        self.rankings_path = self.root / policy["rankings_path"]
        self.base_response_dir = self.root / policy["base_response_dir"]
        self.v3_response_dir = self.root / policy["v3_response_dir"]
        self.v3_recovery_dir = self.root / policy["v3_recovery_dir"]
        self.v19_response_dir = self.root / policy["v19_response_dir"]

    def _load_archive(self, stage: Path) -> ModuleType:
        with zipfile.ZipFile(self.archive_path) as archive:
            for info in archive.infolist():
                target = (stage / info.filename).resolve()
                if stage.resolve() not in target.parents and target != stage.resolve():
                    raise ValueError(f"unsafe archive member: {info.filename}")
            archive.extractall(stage)
        script_path = stage / "script.py"
        spec = importlib.util.spec_from_file_location("_pps_s006_submission", script_path)
        if spec is None or spec.loader is None:
            raise ImportError("cannot load staged submission script")
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(stage))
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path.remove(str(stage))
        return module

    def _task_hash_audit(
        self,
        counter: GemmaTokenCounter,
        base_tasks: Mapping[Any, Mapping[str, Any]],
        specialist_tasks: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, Any]:
        expected_base = _read_json(
            self.base_response_dir.parent / "preflight.json"
        )["task_hashes"]
        expected_v3 = _read_json(
            self.v3_response_dir.parent / "preflight.json"
        )["input_audit"]["task_hashes"]
        expected_v19 = _read_json(
            self.v19_response_dir.parent / "preflight.json"
        )["input_audit"]["task_hashes"]
        actual_base = {
            f"{arm}/{notice_id}": counter.task_sha256(dict(task))
            for (arm, notice_id), task in base_tasks.items()
        }
        actual_v3 = {
            task_id.split("/")[1]: counter.task_sha256(dict(task))
            for task_id, task in specialist_tasks.items() if task_id.startswith("V3/")
        }
        actual_v19 = {
            task_id.split("/")[1] + "__" + task_id.split("/")[2]:
                counter.task_sha256(dict(task))
            for task_id, task in specialist_tasks.items() if task_id.startswith("V19/")
        }
        report = {
            "base": "MATCH" if actual_base == expected_base else "DIFF",
            "v3": "MATCH" if actual_v3 == expected_v3 else "DIFF",
            "v19": "MATCH" if actual_v19 == expected_v19 else "DIFF",
            "counts": {
                "base": len(actual_base), "v3": len(actual_v3), "v19": len(actual_v19),
            },
        }
        if any(report[name] != "MATCH" for name in ("base", "v3", "v19")):
            raise ValueError(f"archive task hashes differ from stored tasks: {report}")
        return report

    def _response_queues(
        self,
        base_tasks: Mapping[Any, Mapping[str, Any]],
        specialist_tasks: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        queues: dict[str, list[dict[str, Any]]] = {}

        def register(task: Mapping[str, Any], responses: list[dict[str, Any]]) -> None:
            key = _fingerprint(task["messages"], task["schema"])
            if key in queues:
                raise ValueError(f"duplicate task fingerprint: {key}")
            queues[key] = responses

        for (arm, notice_id), task in base_tasks.items():
            response = _read_json(self.base_response_dir / arm / f"{notice_id}.json")
            register(task, [response])
        for task_id, task in specialist_tasks.items():
            parts = task_id.split("/")
            notice_id = parts[1]
            if parts[0] == "V3":
                primary = _read_json(self.v3_response_dir / f"{notice_id}.json")
                recovery = self.v3_recovery_dir / notice_id / "attempt_001.json"
                responses = [primary]
                if recovery.exists():
                    responses.append(_read_json(recovery))
                register(task, responses)
            else:
                response = _read_json(
                    self.v19_response_dir / f"{notice_id}__{parts[2]}.json"
                )
                register(task, [response])
        return queues

    def run(self) -> dict[str, Any]:
        manifest = compare_manifests(self.config.path, self.root)
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")
        archive_sha256 = hashlib.sha256(self.archive_path.read_bytes()).hexdigest()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        counter = GemmaTokenCounter(self.config.tokenizer_dir)
        with tempfile.TemporaryDirectory(prefix="pps-s006-") as temp:
            stage = Path(temp)
            module = self._load_archive(stage)
            records = list(module.baseline.iter_records(str(self.config.input_path)))
            builder = module.FactBuilder(str(self.config.data_dir))
            prepared = {
                record["id"]: module.pipeline.prepare_record(record, builder)
                for record in records
            }
            base_tasks = module.pipeline.make_tasks(prepared, str(self.config.data_dir))
            views, specialist_tasks, _ = module.integration.build_specialist_tasks(
                records, counter.count, self.config.prompt_budget,
            )
            del views
            task_hashes = self._task_hash_audit(counter, base_tasks, specialist_tasks)
            queues = self._response_queues(base_tasks, specialist_tasks)
            runner = StoredResponseRunner(counter, queues)
            rankings = _read_json(self.rankings_path)

            def ranking_builder(*_args: Any, **_kwargs: Any) -> tuple[Any, dict[str, Any]]:
                return rankings, {"mode": "stored-rankings", "embedding_calls": 0}

            output_path = self.output_dir / "submission.csv"
            runtime_path = self.output_dir / "archive_runtime_report.json"
            args = SimpleNamespace(
                input=str(self.config.input_path), limit=None,
                output=str(output_path), report=str(runtime_path),
                data_dir=str(self.config.data_dir), embed_dir=str(self.config.data_dir),
                model_dir=str(self.config.data_dir), mock=False,
                chunk=self.config.batch_size,
            )
            archive_report = module.run(
                args, runner_factory=lambda _args: runner, ranking_builder=ranking_builder,
            )

        actual = _read_rows(self.output_dir / "submission.csv")
        expected = _read_rows(self.expected_path)
        differences = _cell_differences(expected, actual)
        metrics = evaluate_rows(actual, self.config.labels_path, {
            "fast20": self.config.fast_panel_path,
            "holdout20": self.config.holdout_panel_path,
        })
        atomic_json(self.output_dir / "metrics.json", metrics)
        status = "PASS" if not differences and not runner.missing else "FAIL"
        report = {
            "status": status,
            "mode": "exact-submission-archive-stored-response-replay",
            "archive_path": str(self.archive_path.relative_to(self.root)),
            "archive_sha256": archive_sha256,
            "records": len(actual),
            "task_hashes": task_hashes,
            "registered_task_fingerprints": len(queues),
            "stored_response_requests": runner.requests,
            "missing_fingerprints": runner.missing,
            "llm_calls": 0,
            "embedding_calls": 0,
            "cell_difference_count": len(differences),
            "cell_differences": differences,
            "metrics": metrics,
            "archive_runtime": archive_report,
            "manifest_diff": manifest,
            "limitation": (
                "Proves package assembly parity for stored responses, not generation parity "
                "between OpenRouter and evaluator vLLM."
            ),
        }
        atomic_json(self.output_dir / "run_report.json", report)
        return report
