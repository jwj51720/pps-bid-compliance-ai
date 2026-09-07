#!/usr/bin/env python3
"""INC-127: paired Gemma test of a fixed full-notice operational contract."""

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


CFG = ROOT / "incubator/configs/inc127_gemma_operational_contract_pilot.json"
OUT = ROOT / "incubator/runs/inc127_gemma_operational_contract_pilot"
RAW = ROOT / "data/raw/open"
CARDS = ROOT / "incubator/reference/dev_history/decision_cards_v6.json"
EXCLUSION_FILES = (
    ROOT / "incubator/data/derived/inc119_gemma_legal_transfer16_manifest.jsonl",
    ROOT / "incubator/runs/inc121_output_contract_anchor_pilot/checkpoint.jsonl",
    ROOT / "incubator/runs/inc122_compact_legal_summary_pilot/checkpoint.jsonl",
    ROOT / "incubator/runs/inc111_gemma_case_rag_pilot/checkpoint.jsonl",
    ROOT / "incubator/runs/inc112_gemma_case_rag_confirmation16/checkpoint.jsonl",
)
OPERATIONS = """
[판단 순서 계약]
각 항목을 독립적으로 아래 순서로 검토한다.
1) 제한·실적·제품 항목은 먼저 실제 입찰참가자격을 제한하는 원문 사실을 찾는다. 일반 안내, 법령 소개, 낙찰 이후 의무, 하도급·지원 정책 언급은 참가자격 제한이 아니다. 그 다음에만 카드의 적용대상·금액·예외를 대조한다.
2) [부재탐지]는 먼저 이 공고가 해당 제도의 적용대상인지 확인하고, 적용대상이 확인된 경우에만 제공된 모든 공고 문서에서 필요한 조건의 존재를 검사한다. 적용대상이 불명확하면 부재를 위반으로 단정하지 않는다.
3) v24는 예산-예산, 계약방법-계약방법, 참가자격 지역제한-지역제한, 참가자격 업종제한-업종제한만 같은 필드끼리 대조한다. 원문 미기재, 표현·분류 차이, 일반 지역 언급, 다른 필드는 불일치가 아니다.
위 절차는 판단 순서일 뿐 새 사실을 만들지 않는다. 근거문구는 언제나 공고 원문에서 변경 없이 복사한다.
""".strip()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def append(path: Path, value: Any) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def profile(record: dict[str, Any]) -> str:
    meta = record["meta"]
    if meta.get("적용계약법") == "국가계약법": return "national"
    if meta.get("계약방법") == "수의계약": return "local_small"
    if meta.get("낙찰방법") == "협상에의한계약": return "local_negotiated"
    return "local_general"


def excluded_ids() -> set[str]:
    ids: set[str] = set()
    for path in EXCLUSION_FILES:
        if path.exists():
            ids.update(json.loads(line)["id"] for line in path.read_text(encoding="utf-8").splitlines() if line)
    return ids


def load() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, str]]]:
    with gzip.open(RAW / "dev.jsonl.gz", "rt", encoding="utf-8") as handle:
        records = {row["id"]: row for row in (json.loads(line) for line in handle if line.strip())}
    with (RAW / "dev_labels.csv").open(encoding="utf-8", newline="") as handle:
        labels = {row["id"]: row for row in csv.DictReader(handle)}
    return records, labels


def manifest(records: dict[str, dict[str, Any]], count: int) -> list[dict[str, str]]:
    excluded = excluded_ids(); groups: dict[str, list[str]] = defaultdict(list)
    for record_id, record in records.items():
        if record_id not in excluded: groups[profile(record)].append(record_id)
    rows = []
    for group in ("national", "local_general", "local_small", "local_negotiated"):
        picks = sorted(groups[group], key=lambda record_id: hashlib.sha256(f"inc127-operational:{group}:{record_id}".encode()).hexdigest())[:count]
        if len(picks) != count: raise RuntimeError(f"insufficient unused records for {group}")
        rows.extend({"id": record_id, "profile": group, "selection": "label-blind SHA-256 rank after all prior Gemma cohorts"} for record_id in picks)
    return rows


def score(rows: dict[str, dict[str, Any]], labels: dict[str, dict[str, str]], ids: list[str]) -> dict[str, Any]:
    per, absence_fp = [], 0
    for item in ITEMS:
        tp = fp = fn = 0
        for record_id in ids:
            actual, predicted = int(labels[record_id][item]), int(rows[record_id]["labels"][item])
            tp += actual == predicted == 1; fp += actual == 0 and predicted == 1; fn += actual == 1 and predicted == 0
        if item in ABSENCE_ITEMS: absence_fp += fp
        precision = tp / (tp + fp) if tp + fp else 0.0; recall = tp / (tp + fn) if tp + fn else 0.0
        per.append({"item": item, "tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0})
    return {"macro_f1": sum(row["f1"] for row in per) / len(per), "recall_micro": sum(row["tp"] for row in per) / max(1, sum(row["tp"] + row["fn"] for row in per)), "absence_false_positives": absence_fp, "per_item": per}


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--mode", required=True, choices=("preflight", "mock", "run", "aggregate")); args = parser.parse_args()
    config = json.loads(CFG.read_text(encoding="utf-8")); records, labels = load(); table = load_item_table(RAW / "data/항목표.json"); cards = load_decision_cards(CARDS, table)
    rows = manifest(records, int(config["cohort_per_profile"])); ids = [row["id"] for row in rows]
    base_system = build_system_prompt(table, decision_cards=cards); prepared = []
    for row in rows:
        for arm in config["arms"]:
            system = base_system if arm == "card_v6" else base_system + "\n\n" + OPERATIONS
            messages = build_messages(records[row["id"]], system, int(config["context_chars"]))
            prepared.append({"id": row["id"], "profile": row["profile"], "arm": arm, "messages": messages, "prompt_sha256": hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True).encode()).hexdigest()})
    preflight = {"experiment_id": config["experiment_id"], "config": config, "cohort_ids_sha256": hashlib.sha256("\n".join(ids).encode()).hexdigest(), "excluded_count": len(excluded_ids()), "requests": len(prepared), "source_sha256": {"dev": digest(RAW / "dev.jsonl.gz"), "labels": digest(RAW / "dev_labels.csv"), "cards": digest(CARDS)}, "labels_excluded_from_messages": True, "operation_sha256": hashlib.sha256(OPERATIONS.encode()).hexdigest()}
    OUT.mkdir(parents=True, exist_ok=True); write(OUT / "config.json", config); write(OUT / "preflight.json", preflight); (OUT / "cohort.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    if len(prepared) != config["max_requests"]: raise RuntimeError("unexpected request count")
    if args.mode == "preflight": print(json.dumps({"status": "preflight_ok", **preflight}, ensure_ascii=False, indent=2)); return
    if args.mode == "mock":
        for entry in prepared: postprocess_judgment({item: {"위반여부": 0, "근거문구": None} for item in ITEMS}, records[entry["id"]])
        print(json.dumps({"status": "mock_ok", "requests": len(prepared)}, ensure_ascii=False)); return
    checkpoint = OUT / "checkpoint.jsonl"; done = {}
    if checkpoint.exists():
        for line in checkpoint.read_text(encoding="utf-8").splitlines():
            row = json.loads(line); done[(row["id"], row["arm"])] = row
    if args.mode == "run":
        load_dotenv(ROOT / ".env")
        if not os.environ.get(config["api_key_env"]): raise RuntimeError("missing API key")
        lock = (OUT / ".active.lock").open("w")
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc: raise SystemExit("INC-127 already running") from exc
        pending = [entry for entry in prepared if (entry["id"], entry["arm"]) not in done]
        def work(entry: dict[str, Any]) -> dict[str, Any]:
            result = transport.request(config, entry["messages"]); result.update({"id": entry["id"], "arm": entry["arm"], "profile": entry["profile"]})
            if result["success"]:
                try:
                    processed = postprocess_judgment(result.pop("judgment"), records[entry["id"]]); result["labels"] = {item: processed[item]["위반여부"] for item in ITEMS}; result["evidence"] = {item: processed[item]["근거문구"] for item in ITEMS}
                except Exception as exc: result = {"id": entry["id"], "arm": entry["arm"], "profile": entry["profile"], "success": False, "error": f"postprocess:{type(exc).__name__}:{exc}", "usage": {}, "raw_response": "", "latency_seconds": 0.0, "model": config["model"]}
            return result
        with concurrent.futures.ThreadPoolExecutor(max_workers=config["max_workers"]) as executor:
            futures = {executor.submit(work, entry): entry for entry in pending}
            for number, future in enumerate(concurrent.futures.as_completed(futures), 1):
                result = future.result(); append(checkpoint, result); print(f"completed={number}/{len(pending)} {result['id']}/{result['arm']} success={result['success']}", flush=True)
        return
    report = {"experiment_id": config["experiment_id"], "cohort_size": len(ids), "arms": {}}
    for arm in config["arms"]:
        arm_rows = [done.get((record_id, arm)) for record_id in ids]; successful = {row["id"]: row for row in arm_rows if row and row["success"]}; failures = len(arm_rows) - len(successful)
        arm_report = {"success": len(successful), "failures": failures, "reported_cost_usd": sum(float((row or {}).get("usage", {}).get("cost", 0) or 0) for row in arm_rows)}
        if not failures: arm_report.update(score(successful, labels, ids))
        report["arms"][arm] = arm_report
    control, treatment = report["arms"]["card_v6"], report["arms"]["operational_contract"]
    if "macro_f1" in control and "macro_f1" in treatment: report["delta"] = {"macro_f1": treatment["macro_f1"] - control["macro_f1"], "recall_micro": treatment["recall_micro"] - control["recall_micro"], "absence_false_positives": treatment["absence_false_positives"] - control["absence_false_positives"]}
    write(OUT / "metrics.json", report); print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
