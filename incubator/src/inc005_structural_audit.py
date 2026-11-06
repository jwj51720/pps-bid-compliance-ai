#!/usr/bin/env python3
"""Offline audit of saved incubator prompts and responses; makes no API calls."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import inc001_simple_joint24 as common


RUNS = (
    "inc001_simple_joint24_pilot",
    "inc002_v13_output_ablation",
    "inc003_v13_product_fact",
    "inc004_v13_unknown_neutrality_seedmatched",
)


def jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["id"]), str(row.get("policy", "single"))


def warning_list(response: dict[str, Any]) -> list[str]:
    value = response.get("warnings", response.get("evidence_warnings", []))
    return value if isinstance(value, list) else []


def source_doc_chars(record: dict[str, Any]) -> int:
    return sum(len(document["text"]) for document in record["docs"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="incubator/runs/inc005_structural_audit")
    args = parser.parse_args()
    root = common.repo_root()
    output = root / args.output
    output.mkdir(parents=True, exist_ok=True)
    records = {record["id"]: record for record in common.read_jsonl_gz(root / "data/raw/open/dev.jsonl.gz")}
    per_run: dict[str, Any] = {}
    all_rows: list[dict[str, Any]] = []
    warning_counts: Counter[str] = Counter()
    for run_id in RUNS:
        run = root / "incubator/runs" / run_id
        inputs = {key(row): row for row in jsonl(run / "inputs.jsonl")}
        responses = jsonl(run / "responses.jsonl")
        prompt_tokens = completion_tokens = total_cost = 0.0
        success = parseable = raw_retained = truncated = 0
        included_chars = source_chars = full_notice_count = 0
        run_warnings: Counter[str] = Counter()
        by_policy: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for response in responses:
            request = inputs.get(key(response))
            if request is None:
                raise RuntimeError(f"missing input for {run_id} {key(response)}")
            usage = response.get("usage", {}) or {}
            policy = str(response.get("policy", "single"))
            current_success = bool(response.get("success", True))
            success += current_success
            raw = str(response.get("raw_response", "") or "")
            raw_retained += bool(raw)
            if raw:
                try:
                    common.parse_json(raw)
                    parseable += 1
                except (ValueError, json.JSONDecodeError):
                    pass
            finish = response.get("finish_reason")
            truncated += finish in {"length", "max_tokens"}
            prompt = float(usage.get("prompt_tokens", 0) or 0)
            completion = float(usage.get("completion_tokens", 0) or 0)
            cost = float(usage.get("cost", 0) or 0)
            prompt_tokens += prompt
            completion_tokens += completion
            total_cost += cost
            by_policy[policy]["requests"] += 1
            by_policy[policy]["successful"] += current_success
            by_policy[policy]["prompt_tokens"] += prompt
            by_policy[policy]["completion_tokens"] += completion
            by_policy[policy]["cost"] += cost
            rendering = request["rendering"]
            included = sum(int(item["chars"]) for item in rendering["included_documents"])
            total = source_doc_chars(records[response["id"]])
            included_chars += included
            source_chars += total
            full_notice_count += included == total
            warnings = warning_list(response)
            run_warnings.update(warnings)
            warning_counts.update(warnings)
            all_rows.append({"run_id": run_id, "policy": policy, "id": response["id"], "success": current_success, "raw_retained": bool(raw), "parseable_raw": bool(raw) and _parseable(raw), "finish_reason": finish, "prompt_tokens": prompt, "completion_tokens": completion, "cost": cost, "included_document_chars": included, "source_document_chars": total, "complete_notice": included == total, "warning_count": len(warnings)})
        count = len(responses)
        per_run[run_id] = {"requests": count, "successful": success, "raw_retained": raw_retained, "parseable_raw": parseable, "truncated": truncated, "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "completion_to_prompt_ratio": completion_tokens / prompt_tokens if prompt_tokens else None, "reported_cost_usd": total_cost, "included_document_chars": included_chars, "source_document_chars": source_chars, "document_character_coverage": included_chars / source_chars if source_chars else None, "complete_notice_count": full_notice_count, "warning_count": sum(run_warnings.values()), "warnings": dict(run_warnings), "policies": {policy: dict(values) for policy, values in by_policy.items()}}
    report = {"audit": "offline saved-artifact structural audit; no new provider calls", "included_runs": list(RUNS), "excluded_runs": {"inc004_v13_unknown_neutrality": "duplicate checkpoint writers", "inc004_v13_unknown_neutrality_rerun": "seed differs from INC-003"}, "per_run": per_run, "all_runs": {"requests": len(all_rows), "successful": sum(row["success"] for row in all_rows), "raw_retained": sum(row["raw_retained"] for row in all_rows), "parseable_raw": sum(row["parseable_raw"] for row in all_rows), "warning_count": sum(row["warning_count"] for row in all_rows), "warnings": dict(warning_counts), "mean_document_character_coverage": sum(row["included_document_chars"] for row in all_rows) / sum(row["source_document_chars"] for row in all_rows)}, "row_count": len(all_rows)}
    common.write_json(output / "report.json", report)
    common.write_jsonl(output / "request_rows.jsonl", all_rows)
    print(json.dumps(report, ensure_ascii=False, indent=2))


def _parseable(raw: str) -> bool:
    try:
        common.parse_json(raw)
        return True
    except (ValueError, json.JSONDecodeError):
        return False


if __name__ == "__main__":
    main()
