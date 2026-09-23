"""Measure the staged S027 policy with fresh Gemma responses on dev200."""

from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.pps_ai import load_experiment_config  # noqa: E402
from src.pps_ai.archive_parity import ArchiveStoredResponseParity, _fingerprint  # noqa: E402
from src.pps_ai.evaluate import evaluate_rows  # noqa: E402
from src.pps_ai.ingest import load_notice_records  # noqa: E402
from src.pps_ai.preflight import compare_manifests  # noqa: E402
from src.pps_ai.runtime.openrouter import OpenRouterRuntime, atomic_json  # noqa: E402
from src.pps_ai.runtime.tokenizer import GemmaTokenCounter  # noqa: E402


ARCHIVE = ROOT / "dist/pps_20260923_163852.zip"
ARCHIVE_SHA256 = "2c6a7ba69d2f2a5cfac067acfb06acb2fc217bbfa57d2ce044d43737ac8b9fe1"
OUTPUT = ROOT / "outputs/clean-exp-s028-s027-fresh-dev200-v1"


class RemoteRunner:
    load_seconds = 0.0

    def __init__(self, config, api_key: str) -> None:
        self.counter = GemmaTokenCounter(config.tokenizer_dir)
        self.runtime = OpenRouterRuntime(config.provider, api_key)
        self.concurrency = config.provider.concurrency
        self.positions: dict[str, int] = defaultdict(int)
        self.fresh = 0
        self.cached = 0
        self.errors = 0
        self.started = time.monotonic()

    def count_tokens(self, messages):
        return self.counter.count(list(messages))

    def chat(self, batch, schema):
        requests = []
        for messages in batch:
            fingerprint = _fingerprint(messages, schema)
            self.positions[fingerprint] += 1
            attempt = self.positions[fingerprint]
            path = OUTPUT / "responses" / f"{fingerprint}__attempt{attempt:02d}.json"
            requests.append((messages, fingerprint, path))

        def complete(item):
            messages, fingerprint, path = item
            if path.exists():
                response = json.loads(path.read_text(encoding="utf-8"))
                if response.get("task_fingerprint") != fingerprint:
                    raise ValueError("cached task fingerprint differs")
                return response, False
            try:
                response = self.runtime.complete({
                    "arm": "S027", "messages": list(messages), "schema": schema,
                })
            except RuntimeError as error:
                response = {
                    "content": "", "finish_reason": None, "invalid": True,
                    "usage": {}, "error": str(error)[:500],
                }
            response["task_fingerprint"] = fingerprint
            atomic_json(path, response)
            return response, True

        values = [None] * len(requests)
        with ThreadPoolExecutor(max_workers=min(self.concurrency, len(requests))) as pool:
            futures = {pool.submit(complete, item): index for index, item in enumerate(requests)}
            for future in as_completed(futures):
                index = futures[future]
                response, fresh = future.result()
                values[index] = response
                self.fresh += int(fresh)
                self.cached += int(not fresh)
                self.errors += int(bool(response.get("invalid")))
        print(json.dumps({
            "event": "batch_complete", "size": len(batch),
            "fresh": self.fresh, "cached": self.cached, "errors": self.errors,
            "elapsed_seconds": round(time.monotonic() - self.started, 1),
        }), flush=True)
        return values


def main() -> int:
    load_dotenv(ROOT / ".env")
    config = load_experiment_config(
        ROOT / "experiments/manifests/clean_exp_s005_v3_revert_ablation_v1.json", ROOT,
    )
    if compare_manifests(config.path, ROOT)["status"] != "PASS":
        raise ValueError("S005 policy preflight failed")
    if hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("S027 archive hash differs")
    api_key = os.environ.get(config.provider.api_key_env, "")
    if not api_key:
        raise ValueError(f"{config.provider.api_key_env} is required")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    atomic_json(OUTPUT / "manifest.snapshot.json", config.raw)
    audit = ArchiveStoredResponseParity(load_experiment_config(
        ROOT / "experiments/manifests/clean_exp_s006_archive_stored_response_parity_v1.json", ROOT,
    ))
    audit.archive_path = ARCHIVE
    rankings = json.loads(audit.rankings_path.read_text(encoding="utf-8"))
    runner = RemoteRunner(config, api_key)
    with tempfile.TemporaryDirectory(prefix="pps-s028-") as temporary:
        module = audit._load_archive(Path(temporary))
        records = list(module.baseline.iter_records(str(config.input_path)))
        if len(records) != 200 or set(rankings) != {record["id"] for record in records}:
            raise ValueError("dev200/ranking ID coverage differs")
        args = type("Args", (), {
            "input": str(config.input_path), "limit": None,
            "output": str(OUTPUT / "submission.csv"),
            "report": str(OUTPUT / "archive_runtime_report.json"),
            "data_dir": str(config.data_dir), "embed_dir": str(config.data_dir),
            "model_dir": str(config.data_dir), "mock": False,
            "chunk": config.batch_size,
        })()
        report = module.run(
            args, runner_factory=lambda _args: runner,
            ranking_builder=lambda *_args, **_kwargs: (
                rankings, {"mode": "stored-unchanged-bge-rankings", "embedding_calls": 0},
            ),
        )
    with (OUTPUT / "submission.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected = ["id", *[f"v{i}" for i in range(1, 25)], *[f"e{i}" for i in range(1, 25)]]
    if len(rows) != 200 or list(rows[0]) != expected or len({row["id"] for row in rows}) != 200:
        raise ValueError("submission row/column/ID contract failed")
    original = {record.notice_id: record for record in load_notice_records(config.input_path)}
    invalid_evidence = []
    for row in rows:
        sources = [document.text for document in original[row["id"]].documents]
        for index in range(1, 25):
            if row[f"v{index}"] not in {"0", "1"}:
                raise ValueError("nonbinary label")
            evidence = row[f"e{index}"]
            if evidence and (len(evidence) > 500 or not any(evidence in source for source in sources)):
                invalid_evidence.append((row["id"], index))
    if invalid_evidence:
        raise ValueError(f"invalid evidence: {invalid_evidence[:5]}")
    typed = [{**row, **{f"v{i}": int(row[f"v{i}"]) for i in range(1, 25)}} for row in rows]
    metrics = evaluate_rows(typed, config.labels_path, {
        "fast20": config.fast_panel_path, "holdout20": config.holdout_panel_path,
    })
    summary = {
        "status": report["status"], "archive_sha256": ARCHIVE_SHA256,
        "fresh_calls": runner.fresh, "cached_calls": runner.cached,
        "transport_errors": runner.errors, "runtime": report,
        "metrics": metrics, "invalid_evidence": invalid_evidence,
        "limitation": "Fresh OpenRouter Gemma; unchanged stored BGE ranking; not evaluator vLLM.",
    }
    atomic_json(OUTPUT / "run_report.json", summary)
    print(json.dumps({
        "status": summary["status"], "fresh_calls": runner.fresh,
        "cached_calls": runner.cached, "transport_errors": runner.errors,
        "dev200_macro_positive_f1": metrics["dev200"]["macro_positive_f1"],
        "fast20_macro_positive_f1": metrics["fast20"]["macro_positive_f1"],
        "holdout20_macro_positive_f1": metrics["holdout20"]["macro_positive_f1"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
