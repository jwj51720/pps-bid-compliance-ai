#!/usr/bin/env python3
"""Build and validate the explicitly L41-derived runtime-hardened submission."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_ZIP = ROOT / "dist/reference/submit.zip"
REFERENCE_SHA256 = "a06feff77ffbc4a6f2a47cd0e2d322f341f652ca865d1b9cf53919012c8ca216"
SUBMISSION_DIR = ROOT / "submission"
EXPECTED_MEMBERS = ("script.py", "requirements.txt", "runtime_config.json")


REPORTING_RUNNER_OLD = '''class ReportingRunner:
    max_tokens = 1536

    def __init__(self, runner, schemas):
        self.runner = runner
        self.schemas = schemas
        self.stats = {arm: {'requests': 0, 'batches': 0, 'seconds': 0.0,
                           'prompt_tokens': 0, 'completion_tokens': 0,
                           'usage_responses': 0, 'finish_reasons': {}}
                      for arm in pipeline.ARMS}

    def count_tokens(self, messages):
        return self.runner.count_tokens(messages)

    def chat(self, batch, schema):
        arm = next(key for key, value in self.schemas.items() if value == schema)
        stat = self.stats[arm]
        started = time.perf_counter()
        values = self.runner.chat(batch, schema)
        stat['seconds'] += time.perf_counter() - started
        stat['requests'] += len(batch)
        stat['batches'] += 1
        for value in values:
            reason = str(value.get('finish_reason'))
            stat['finish_reasons'][reason] = stat['finish_reasons'].get(reason, 0) + 1
            usage = value.get('usage') or {}
            if all(type(usage.get(key)) is int for key in ('prompt_tokens', 'completion_tokens')):
                stat['usage_responses'] += 1
                for key in ('prompt_tokens', 'completion_tokens'):
                    stat[key] += usage[key]
        emit('inference_batch', arm=arm, completed=stat['requests'],
             seconds=round(stat['seconds'], 3))
        return values
'''


REPORTING_RUNNER_NEW = '''class ReportingRunner:
    max_tokens = 1536

    def __init__(self, runner, schemas):
        self.runner = runner
        self.schemas = schemas
        self.stats = {arm: {'requests': 0, 'batches': 0, 'seconds': 0.0,
                           'prompt_tokens': 0, 'completion_tokens': 0,
                           'usage_responses': 0, 'finish_reasons': {},
                           'backend_batches': 0, 'backend_attempted_inputs': 0,
                           'backend_errors': 0, 'isolated_single_failures': 0}
                      for arm in pipeline.ARMS}

    def count_tokens(self, messages):
        return self.runner.count_tokens(messages)

    def _chat_isolated(self, batch, schema, arm):
        stat = self.stats[arm]
        stat['backend_batches'] += 1
        stat['backend_attempted_inputs'] += len(batch)
        try:
            values = self.runner.chat(batch, schema)
            if not isinstance(values, (list, tuple)) or len(values) != len(batch):
                raise ValueError('backend output count differs from isolated batch')
            if any(not isinstance(value, dict) for value in values):
                raise ValueError('backend returned a non-dictionary response')
            return list(values)
        except Exception as error:
            stat['backend_errors'] += 1
            emit('backend_batch_error', arm=arm, batch=len(batch),
                 error_type=type(error).__name__, error=str(error)[:240])
            if len(batch) == 1:
                stat['isolated_single_failures'] += 1
                return [{'content': '', 'finish_reason': None, 'invalid': True,
                         'usage': {}, 'backend_error': type(error).__name__ + ': ' + str(error)[:240]}]
            middle = len(batch) // 2
            return (self._chat_isolated(batch[:middle], schema, arm)
                    + self._chat_isolated(batch[middle:], schema, arm))

    def chat(self, batch, schema):
        arm = next(key for key, value in self.schemas.items() if value == schema)
        stat = self.stats[arm]
        started = time.perf_counter()
        values = self._chat_isolated(batch, schema, arm)
        stat['seconds'] += time.perf_counter() - started
        stat['requests'] += len(batch)
        stat['batches'] += 1
        for value in values:
            reason = str(value.get('finish_reason'))
            stat['finish_reasons'][reason] = stat['finish_reasons'].get(reason, 0) + 1
            usage = value.get('usage') or {}
            if all(type(usage.get(key)) is int for key in ('prompt_tokens', 'completion_tokens')):
                stat['usage_responses'] += 1
                for key in ('prompt_tokens', 'completion_tokens'):
                    stat[key] += usage[key]
        emit('inference_batch', arm=arm, completed=stat['requests'],
             seconds=round(stat['seconds'], 3))
        return values
'''


NORMAL_COVERAGE_OLD = '''def normal_coverage(ids, responses):
    failed = 0
    for rid in ids:
        normal = any(response.get('finish_reason') == 'stop'
                     and response.get('invalid') is not True
                     and isinstance(response.get('content'), str)
                     and bool(response['content'].strip())
                     for response in (responses[arm, rid] for arm in pipeline.ARMS))
        failed += int(not normal)
    if failed:
        raise RuntimeError(f'{failed} records have no nonempty stop response; no retry or dummy submission')
'''


NORMAL_COVERAGE_NEW = '''def response_is_structurally_valid(response):
    if (not isinstance(response, dict) or response.get('finish_reason') != 'stop'
            or response.get('invalid') is True):
        return False
    content = response.get('content')
    if not isinstance(content, str) or not content.strip():
        return False
    try:
        value = json.loads(content)
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    return isinstance(value, dict)


def retry_invalid_responses(tasks, responses, runner, chunk):
    targets = [key for key in sorted(tasks) if not response_is_structurally_valid(responses[key])]
    recovered, unresolved = [], []
    for arm in pipeline.ARMS:
        arm_targets = [key for key in targets if key[0] == arm]
        for offset in range(0, len(arm_targets), chunk):
            keys = arm_targets[offset:offset + chunk]
            if not keys:
                continue
            schema = tasks[keys[0]]['schema']
            values = runner.chat([tasks[key]['messages'] for key in keys], schema)
            for key, value in zip(keys, values):
                responses[key] = value
                if response_is_structurally_valid(value):
                    recovered.append(key)
                else:
                    unresolved.append(key)
    report = {
        'attempted': len(targets),
        'targets': [arm + '/' + rid for arm, rid in targets],
        'recovered': [arm + '/' + rid for arm, rid in recovered],
        'unresolved': [arm + '/' + rid for arm, rid in unresolved],
    }
    emit('invalid_retry_complete', attempted=len(targets), recovered=len(recovered),
         unresolved=len(unresolved))
    return responses, report


def normal_coverage(ids, responses):
    failed = []
    for rid in ids:
        normal = any(response_is_structurally_valid(responses[arm, rid])
                     for arm in pipeline.ARMS)
        if not normal:
            failed.append(rid)
    if failed:
        emit('all_arms_invalid_after_retry', count=len(failed), ids=failed)
    return failed
'''


RUN_OLD = '''    responses, counts = pipeline.infer_once(tasks, measured, chunk=args.chunk, data_dir=args.data_dir)
    report['inference_with_preflight_seconds'] = time.perf_counter() - then
    report['by_arm'] = measured.stats
'''


RUN_NEW = '''    responses, counts = pipeline.infer_once(tasks, measured, chunk=args.chunk, data_dir=args.data_dir)
    responses, retry_report = retry_invalid_responses(
        tasks, responses, measured, args.chunk)
    report['invalid_retry'] = retry_report
    report['retries'] = retry_report['attempted']
    report['inference_with_preflight_seconds'] = time.perf_counter() - then
    report['by_arm'] = measured.stats
'''


CALL_COUNT_OLD = "                  normal_response_records=len(ids), gemma_calls=0 if args.mock else len(responses))"
CALL_COUNT_NEW = "                  normal_response_records=len(ids), gemma_calls=0 if args.mock else len(responses) + report['retries'])"

NORMAL_CALL_OLD = "    normal_coverage(ids, responses)"
NORMAL_CALL_NEW = "    report['records_without_valid_arm'] = normal_coverage(ids, responses)"

MAIN_ANCHOR_OLD = '''def main(argv=None):
    # No network access, no implicit Hugging Face download, no model creation on import/spawn.
'''

MAIN_ANCHOR_NEW = '''def emergency_submission(args, error):
    # Last-resort validity path: preserve every organizer ID and the exact 49-column contract.
    records = list(baseline.iter_records(args.input, limit=args.limit))
    rows = []
    for record in records:
        row = {'id': record['id']}
        row.update({f'v{index}': 0 for index in range(1, 25)})
        row.update({f'e{index}': '' for index in range(1, 25)})
        rows.append(row)
    write_submission(rows, args.output)
    report = {
        'pipeline': VERSION,
        'status': 'DEGRADED_PASS',
        'records': len(rows),
        'fallback': 'emergency-zero-csv',
        'error_type': type(error).__name__,
        'error': str(error)[:2000],
    }
    atomic_json(args.report, report)
    emit('emergency_submission_written', records=len(rows),
         error_type=type(error).__name__, error=str(error)[:240])
    return report


def main(argv=None):
    # No network access, no implicit Hugging Face download, no model creation on import/spawn.
'''

MAIN_ERROR_OLD = '''    try:
        report = preflight(args) if args.preflight else run(args)
    except Exception as error:
        atomic_json(args.report, {'pipeline': VERSION, 'status': 'FAIL',
                                 'error_type': type(error).__name__, 'error': str(error)})
        raise
    return 0 if report['status'] == 'PASS' else 1
'''

MAIN_ERROR_NEW = '''    try:
        report = preflight(args) if args.preflight else run(args)
    except Exception as error:
        if args.preflight:
            atomic_json(args.report, {'pipeline': VERSION, 'status': 'FAIL',
                                     'error_type': type(error).__name__, 'error': str(error)})
            return 1
        report = emergency_submission(args, error)
    return 0 if report['status'] in ('PASS', 'DEGRADED_PASS') else 1
'''


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_reference_script() -> str:
    if sha256(REFERENCE_ZIP) != REFERENCE_SHA256:
        raise ValueError("reference ZIP hash differs")
    with zipfile.ZipFile(REFERENCE_ZIP) as archive:
        if archive.namelist() != ["script.py"]:
            raise ValueError("reference ZIP must contain exactly script.py")
        return archive.read("script.py").decode("utf-8")


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise ValueError(f"{label} anchor count is {count}, expected 1")
    return source.replace(old, new, 1)


def build_script() -> str:
    source = load_reference_script()
    source = replace_once(source, REPORTING_RUNNER_OLD, REPORTING_RUNNER_NEW, "runner")
    source = replace_once(source, NORMAL_COVERAGE_OLD, NORMAL_COVERAGE_NEW, "coverage")
    source = replace_once(source, RUN_OLD, RUN_NEW, "run")
    source = replace_once(source, CALL_COUNT_OLD, CALL_COUNT_NEW, "call count")
    source = replace_once(source, NORMAL_CALL_OLD, NORMAL_CALL_NEW, "coverage call")
    source = replace_once(source, MAIN_ANCHOR_OLD, MAIN_ANCHOR_NEW, "main anchor")
    source = replace_once(source, MAIN_ERROR_OLD, MAIN_ERROR_NEW, "main recovery")
    source = replace_once(
        source,
        "VERSION = 'l41-frozen-three-expert-submission-v1'",
        "VERSION = 'l41-derived-runtime-hardened-v1'",
        "version",
    )
    return source


def write_active_script() -> Path:
    destination = SUBMISSION_DIR / "script.py"
    destination.write_text(build_script(), encoding="utf-8")
    return destination


def validate_zip(path: Path) -> dict[str, object]:
    if len(path.name) > 30:
        raise ValueError("submission ZIP filename exceeds 30 characters")
    if path.stat().st_size > 2 * 1024**3:
        raise ValueError("compressed submission exceeds 2 GiB")
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if names != list(EXPECTED_MEMBERS):
            raise ValueError(f"unexpected ZIP members: {names}")
        if any(
            info.is_dir()
            or Path(info.filename).is_absolute()
            or ".." in Path(info.filename).parts
            for info in archive.infolist()
        ):
            raise ValueError("unsafe ZIP member")
        extracted_size = sum(info.file_size for info in archive.infolist())
    if extracted_size > 8 * 1024**3:
        raise ValueError("extracted submission exceeds 8 GiB")
    return {
        "path": str(path),
        "sha256": sha256(path),
        "compressed_bytes": path.stat().st_size,
        "extracted_bytes": extracted_size,
        "members": names,
    }


def staged_mock(path: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="pps-l41-staged-") as temporary:
        stage = Path(temporary)
        with zipfile.ZipFile(path) as archive:
            archive.extractall(stage)
        output_dir = stage / "output"
        command = [
            sys.executable,
            str(stage / "script.py"),
            "--mock",
            "--data-dir",
            str(ROOT / "data/raw/open/data"),
            "--output-dir",
            str(output_dir),
            "--limit",
            "10",
        ]
        completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=120)
        if completed.returncode != 0:
            raise RuntimeError(
                "staged mock failed: " + (completed.stderr[-2000:] or completed.stdout[-2000:])
            )
        csv_path = output_dir / "submission.csv"
        report_path = output_dir / "l41_runtime_report.json"
        if not csv_path.is_file() or not report_path.is_file():
            raise ValueError("staged mock did not create required outputs")
        import csv

        with csv_path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        with csv_path.open(encoding="utf-8", newline="") as stream:
            reader = csv.reader(stream)
            header = next(reader)
        expected = ["id", *[f"v{i}" for i in range(1, 25)], *[f"e{i}" for i in range(1, 25)]]
        if header != expected or len(rows) != 10 or len({row["id"] for row in rows}) != 10:
            raise ValueError("staged mock CSV shape/identity contract failed")
        if any(row[f"v{i}"] not in {"0", "1"} for row in rows for i in range(1, 25)):
            raise ValueError("staged mock contains non-binary labels")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("status") != "PASS" or report.get("invalid_retry", {}).get("unresolved"):
            raise ValueError("staged mock runtime report failed")
        return {
            "records": len(rows),
            "columns": len(header),
            "ids_unique": True,
            "status": report["status"],
            "invalid_retry": report["invalid_retry"],
        }


def package(output: Path) -> dict[str, object]:
    script = write_active_script()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.write(script, "script.py")
        archive.write(SUBMISSION_DIR / "requirements.txt", "requirements.txt")
        archive.write(SUBMISSION_DIR / "runtime_config.json", "runtime_config.json")
    report = validate_zip(output)
    report["script_sha256"] = sha256(script)
    report["staged_mock"] = staged_mock(output)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_name = "pps_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".zip"
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / default_name)
    args = parser.parse_args()
    report = package(args.output.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
