"""Zero-call stability audit for independently generated identical tasks."""

from __future__ import annotations

from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Mapping, Sequence

from .config import CleanExperimentConfig
from .decisions.v3_basis_reducer_v2 import decide_v3_basis_v2
from .decisions.v3_keyed_serialization import adapt_keyed_response
from .decisions.v19_quote_resolution_v2 import (
    parse_v19_observations_relaxed_quote,
    reduce_v19_with_quote_resolution,
)
from .ingest import load_notice_records
from .preflight import compare_manifests
from .runtime.openrouter import atomic_json
from .views.v3_monetary import build_v3_monetary_view
from .views.v19_requirements import build_v19_requirement_view


V3_FIELDS = ("role", "requirement_basis", "mandatory", "amount_surface")
V19_SEMANTIC_FIELDS = (
    "requirement_role", "document_kind", "external_issuer_explicit",
    "bidder_must_obtain_or_hold", "bidder_must_submit",
    "obtain_before_bid_deadline", "submit_with_bid_or_proposal",
    "submit_after_bid_or_contract",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _response(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _usage(response: Mapping[str, Any], key: str) -> int:
    return int((response.get("usage") or {}).get(key) or 0)


def _latency(response: Mapping[str, Any]) -> float:
    return float(response.get("latency_seconds") or 0.0)


def _keyed_rows(response: Mapping[str, Any], view: Mapping[str, Any]) -> list[dict[str, Any]] | None:
    adapted = adapt_keyed_response(response, view)
    if adapted is None:
        return None
    return list(json.loads(str(adapted["content"]))["observations"])


def _field_disagreements(
    left: Sequence[Mapping[str, Any]], right: Sequence[Mapping[str, Any]],
    fields: Sequence[str],
) -> Counter[str]:
    left_rows = {str(row["source_id"]): row for row in left}
    right_rows = {str(row["source_id"]): row for row in right}
    if set(left_rows) != set(right_rows):
        return Counter({"candidate_key_set": 1})
    result: Counter[str] = Counter()
    for source_id in left_rows:
        for field in fields:
            if left_rows[source_id].get(field) != right_rows[source_id].get(field):
                result[field] += 1
    return result


def _read_baseline(path: Path) -> dict[str, dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {str(row["id"]): row for row in csv.DictReader(handle)}


def _preflight_hashes(path: Path) -> dict[str, str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    return {str(key): str(item) for key, item in value["input_audit"]["task_hashes"].items()}


def _common_response_names(left: Path, right: Path) -> list[str]:
    left_names = {path.name for path in left.glob("*.json")}
    right_names = {path.name for path in right.glob("*.json")}
    return sorted(left_names & right_names)


class ExactRepeatStabilityAudit:
    def __init__(self, config: CleanExperimentConfig) -> None:
        self.config = config
        self.root = config.path.parents[2]
        self.output_dir = config.output_dir.resolve()
        policy = config.raw["exact_repeat_stability_audit"]
        self.paths = {
            key: self.root / value for key, value in policy.items()
            if key.endswith("_path") or key.endswith("_dir")
        }

    def _v3(self, records: Mapping[str, Any]) -> dict[str, Any]:
        fast_dir = self.paths["v3_fast_response_dir"]
        dev_dir = self.paths["v3_dev_response_dir"]
        fast_hashes = _preflight_hashes(self.paths["v3_fast_preflight_path"])
        dev_hashes = _preflight_hashes(self.paths["v3_dev_preflight_path"])
        baseline = _read_baseline(self.paths["v3_baseline_submission_path"])
        names = _common_response_names(fast_dir, dev_dir)
        rows = []
        field_counts: Counter[str] = Counter()
        for name in names:
            notice_id = Path(name).stem
            if fast_hashes.get(notice_id) != dev_hashes.get(notice_id):
                raise ValueError(f"v3 task hash mismatch: {notice_id}")
            view = build_v3_monetary_view(records[notice_id].raw)
            left = _response(fast_dir / name)
            right = _response(dev_dir / name)
            left_rows = _keyed_rows(left, view)
            right_rows = _keyed_rows(right, view)
            disagreements = (
                _field_disagreements(left_rows, right_rows, V3_FIELDS)
                if left_rows is not None and right_rows is not None else Counter()
            )
            field_counts.update(disagreements)
            base = baseline[notice_id]
            left_decision = decide_v3_basis_v2(
                records[notice_id].raw, view, left, int(base["v3"]), str(base["e3"]),
            )
            right_decision = decide_v3_basis_v2(
                records[notice_id].raw, view, right, int(base["v3"]), str(base["e3"]),
            )
            rows.append({
                "id": notice_id,
                "task_hash": fast_hashes[notice_id],
                "exact_content_equal": left.get("content") == right.get("content"),
                "both_parse_valid": left_rows is not None and right_rows is not None,
                "semantic_field_disagreements": dict(disagreements),
                "final_values": [left_decision[0], right_decision[0]],
                "final_value_disagreement": left_decision[0] != right_decision[0],
                "finish_reasons": [left.get("finish_reason"), right.get("finish_reason")],
                "completion_tokens": [_usage(left, "completion_tokens"), _usage(right, "completion_tokens")],
                "latency_seconds": [_latency(left), _latency(right)],
            })
        return self._summarize("v3", rows, field_counts)

    def _v19(self, records: Mapping[str, Any]) -> dict[str, Any]:
        fast_dir = self.paths["v19_fast_response_dir"]
        dev_dir = self.paths["v19_dev_response_dir"]
        fast_hashes = _preflight_hashes(self.paths["v19_fast_preflight_path"])
        dev_hashes = _preflight_hashes(self.paths["v19_dev_preflight_path"])
        names = _common_response_names(fast_dir, dev_dir)
        rows = []
        field_counts: Counter[str] = Counter()
        for name in names:
            task_id = Path(name).stem
            if fast_hashes.get(task_id) != dev_hashes.get(task_id):
                raise ValueError(f"v19 task hash mismatch: {task_id}")
            notice_id = task_id.split("__p", 1)[0]
            view = build_v19_requirement_view(records[notice_id].raw)
            candidates = tuple(view["candidates"])
            left = _response(fast_dir / name)
            right = _response(dev_dir / name)
            left_rows, left_reason = parse_v19_observations_relaxed_quote(left, candidates)
            right_rows, right_reason = parse_v19_observations_relaxed_quote(right, candidates)
            disagreements = (
                _field_disagreements(left_rows, right_rows, V19_SEMANTIC_FIELDS)
                if left_rows is not None and right_rows is not None else Counter()
            )
            quote_disagreements = (
                sum(a["quoted_text"] != b["quoted_text"] for a, b in zip(left_rows, right_rows))
                if left_rows is not None and right_rows is not None else None
            )
            field_counts.update(disagreements)
            left_decision = (
                reduce_v19_with_quote_resolution(candidates, left_rows)
                if left_rows is not None else (None, "", {"observations": []})
            )
            right_decision = (
                reduce_v19_with_quote_resolution(candidates, right_rows)
                if right_rows is not None else (None, "", {"observations": []})
            )
            left_positive = sum(
                bool(row.get("positive_predicate"))
                for row in left_decision[2].get("observations", [])
            )
            right_positive = sum(
                bool(row.get("positive_predicate"))
                for row in right_decision[2].get("observations", [])
            )
            rows.append({
                "id": notice_id,
                "task_id": task_id,
                "task_hash": fast_hashes[task_id],
                "exact_content_equal": left.get("content") == right.get("content"),
                "both_parse_valid": left_rows is not None and right_rows is not None,
                "parse_reasons": [left_reason, right_reason],
                "semantic_field_disagreements": dict(disagreements),
                "quote_disagreements": quote_disagreements,
                "positive_predicate_counts": [left_positive, right_positive],
                "positive_predicate_disagreement": left_positive != right_positive,
                "final_values": [left_decision[0], right_decision[0]],
                "final_value_disagreement": left_decision[0] != right_decision[0],
                "finish_reasons": [left.get("finish_reason"), right.get("finish_reason")],
                "completion_tokens": [_usage(left, "completion_tokens"), _usage(right, "completion_tokens")],
                "latency_seconds": [_latency(left), _latency(right)],
            })
        return self._summarize("v19", rows, field_counts)

    @staticmethod
    def _summarize(
        item: str, rows: Sequence[Mapping[str, Any]], field_counts: Counter[str],
    ) -> dict[str, Any]:
        return {
            "item": item,
            "identical_task_pairs": len(rows),
            "exact_content_equal": sum(row["exact_content_equal"] for row in rows),
            "exact_content_different": sum(not row["exact_content_equal"] for row in rows),
            "both_parse_valid": sum(row["both_parse_valid"] for row in rows),
            "final_value_disagreements": sum(row["final_value_disagreement"] for row in rows),
            "semantic_field_disagreements": dict(field_counts),
            "pairs": list(rows),
        }

    def run(self) -> dict[str, Any]:
        started = time.perf_counter()
        manifest = compare_manifests(self.config.path, self.root)
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")
        for path in self.paths.values():
            if not path.exists():
                raise FileNotFoundError(path)
        records = {record.notice_id: record for record in load_notice_records(self.config.input_path)}
        report = {
            "status": "PASS",
            "mode": "identical-task-independent-generation-stability",
            "inputs": {
                key: {"path": str(path), "sha256": _sha256(path) if path.is_file() else None}
                for key, path in self.paths.items()
            },
            "v3": self._v3(records),
            "v19": self._v19(records),
            "base_repeat_availability": {
                "r10": False, "B": False, "C24": False,
                "limitation": "No independently generated identical-task response pair was found.",
            },
            "calls": {"llm": 0, "embedding": 0},
            "final_prediction": False,
            "manifest_diff": manifest,
            "runtime_seconds": time.perf_counter() - started,
            "limitations": [
                "Fast/dev overlap is small and selected from adaptive dev data.",
                "OpenRouter repeat stability does not establish evaluator INT8 vLLM parity.",
                "Base r10/B/C24 arms have no independent identical-task repeats in stored outputs.",
            ],
        }
        self.output_dir.mkdir(parents=True, exist_ok=True)
        atomic_json(self.output_dir / "audit_report.json", report)
        return report
