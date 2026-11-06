"""Zero-call exact-source quote recovery for stored v5 role observations."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .config import CleanExperimentConfig
from .decisions.v19_quote_resolution_v2 import resolve_exact_quote
from .preflight import compare_manifests
from .runtime.openrouter import atomic_json
from .runtime.tokenizer import GemmaTokenCounter
from .v5_full_source_role_probe import ROLES, _aggregate


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_recovered_response(response: Mapping[str, Any], task: Mapping[str, Any]) -> dict[str, Any]:
    if response.get("finish_reason") != "stop" or response.get("invalid") is True:
        raise ValueError("response did not finish normally")
    value = json.loads(str(response.get("content") or ""))
    if not isinstance(value, dict) or set(value) != {"role", "quote"}:
        raise ValueError("role response shape mismatch")
    role, quote = value["role"], value["quote"]
    if role not in ROLES or not isinstance(quote, str) or len(quote) > 500:
        raise ValueError("role/quote contract mismatch")
    if role == "BIDDER_LOCATION" and not quote:
        raise ValueError("positive role requires source quote")
    if not quote:
        return {"role": role, "quote": "", "method": "EMPTY_NONPOSITIVE", "matches": 0}
    matches = []
    for source_index, text in enumerate(task["source_texts"]):
        resolved, method = resolve_exact_quote(text, quote)
        if resolved is not None:
            matches.append((source_index, resolved, method))
    if not matches:
        raise ValueError("quote cannot be recovered from current actual source")
    exact_matches = [match for match in matches if match[2] == "BYTE_EXACT"]
    source_index, resolved, method = (exact_matches or matches)[0]
    if not 1 <= len(resolved) <= 500 or resolved not in task["source_texts"][source_index]:
        raise ValueError("resolved quote is not a valid exact source substring")
    return {
        "role": role, "quote": resolved, "method": method,
        "matches": len(matches), "source_fragment_index": source_index,
    }


def replay(config: CleanExperimentConfig) -> dict[str, Any]:
    root = config.path.parents[2]
    manifest = compare_manifests(config.path, root)
    if manifest["status"] != "PASS":
        raise ValueError("manifest policy diff failed")
    stored = root / config.raw["v5_role_quote_recovery"]["stored_output_dir"]
    source_report = json.loads((stored / "report.json").read_text(encoding="utf-8"))
    ledger = json.loads((stored / "source_ledger.json").read_text(encoding="utf-8"))
    tokenizer = GemmaTokenCounter(config.tokenizer_dir)
    rows = []
    for source in ledger:
        notice_id, part = source["id"], source["part"]
        task_path = stored / "rendered" / f"{notice_id}__p{part:02d}.json"
        response_path = stored / "responses" / f"{notice_id}__p{part:02d}.json"
        task = json.loads(task_path.read_text(encoding="utf-8"))
        response = json.loads(response_path.read_text(encoding="utf-8"))
        if tokenizer.task_sha256(task) != source["task_sha256"] \
                or response.get("task_sha256") != source["task_sha256"]:
            raise ValueError(f"{notice_id}/p{part}: task/response hash mismatch")
        parsed = parse_recovered_response(response, task)
        rows.append({"id": notice_id, "part": part, "valid": True, **parsed,
                     "task_sha256": source["task_sha256"],
                     "response_sha256": _sha256(response_path)})
    if len(rows) != source_report["calls"]:
        raise ValueError("replay call count differs")
    by_id: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_id.setdefault(row["id"], []).append(row)
    for notice_id, prior in source_report["per_notice"].items():
        for part in prior["parts"]:
            if part["valid"]:
                current = next(row for row in by_id[notice_id] if row["part"] == part["part"])
                if current["role"] != part["role"] or current["quote"] != part["quote"]:
                    raise ValueError(f"{notice_id}: valid strict response changed")
    report = {
        "status": "PASS", "mode": "stored-response-quote-replay",
        "base_manifest": config.raw["experiment"]["base_config"],
        "allowed_policy_changes": config.raw["experiment"]["allowed_policy_changes"],
        "source_report_sha256": _sha256(stored / "report.json"),
        "source_ledger_sha256": _sha256(stored / "source_ledger.json"),
        "calls": len(rows), "notices": len(by_id), "llm_calls": 0,
        "recovered_strict_invalid": source_report["invalid"],
        "remaining_invalid": 0,
        "per_notice": {notice_id: {
            "role": _aggregate(parts), "parts": sorted(parts, key=lambda row: row["part"]),
        } for notice_id, parts in sorted(by_id.items())},
        "final_v5_labels_changed": 0,
    }
    config.output_dir.mkdir(parents=True, exist_ok=True)
    atomic_json(config.output_dir / "report.json", report)
    return report
