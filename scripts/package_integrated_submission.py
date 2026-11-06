#!/usr/bin/env python3
"""Build and stage-test the integrated submission package."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
BASE_PACKAGER = ROOT / "scripts/package_l41_hardened_submission.py"
PACKAGE_ROOT = ROOT / "submission/integrated"
RUNTIME_CONFIG = {
    "schema_version": "pps-submission-v1",
    "candidate": "integrated-v3-v19-retry2-v1",
    "batch_size": 128,
    "invalid_retry_rounds": 2,
    "batch_exception_policy": "recursive-bisection-single-input-isolation",
    "unresolved_policy": "preserve-base-cell-and-always-write-valid-csv",
    "model_max_length": 16384,
    "max_completion_tokens": 1536,
    "temperature": 0,
    "seed": 20260826,
    "quantization": "int8_per_channel_weight_only",
}
PACKAGE_FILES = (
    "script.py",
    "requirements.txt",
    "runtime_config.json",
    "pps_ai/__init__.py",
    "pps_ai/submission_integration.py",
    "pps_ai/views/__init__.py",
    "pps_ai/views/v3_monetary.py",
    "pps_ai/views/v19_requirements.py",
    "pps_ai/decisions/__init__.py",
    "pps_ai/decisions/v3_monetary.py",
    "pps_ai/decisions/v3_keyed_serialization.py",
    "pps_ai/decisions/v3_basis_reducer_v2.py",
    "pps_ai/decisions/v19_requirements.py",
    "pps_ai/decisions/v19_quote_resolution_v2.py",
)


RUN_FUNCTION = '''def run(args, *, runner_factory=None, ranking_builder=build_rankings):
    started = time.perf_counter()
    records = list(baseline.iter_records(args.input, limit=args.limit))
    ids = [r['id'] for r in records]
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate input ID')
    report = {'pipeline': VERSION, 'mode': 'mock' if args.mock else 'vllm-offline',
              'records': len(records), 'status': 'RUNNING', 'server_time_verified': False,
              'max_tokens': 1536, 'temperature': 0, 'seed': 20260826, 'thinking': False,
              'max_model_len': 16384, 'quantization': 'int8_per_channel_weight_only',
              'batch_size': args.chunk, 'invalid_retry_rounds': 2}
    if not records:
        write_submission([], args.output)
        report.update(status='PASS', total_seconds=time.perf_counter() - started, gemma_calls=0)
        atomic_json(args.report, report)
        return report
    emit('start', pipeline=VERSION, records=len(records), mock=args.mock)
    builder = FactBuilder(args.data_dir)
    prepared = {r['id']: pipeline.prepare_record(r, builder) for r in records}
    base_tasks = pipeline.make_tasks(prepared, args.data_dir)
    if args.mock:
        rankings = {rid: {'id': rid, 'query': '', 'ranked': []} for rid in ids}
        retrieval = {'mode': 'mock-empty'}
    else:
        rankings, retrieval = ranking_builder(records, builder, args.embed_dir,
            device='cpu', batch_size=24, max_length=256, top_k=10)
    report['retrieval'] = retrieval
    runner = (runner_factory(args) if runner_factory else
              MockRunner() if args.mock else VLLMRunner(args.model_dir))
    report['model_load_seconds'] = runner.load_seconds
    measured = ReportingRunner(runner)
    views, specialist_tasks, routing = integration.build_specialist_tasks(
        records, measured.count_tokens, baseline.PROMPT_BUDGET)
    selected_base = {
        key: task for key, task in base_tasks.items()
        if key[0] in ('r10', 'C24') or routing[key[1]]['use_base_b_initially']
    }
    base_responses, base_retry = infer_tasks(
        selected_base, measured, args.chunk,
        lambda key, task, response: integration.valid_base_response(task, response))
    specialist_responses, specialist_retry = infer_tasks(
        specialist_tasks, measured, args.chunk,
        lambda key, task, response: integration.valid_response(key, task, response, views))
    for rid in ids:
        key = ('B', rid)
        if key not in base_responses:
            base_responses[key] = {'content': json.dumps(schema_sample(base_tasks[key]['schema']),
                ensure_ascii=False), 'finish_reason': 'stop', 'invalid': False, 'usage': {}}
    candidate, _, _, _, details = pipeline.assemble({r['id']: r for r in records},
        prepared, base_responses, rankings, builder, data_dir=args.data_dir)
    candidate, fallback_b, specialist_details = integration.apply_specialists(
        records, candidate, views, specialist_tasks, specialist_responses, routing)
    fallback_retry = {'attempts': 0, 'unresolved': []}
    if fallback_b:
        fallback_tasks = {('B', rid): base_tasks['B', rid] for rid in fallback_b}
        fallback_responses, fallback_retry = infer_tasks(
            fallback_tasks, measured, args.chunk,
            lambda key, task, response: integration.valid_base_response(task, response))
        base_responses.update(fallback_responses)
        candidate, _, _, _, details = pipeline.assemble({r['id']: r for r in records},
            prepared, base_responses, rankings, builder, data_dir=args.data_dir)
        candidate, _, specialist_details = integration.apply_specialists(
            records, candidate, views, specialist_tasks, specialist_responses, routing)
    rows, evidence = clean_rows(records, candidate)
    write_submission(rows, args.output)
    initial_calls = len(selected_base) + len(specialist_tasks)
    retry_calls = base_retry['attempts'] + specialist_retry['attempts'] + fallback_retry['attempts']
    report.update(
        status='PASS', total_seconds=time.perf_counter() - started,
        initial_logical_calls=initial_calls,
        retry_calls=retry_calls,
        fallback_b_calls=len(fallback_b),
        gemma_calls=0 if args.mock else initial_calls + retry_calls + len(fallback_b),
        task_counts={'base': len(selected_base), 'specialist': len(specialist_tasks)},
        retry={'base': base_retry, 'specialist': specialist_retry, 'fallback_b': fallback_retry},
        by_arm=measured.stats, evidence=evidence,
        unresolved_tasks=base_retry['unresolved'] + specialist_retry['unresolved']
            + fallback_retry['unresolved'])
    atomic_json(args.report, report)
    emit('complete', status=report['status'], records=len(records),
         initial_calls=initial_calls, retry_calls=retry_calls, fallback_b=len(fallback_b))
    return report


'''


RUNNER_BLOCK = '''class ReportingRunner:
    max_tokens = 1536

    def __init__(self, runner):
        self.runner = runner
        self.stats = {}

    def count_tokens(self, messages):
        return self.runner.count_tokens(messages)

    def chat(self, batch, schema, arm):
        stat = self.stats.setdefault(arm, {'requests': 0, 'batches': 0, 'seconds': 0.0,
            'backend_batches': 0, 'backend_errors': 0, 'isolated_single_failures': 0})
        started = time.perf_counter()
        values = self._isolated(batch, schema, arm)
        stat['seconds'] += time.perf_counter() - started
        stat['requests'] += len(batch)
        stat['batches'] += 1
        return values

    def _isolated(self, batch, schema, arm):
        stat = self.stats[arm]
        stat['backend_batches'] += 1
        try:
            values = self.runner.chat(batch, schema)
            if not isinstance(values, (list, tuple)) or len(values) != len(batch):
                raise ValueError('backend output count differs')
            if any(not isinstance(value, dict) for value in values):
                raise ValueError('backend output type differs')
            return list(values)
        except Exception as error:
            stat['backend_errors'] += 1
            if len(batch) == 1:
                stat['isolated_single_failures'] += 1
                return [{'content': '', 'finish_reason': None, 'invalid': True, 'usage': {},
                         'backend_error': type(error).__name__ + ': ' + str(error)[:240]}]
            middle = len(batch) // 2
            return self._isolated(batch[:middle], schema, arm) + self._isolated(
                batch[middle:], schema, arm)


def infer_tasks(tasks, runner, chunk, validator):
    responses = {}
    pending = list(sorted(tasks, key=str))
    attempts = 0
    for round_number in range(3):
        groups = {}
        for key in pending:
            task = tasks[key]
            schema_key = fingerprint(task['schema'])
            groups.setdefault((str(key).split('/')[0] if isinstance(key, str) else key[0], schema_key), []).append(key)
        current = []
        for (arm, _), keys in groups.items():
            schema = tasks[keys[0]]['schema']
            for offset in range(0, len(keys), chunk):
                batch_keys = keys[offset:offset + chunk]
                values = runner.chat([tasks[key]['messages'] for key in batch_keys], schema, arm)
                for key, value in zip(batch_keys, values):
                    responses[key] = value
                    if not validator(key, tasks[key], value):
                        current.append(key)
                if round_number:
                    attempts += len(batch_keys)
        pending = current
        if not pending:
            break
    return responses, {'attempts': attempts, 'unresolved': [str(key) for key in pending]}


'''


def _load_base_packager():
    spec = importlib.util.spec_from_file_location("_base_packager", BASE_PACKAGER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load base packager")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _replace_region(source: str, start: str, end: str, replacement: str) -> str:
    left = source.index(start)
    right = source.index(end, left)
    return source[:left] + replacement + source[right:]


def build_script() -> str:
    source = _load_base_packager().build_script()
    source = source.replace(
        '"""Generated frozen L41 standalone entry. See l41 build_manifest.json for provenance."""',
        '"""Offline submission entry point."""',
        1,
    )
    source = source.replace(
        "from submission.l41_candidate.vllm_runner import VLLMRunner, tokenize_messages\n",
        "from submission.l41_candidate.vllm_runner import VLLMRunner, tokenize_messages\n"
        "from pps_ai import submission_integration as integration\n",
        1,
    )
    source = source.replace(
        "VERSION = 'l41-derived-runtime-hardened-v1'",
        "VERSION = 'pps-integrated-v1'",
        1,
    )
    source = _replace_region(source, "class ReportingRunner:", "def clean_rows", RUNNER_BLOCK)
    source = _replace_region(source, "def run(args, *, runner_factory=None, ranking_builder=build_rankings):", "def arguments", RUN_FUNCTION)
    source = source.replace("submission.l41_candidate", "submission.runtime_core")
    source = source.replace("l41-offline-assembly-v1", "pps-offline-assembly-v1")
    source = source.replace("l41_runtime_report.json", "runtime_report.json")
    source = source.replace(".l41-report-", ".pps-report-")
    source = source.replace(".l41-csv-", ".pps-csv-")
    source = source.replace("Frozen L41", "Fixed runtime")
    source = source.replace("frozen L41", "fixed runtime")
    source = source.replace("frozen limit", "fixed limit")
    source = source.replace("frozen quantization", "fixed quantization")
    source = source.replace("frozen 14848-token budget", "fixed 14848-token budget")
    source = source.replace("frozen max_tokens", "fixed max_tokens")
    source = source.replace("frozen output budget", "fixed output budget")
    source = source.replace("Frozen order", "Assembly order")
    source = source.replace(
        "# Generated by tools/build_l41_offline_runtime.py; do not hand-edit.\\n",
        "",
    )
    return source


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_package_files() -> None:
    PACKAGE_ROOT.mkdir(parents=True, exist_ok=True)
    (PACKAGE_ROOT / "script.py").write_text(build_script(), encoding="utf-8")
    (PACKAGE_ROOT / "requirements.txt").write_text(
        "# Runtime libraries are supplied by the evaluation server.\n", encoding="utf-8",
    )
    (PACKAGE_ROOT / "runtime_config.json").write_text(
        json.dumps(RUNTIME_CONFIG, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    for relative in ("pps_ai/__init__.py", "pps_ai/views/__init__.py", "pps_ai/decisions/__init__.py"):
        destination = PACKAGE_ROOT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("", encoding="utf-8")
    sources = {
        "pps_ai/submission_integration.py": ROOT / "src/pps_ai/submission_integration.py",
        "pps_ai/views/v3_monetary.py": ROOT / "src/pps_ai/views/v3_monetary.py",
        "pps_ai/views/v19_requirements.py": ROOT / "src/pps_ai/views/v19_requirements.py",
        "pps_ai/decisions/v3_monetary.py": ROOT / "src/pps_ai/decisions/v3_monetary.py",
        "pps_ai/decisions/v3_keyed_serialization.py": ROOT / "src/pps_ai/decisions/v3_keyed_serialization.py",
        "pps_ai/decisions/v3_basis_reducer_v2.py": ROOT / "src/pps_ai/decisions/v3_basis_reducer_v2.py",
        "pps_ai/decisions/v19_requirements.py": ROOT / "src/pps_ai/decisions/v19_requirements.py",
        "pps_ai/decisions/v19_quote_resolution_v2.py": ROOT / "src/pps_ai/decisions/v19_quote_resolution_v2.py",
    }
    for relative, source in sources.items():
        destination = PACKAGE_ROOT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())


def create_zip(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in PACKAGE_FILES:
            archive.write(PACKAGE_ROOT / relative, relative)


def staged_mock(path: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="pps-integrated-") as temporary:
        stage = Path(temporary)
        with zipfile.ZipFile(path) as archive:
            archive.extractall(stage)
        output_dir = stage / "output"
        command = [
            sys.executable, str(stage / "script.py"), "--mock",
            "--data-dir", str(ROOT / "data/raw/open/data"),
            "--output-dir", str(output_dir), "--limit", "10", "--chunk", "128",
        ]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=180)
        if completed.returncode != 0:
            raise RuntimeError((completed.stderr or completed.stdout)[-4000:])
        import csv
        with (output_dir / "submission.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
            fields = list(rows[0]) if rows else []
        expected = ["id", *[f"v{i}" for i in range(1, 25)], *[f"e{i}" for i in range(1, 25)]]
        if len(rows) != 10 or fields != expected or len({row["id"] for row in rows}) != 10:
            raise ValueError("staged CSV contract failed")
        report = json.loads((output_dir / "runtime_report.json").read_text(encoding="utf-8"))
        if report["status"] != "PASS" or report["invalid_retry_rounds"] != 2:
            raise ValueError("staged runtime report failed")
        return {"records": len(rows), "columns": len(fields), "status": report["status"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    args = parser.parse_args()
    write_package_files()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = Path(args.output) if args.output else ROOT / "dist" / f"pps_{timestamp}.zip"
    create_zip(output)
    if len(output.name) > 30:
        raise ValueError("ZIP filename exceeds 30 characters")
    result = {
        "path": str(output), "sha256": sha256(output),
        "compressed_bytes": output.stat().st_size,
        "members": list(PACKAGE_FILES), "staged_mock": staged_mock(output),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
