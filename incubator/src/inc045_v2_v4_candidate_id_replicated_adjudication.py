#!/usr/bin/env python3
"""INC-042 replication with source candidate IDs instead of generated evidence."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

import inc001_simple_joint24 as common
import inc042_v2_v4_replicated_law_adjudication as base
from inc044_v2_v4_candidate_id_coverage_audit import candidates


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "incubator/runs/inc045_v2_v4_candidate_id_replicated_adjudication"
ITEMS = base.ITEMS
ARMS = base.ARMS


def candidate_map(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {candidate["candidate_id"]: candidate for candidate in candidates(record) if candidate["selectable"]}


def schema(record: dict[str, Any]) -> dict[str, Any]:
    ids = ["NONE", *candidate_map(record)]
    return {"type": "object", "additionalProperties": False, "required": list(ITEMS), "properties": {
        item: {"type": "object", "additionalProperties": False, "required": ["위반여부", "evidence_id"], "properties": {
            "위반여부": {"type": "integer", "enum": [0, 1]}, "evidence_id": {"type": "string", "enum": ids},
        }} for item in ITEMS
    }}


def messages(record: dict[str, Any], table: dict[str, Any], arm: str) -> list[dict[str, str]]:
    candidates_by_id = candidate_map(record)
    candidate_text = "\n".join(f"- {candidate_id}: [{row['doc_type']}] {row['source_line']}" for candidate_id, row in candidates_by_id.items()) or "- (선택 가능한 실적 금액 후보 없음)"
    system = "\n".join([
        "당신은 공공입찰 공고의 법령 위반을 독립적으로 판정한다.",
        "모든 메타데이터와 원문 문서를 읽고 v2와 v4를 각각 판정한다. 두 항목은 동시에 1일 수 있다.",
        f"- v2: {table['v2']['항목명']}", f"- v4: {table['v4']['항목명']}",
        "키워드만으로 단정하지 말고 실제 입찰참가자격 제한인지, 금액·계약법·실적 역할을 확인한다.",
        "각 항목이 1이면 아래 원문 후보 중 실제 근거 하나의 evidence_id를 선택한다. 0이면 evidence_id는 반드시 NONE이다.",
        "후보 목록은 근거 선택을 돕는 것이며, 후보가 없다는 사실만으로 0을 결정하지 않는다. JSON 객체 하나만 출력한다.",
    ])
    content = "[메타]\n" + json.dumps(record["meta"], ensure_ascii=False, sort_keys=True)
    if arm.startswith("law_"):
        content += "\n\n[적용 법령: 메타 계약법으로 선택된 완결 단위]\n" + base.law_context(str(record["meta"]["적용계약법"]))
    content += "\n\n[원문 문서]\n" + base.render_docs(record)
    content += "\n\n[선택 가능한 원문 근거 후보]\n" + candidate_text
    return [{"role": "system", "content": system}, {"role": "user", "content": content}]


def validate(payload: dict[str, Any], record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    source_candidates = candidate_map(record)
    result = {}
    for item in ITEMS:
        cell = payload.get(item)
        if not isinstance(cell, dict) or cell.get("위반여부") not in (0, 1) or not isinstance(cell.get("evidence_id"), str):
            raise ValueError(f"invalid structured cell: {item}")
        violation, evidence_id = int(cell["위반여부"]), cell["evidence_id"]
        if violation and evidence_id not in source_candidates:
            raise ValueError(f"positive without valid candidate ID: {item}")
        if not violation and evidence_id != "NONE":
            raise ValueError(f"negative with non-NONE candidate ID: {item}")
        evidence = source_candidates[evidence_id]["source_line"] if violation else ""
        result[item] = {"위반여부": violation, "evidence_id": evidence_id, "근거문구": evidence}
    return result


def append_checkpoint(entry: dict[str, Any]) -> None:
    path = OUTPUT / "checkpoint.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX); handle.write(json.dumps(entry, ensure_ascii=False) + "\n"); handle.flush(); os.fsync(handle.fileno()); fcntl.flock(handle, fcntl.LOCK_UN)


def run_one(record_id: str, arm: str) -> None:
    records, _, table = base.load_inputs(); record = records[record_id]; path = OUTPUT / "records" / f"{record_id}_{arm}.json"
    if path.exists(): return
    response: Any = None
    try:
        response = common.completion(base.request_config(), messages(record, table, arm), schema(record))
        entry = {"id": record_id, "arm": arm, "success": True, "usage": response.usage, "raw_response": response.content, "judgment": validate(common.parse_json(response.content), record)}
    except Exception as exc:
        entry = {"id": record_id, "arm": arm, "success": False, "error": f"{type(exc).__name__}: {exc}", "usage": {} if response is None else response.usage, "raw_response": "" if response is None else response.content}
    path.parent.mkdir(parents=True, exist_ok=True); common.write_json(path, entry); append_checkpoint(entry)


def aggregate() -> None:
    records, labels, _ = base.load_inputs(); ids = base.cohort(records, labels)
    report: dict[str, Any] = {"experiment_id": "inc045_v2_v4_candidate_id_replicated_adjudication", "cohort_size": len(ids), "requested_calls": len(ids) * len(ARMS), "arms": {}}
    for arm in ARMS:
        entries = [json.loads((OUTPUT / "records" / f"{record_id}_{arm}.json").read_text(encoding="utf-8")) for record_id in ids if (OUTPUT / "records" / f"{record_id}_{arm}.json").exists()]
        failures = [entry for entry in entries if not entry["success"]]
        arm_report: dict[str, Any] = {"successful_calls": len(entries) - len(failures), "failure_count": len(failures), "reported_cost_usd": sum(float(entry.get("usage", {}).get("cost", 0) or 0) for entry in entries)}
        if not failures and len(entries) == len(ids):
            per_item = []
            for item in ITEMS:
                tp = fp = fn = 0
                for entry in entries:
                    gold, pred = int(labels[entry["id"]][item]), entry["judgment"][item]["위반여부"]
                    tp += gold and pred; fp += not gold and pred; fn += gold and not pred
                per_item.append({"item": item, "tp": tp, "fp": fp, "fn": fn, "f1": base.f1(tp, fp, fn)})
            arm_report["target_macro_f1"] = sum(row["f1"] for row in per_item) / len(per_item); arm_report["per_item"] = per_item
        report["arms"][arm] = arm_report
    deltas = {}
    for repeat in ("r1", "r2"):
        control, law = report["arms"][f"control_{repeat}"], report["arms"][f"law_{repeat}"]
        if "target_macro_f1" in control and "target_macro_f1" in law: deltas[repeat] = law["target_macro_f1"] - control["target_macro_f1"]
    report["law_minus_control_deltas"] = deltas; report["promotion_gate_passed"] = len(deltas) == 2 and all(delta >= 0 for delta in deltas.values())
    common.write_json(OUTPUT / "metrics.json", report); common.write_jsonl(OUTPUT / "responses.jsonl", [json.loads(path.read_text(encoding="utf-8")) for arm in ARMS for record_id in ids if (path := OUTPUT / "records" / f"{record_id}_{arm}.json").exists()]); print(json.dumps(report, ensure_ascii=False, indent=2))


def preflight() -> None:
    records, labels, table = base.load_inputs(); ids = base.cohort(records, labels); manifest = []
    for record_id in ids:
        record = records[record_id]
        for arm in ARMS:
            request = messages(record, table, arm)
            manifest.append({"id": record_id, "arm": arm, "prompt_sha256": common.sha256_text(json.dumps(request, ensure_ascii=False, sort_keys=True)), "candidate_ids": sorted(candidate_map(record)), "message_characters": sum(len(message["content"]) for message in request)})
    common.write_json(OUTPUT / "config.json", {"items": ITEMS, "arms": ARMS, "model": base.request_config(), "max_calls": len(manifest), "max_cost_usd": 0.55, "cohort_definition": "same frozen INC-042 cohort", "evidence_transport": "candidate_id"}); common.write_jsonl(OUTPUT / "cohort.jsonl", manifest); print(json.dumps({"status": "preflight_ok", "notice_count": len(ids), "calls": len(manifest), "max_message_characters": max(row["message_characters"] for row in manifest)}, ensure_ascii=False, indent=2))


def run_all(workers: int) -> None:
    records, labels, _ = base.load_inputs(); jobs = [(record_id, arm) for record_id in base.cohort(records, labels) for arm in ARMS]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_one, record_id, arm) for record_id, arm in jobs]
        for index, future in enumerate(as_completed(futures), 1):
            future.result()
            if index % workers == 0 or index == len(futures): print(f"completed={index}/{len(futures)}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--mode", required=True, choices=("preflight", "run-all", "aggregate")); parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args(); load_dotenv(ROOT / ".env"); OUTPUT.mkdir(parents=True, exist_ok=True)
    if args.mode == "preflight": preflight()
    elif args.mode == "run-all": run_all(args.workers)
    else: aggregate()


if __name__ == "__main__": main()
