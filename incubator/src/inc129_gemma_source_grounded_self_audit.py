#!/usr/bin/env python3
"""INC-129: source-preserving second-pass audit of a Gemma V/E judgment."""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import fcntl
import gzip
import hashlib
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "incubator/submission_candidates/exp120_card_v6"))
from src.data import load_decision_cards, load_item_table  # noqa: E402
from src.pipeline import parse_judgment, postprocess_judgment  # noqa: E402
from src.prompt import build_messages, build_system_prompt  # noqa: E402
from src.schema import ABSENCE_ITEMS, ITEMS  # noqa: E402
import inc122_compact_legal_summary_pilot as transport  # noqa: E402


CFG = ROOT / "incubator/configs/inc129_gemma_source_grounded_self_audit.json"
OUT = ROOT / "incubator/runs/inc129_gemma_source_grounded_self_audit"
RAW = ROOT / "data/raw/open"
CARDS = ROOT / "incubator/reference/dev_history/decision_cards_v6.json"
EXCLUSION_FILES = (
    ROOT / "incubator/data/derived/inc119_gemma_legal_transfer16_manifest.jsonl",
    ROOT / "incubator/runs/inc121_output_contract_anchor_pilot/checkpoint.jsonl",
    ROOT / "incubator/runs/inc122_compact_legal_summary_pilot/checkpoint.jsonl",
    ROOT / "incubator/runs/inc111_gemma_case_rag_pilot/checkpoint.jsonl",
    ROOT / "incubator/runs/inc112_gemma_case_rag_confirmation16/checkpoint.jsonl",
    ROOT / "incubator/runs/inc127_gemma_operational_contract_pilot/checkpoint.jsonl",
)
AUDIT_CONTRACT = """
[이전 판단의 source-grounded audit]
아래는 같은 공고에 대해 직전 검토가 낸 V/E 판단이다. 이는 정답이나 새 사실이 아니라, 원문으로 다시 검증할 주장 목록이다. 각 항목을 독립적으로 원문·메타·카드와 대조한다. 직전 판단을 그대로 따르지 말고, 원문이 뒷받침하지 않거나 적용조건·예외와 모순되면 고친다. 원문에 있는 결정적 사실을 직전 판단이 놓쳤다면 고친다. 최종 출력은 직전 JSON을 복사하지 말고, 동일한 V/E 스키마와 원문 근거문구 규칙으로 새로 출력한다.
""".strip()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def append(path: Path, value: Any) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n"); handle.flush(); os.fsync(handle.fileno())


def profile(record: dict[str, Any]) -> str:
    if record["meta"].get("적용계약법") == "국가계약법": return "national"
    if record["meta"].get("계약방법") == "수의계약": return "local_small"
    if record["meta"].get("낙찰방법") == "협상에의한계약": return "local_negotiated"
    return "local_general"


def excluded_ids() -> set[str]:
    result: set[str] = set()
    for path in EXCLUSION_FILES:
        if path.exists(): result.update(json.loads(line)["id"] for line in path.read_text(encoding="utf-8").splitlines() if line)
    return result


def load() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, str]]]:
    with gzip.open(RAW / "dev.jsonl.gz", "rt", encoding="utf-8") as handle: records = {row["id"]: row for row in (json.loads(line) for line in handle if line)}
    with (RAW / "dev_labels.csv").open(encoding="utf-8", newline="") as handle: labels = {row["id"]: row for row in csv.DictReader(handle)}
    return records, labels


def manifest(records: dict[str, dict[str, Any]], count: int) -> list[dict[str, str]]:
    groups: dict[str, list[str]] = defaultdict(list); excluded = excluded_ids()
    for record_id, record in records.items():
        if record_id not in excluded: groups[profile(record)].append(record_id)
    rows = []
    for group in ("national", "local_general", "local_small", "local_negotiated"):
        selected = sorted(groups[group], key=lambda record_id: hashlib.sha256(f"inc129-self-audit:{group}:{record_id}".encode()).hexdigest())[:count]
        if len(selected) != count: raise RuntimeError(f"insufficient unused {group} records")
        rows.extend({"id": record_id, "profile": group, "selection": "label-blind SHA-256 rank after prior Gemma cohorts"} for record_id in selected)
    return rows


def score(rows: dict[str, dict[str, Any]], labels: dict[str, dict[str, str]], ids: list[str]) -> dict[str, Any]:
    per, evidence_valid = [], 0; positive = 0
    for item in ITEMS:
        tp = fp = fn = 0
        for record_id in ids:
            actual, predicted = int(labels[record_id][item]), int(rows[record_id]["labels"][item])
            tp += actual == predicted == 1; fp += actual == 0 and predicted == 1; fn += actual == 1 and predicted == 0
            if predicted:
                positive += 1; evidence_valid += bool(rows[record_id]["evidence"].get(item)) or item in ABSENCE_ITEMS
        precision = tp / (tp + fp) if tp + fp else 0.; recall = tp / (tp + fn) if tp + fn else 0.
        per.append({"item": item, "tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.})
    return {"macro_f1": sum(row["f1"] for row in per) / len(per), "recall_micro": sum(row["tp"] for row in per) / max(1, sum(row["tp"] + row["fn"] for row in per)), "evidence_valid_rate": evidence_valid / positive if positive else 1., "per_item": per}


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rendered_prior(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item: {"위반여부": int(row["labels"][item]), "근거문구": row["evidence"].get(item)} for item in ITEMS}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--mode", choices=("preflight", "mock", "run", "aggregate"), required=True); args = parser.parse_args()
    config = json.loads(CFG.read_text(encoding="utf-8")); records, labels = load(); table = load_item_table(RAW / "data/항목표.json"); cards = load_decision_cards(CARDS, table)
    cohort = manifest(records, int(config["cohort_per_profile"])); ids = [row["id"] for row in cohort]; base_system = build_system_prompt(table, decision_cards=cards)
    direct_messages = {record_id: build_messages(records[record_id], base_system, int(config["context_chars"])) for record_id in ids}
    preflight = {"experiment_id": config["experiment_id"], "config": config, "requests": config["max_requests"], "cohort_ids_sha256": hashlib.sha256("\n".join(ids).encode()).hexdigest(), "excluded_count": len(excluded_ids()), "source_sha256": {"dev": digest(RAW / "dev.jsonl.gz"), "labels": digest(RAW / "dev_labels.csv"), "cards": digest(CARDS)}, "labels_excluded_from_messages": True, "audit_contract_sha256": hashlib.sha256(AUDIT_CONTRACT.encode()).hexdigest()}
    OUT.mkdir(parents=True, exist_ok=True); write(OUT / "config.json", config); write(OUT / "preflight.json", preflight); (OUT / "cohort.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in cohort), encoding="utf-8")
    if args.mode == "preflight": print(json.dumps({"status": "preflight_ok", **preflight}, ensure_ascii=False, indent=2)); return
    if args.mode == "mock":
        for record_id in ids: postprocess_judgment({item: {"위반여부": 0, "근거문구": None} for item in ITEMS}, records[record_id])
        print(json.dumps({"status": "mock_ok", "requests": config["max_requests"]}, ensure_ascii=False)); return
    checkpoint = OUT / "checkpoint.jsonl"; done = {}
    if checkpoint.exists():
        for line in checkpoint.read_text(encoding="utf-8").splitlines():
            row = json.loads(line); done[(row["stage"], row["id"])] = row
    def invoke(stage: str, record_id: str, messages: list[dict[str, str]]) -> dict[str, Any]:
        result = transport.request(config, messages); result.update({"id": record_id, "stage": stage})
        if result["success"]:
            try:
                processed = postprocess_judgment(result.pop("judgment"), records[record_id]); result["labels"] = {item: processed[item]["위반여부"] for item in ITEMS}; result["evidence"] = {item: processed[item]["근거문구"] for item in ITEMS}
            except Exception as exc: result = {"id": record_id, "stage": stage, "success": False, "error": f"postprocess:{type(exc).__name__}:{exc}", "usage": {}, "raw_response": "", "latency_seconds": 0., "model": config["model"]}
        return result
    if args.mode == "run":
        load_dotenv(ROOT / ".env");
        if not os.environ.get(config["api_key_env"]): raise RuntimeError("missing API key")
        lock = (OUT / ".active.lock").open("w")
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc: raise SystemExit("INC-129 already running") from exc
        for stage in ("direct", "audit"):
            if stage == "direct": prepared = [(record_id, direct_messages[record_id]) for record_id in ids if (stage, record_id) not in done]
            else:
                direct = {record_id: done[("direct", record_id)] for record_id in ids if done.get(("direct", record_id), {}).get("success")}
                if len(direct) != len(ids): raise RuntimeError("all direct calls must succeed before audit")
                prepared = []
                for record_id in ids:
                    if (stage, record_id) in done: continue
                    messages = [dict(message) for message in direct_messages[record_id]]
                    messages[-1]["content"] += "\n\n" + AUDIT_CONTRACT + "\n[직전 판단]\n" + json.dumps(rendered_prior(direct[record_id]), ensure_ascii=False, sort_keys=True)
                    prepared.append((record_id, messages))
            with concurrent.futures.ThreadPoolExecutor(max_workers=config["max_workers"]) as executor:
                futures = {executor.submit(invoke, stage, record_id, messages): record_id for record_id, messages in prepared}
                for number, future in enumerate(concurrent.futures.as_completed(futures), 1):
                    row = future.result(); done[(stage, row["id"])] = row; append(checkpoint, row); print(f"{stage} {number}/{len(prepared)} {row['id']} success={row['success']}", flush=True)
        return
    report = {"experiment_id": config["experiment_id"], "cohort_size": len(ids), "stages": {}}
    for stage in ("direct", "audit"):
        rows = [done.get((stage, record_id)) for record_id in ids]; valid = {row["id"]: row for row in rows if row and row["success"]}; entry = {"success": len(valid), "failures": len(rows) - len(valid), "reported_cost_usd": sum(float((row or {}).get("usage", {}).get("cost", 0) or 0) for row in rows)}
        if not entry["failures"]: entry.update(score(valid, labels, ids))
        report["stages"][stage] = entry
    direct, audit = report["stages"]["direct"], report["stages"]["audit"]
    if "macro_f1" in direct and "macro_f1" in audit: report["delta"] = {"macro_f1": audit["macro_f1"] - direct["macro_f1"], "recall_micro": audit["recall_micro"] - direct["recall_micro"], "evidence_valid_rate": audit["evidence_valid_rate"] - direct["evidence_valid_rate"]}
    write(OUT / "metrics.json", report); print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
