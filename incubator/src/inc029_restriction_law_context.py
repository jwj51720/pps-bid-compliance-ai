#!/usr/bin/env python3
"""INC-029: paired restriction-law context pilot with durable per-arm records."""

from __future__ import annotations

import argparse
import csv
import fcntl
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

import inc001_simple_joint24 as common
from inc023_article_context_audit import active_body


ROOT = Path(__file__).resolve().parents[2]
ITEMS = ("v4", "v6", "v7", "v8")
OUTPUT = ROOT / "incubator/runs/inc029_restriction_law_context"
LAW_DIR = ROOT / "data/raw/open/data/법령패키지/법령"


def load_inputs() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, str]], dict[str, Any]]:
    data = ROOT / "data/raw/open"
    records = {row["id"]: row for row in common.read_jsonl_gz(data / "dev.jsonl.gz")}
    labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}
    table = json.loads((data / "data/항목표.json").read_text(encoding="utf-8"))["항목"]
    return records, labels, table


def stratum(record: dict[str, Any]) -> tuple[str, str]:
    return str(record["meta"].get("적용계약법")), str(record["meta"].get("계약방법"))


def cohort(records: dict[str, dict[str, Any]], labels: dict[str, dict[str, str]]) -> list[str]:
    positives = sorted(record_id for record_id, row in labels.items() if any(row[item] == "1" for item in ITEMS))
    if len(positives) != 21:
        raise RuntimeError(f"expected 21 positive notices, got {len(positives)}")
    positive_strata = sorted({stratum(records[record_id]) for record_id in positives})
    negative_pools: dict[tuple[str, str], list[str]] = defaultdict(list)
    for record_id, row in labels.items():
        if all(row[item] == "0" for item in ITEMS):
            negative_pools[stratum(records[record_id])].append(record_id)
    for pool in negative_pools.values():
        pool.sort()
    selected = list(positives)
    positions = defaultdict(int)
    while len(selected) < 36:
        progressed = False
        for key in positive_strata:
            pool = negative_pools[key]
            if positions[key] < len(pool):
                selected.append(pool[positions[key]])
                positions[key] += 1
                progressed = True
                if len(selected) == 36:
                    break
        if not progressed:
            raise RuntimeError("not enough stratum-matched negatives")
    return selected


def complete_article(filename: str, article: str) -> str:
    text = active_body((LAW_DIR / filename).read_text(encoding="utf-8"))
    match = re.search(rf"(?m)^제{re.escape(article)}(?:\s*\([^\n]*\))?", text)
    if not match:
        raise RuntimeError(f"article not found: {filename} {article}")
    next_match = re.search(r"(?m)^제\d+조(?:의\d+)?(?:\s*\([^\n]*\))?", text[match.end():])
    end = match.end() + next_match.start() if next_match else len(text)
    return text[match.start():end].strip()


def between(filename: str, start: str, end: str) -> str:
    text = active_body((LAW_DIR / filename).read_text(encoding="utf-8"))
    start_match = re.search(start, text, re.MULTILINE)
    if not start_match:
        raise RuntimeError(f"start boundary not found: {filename}")
    end_match = re.search(end, text[start_match.end():], re.MULTILINE)
    if not end_match:
        raise RuntimeError(f"end boundary not found: {filename}")
    return text[start_match.start():start_match.end() + end_match.start()].strip()


def law_context(contract_law: str) -> str:
    if contract_law == "국가계약법":
        units = [
            ("정부 입찰·계약 집행기준 제5조", complete_article("(계약예규) 정부 입찰·계약 집행기준.txt", "5조")),
            ("국가계약법 시행규칙 제25조", complete_article("국가를 당사자로 하는 계약에 관한 법률 시행규칙.txt", "25조")),
        ]
    elif contract_law == "지방계약법":
        units = [
            ("지방계약법 시행규칙 제25조", complete_article("지방자치단체를 당사자로 하는 계약에 관한 법률 시행규칙.txt", "25조")),
            ("지방계약 집행기준 제1장 7", between("지방자치단체 입찰 및 계약 집행기준.txt", r"^7\. 계약담당자 주의사항$", r"^8\. 계약정보의 공개$")),
            ("지방계약 집행기준 제5장 제3절 1", between("지방자치단체 입찰 및 계약 집행기준.txt", r"^1\. 금액기준에 따른 2인 이상 견적서 제출 수의계약$", r"^2\. 금액기준에 따른 1인 견적서 제출 가능 수의계약$")),
        ]
    else:
        raise RuntimeError(f"unsupported contract law: {contract_law}")
    return "\n\n".join(f"[법령: {name}]\n{text}" for name, text in units)


def render_docs(record: dict[str, Any]) -> str:
    ordered = sorted(record["docs"], key=lambda doc: (common.DOCUMENT_ORDER[doc["type"]], doc["doc_id"]))
    return "\n\n".join(f"[{doc['type']}:{doc['doc_id']}]\n{doc['text']}" for doc in ordered)


def schema() -> dict[str, Any]:
    return {"type": "object", "additionalProperties": False, "required": list(ITEMS), "properties": {
        item: {"type": "object", "additionalProperties": False, "required": ["위반여부", "근거문구"],
               "properties": {"위반여부": {"type": "integer", "enum": [0, 1]}, "근거문구": {"type": ["string", "null"], "maxLength": 500}}}
        for item in ITEMS}}


def messages(record: dict[str, Any], table: dict[str, Any], arm: str) -> list[dict[str, str]]:
    definitions = "\n".join(f"- {item}: {table[item]['항목명']}" for item in ITEMS)
    system = "\n".join([
        "당신은 공공입찰 공고의 법령 위반을 판단한다.",
        "제공된 메타와 모든 원문 문서를 읽고 각 항목을 독립적으로 판정한다.",
        "키워드만으로 위반을 단정하지 말고 적용 계약법, 금액·지역·실적 조건과 실제 제한을 함께 확인한다.",
        "1이면 근거문구는 원문 문서의 변경 없는 연속 부분문자열(500자 이하)이어야 한다. 0이면 null이다.",
        "법령 텍스트는 판단기준이며 근거문구로 인용하지 않는다.", "판정 항목:", definitions,
        "JSON 객체 하나만 출력한다. 각 항목은 {\"위반여부\": 0 또는 1, \"근거문구\": 문자열 또는 null}이다.",
    ])
    content = "[메타]\n" + json.dumps(record["meta"], ensure_ascii=False, sort_keys=True)
    if arm == "law":
        content += "\n\n[적용 법령: 메타의 적용계약법으로 선택됨]\n" + law_context(str(record["meta"]["적용계약법"]))
    content += "\n\n[원문 문서]\n" + render_docs(record)
    return [{"role": "system", "content": system}, {"role": "user", "content": content}]


def validate(payload: dict[str, Any], record: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    source = "\n".join(doc["text"] for doc in record["docs"])
    result, warnings = {}, []
    for item in ITEMS:
        cell = payload.get(item)
        if not isinstance(cell, dict) or cell.get("위반여부") not in (0, 1):
            raise ValueError(f"invalid cell {item}")
        violation, evidence = int(cell["위반여부"]), cell.get("근거문구")
        evidence = evidence.strip() if isinstance(evidence, str) else ""
        if violation and evidence not in source:
            warnings.append(f"{item}: invalid evidence; downgraded")
            violation, evidence = 0, ""
        if not violation:
            evidence = ""
        result[item] = {"위반여부": violation, "근거문구": evidence[:500]}
    return result, warnings


def request_config() -> dict[str, Any]:
    return {"model": "google/gemma-4-26b-a4b-it", "api_url": "https://openrouter.ai/api/v1/chat/completions", "api_key_env": "OPENROUTER_API_KEY", "temperature": 0.0, "seed": 20260905, "max_tokens": 1000, "timeout_seconds": 120, "request_retries": 1}


def append_checkpoint(path: Path, entry: dict[str, Any]) -> None:
    """Serialize concurrent per-notice writers; record files remain authoritative."""
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
        fcntl.flock(handle, fcntl.LOCK_UN)


def run_one(record_id: str, arm: str) -> None:
    records, _, table = load_inputs(); record = records[record_id]; result_path = OUTPUT / "records" / f"{record_id}_{arm}.json"; result_path.parent.mkdir(parents=True, exist_ok=True)
    response: Any = None
    try:
        response = common.completion(request_config(), messages(record, table, arm), schema())
        judgment, warnings = validate(common.parse_json(response.content), record)
        entry = {"id": record_id, "arm": arm, "success": True, "usage": response.usage, "raw_response": response.content, "judgment": judgment, "warnings": warnings}
    except Exception as exc:
        entry = {"id": record_id, "arm": arm, "success": False, "error": f"{type(exc).__name__}: {exc}", "usage": {} if response is None else response.usage, "raw_response": "" if response is None else response.content}
    append_checkpoint(OUTPUT / "checkpoint.jsonl", entry); common.write_json(result_path, entry)


def f1(tp: int, fp: int, fn: int) -> float:
    return 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0


def aggregate() -> None:
    records, labels, _ = load_inputs(); ids = cohort(records, labels); entries = []
    for record_id in ids:
        for arm in ("control", "law"):
            path = OUTPUT / "records" / f"{record_id}_{arm}.json"
            if path.exists(): entries.append(json.loads(path.read_text(encoding="utf-8")))
    output: dict[str, Any] = {"experiment_id": "inc029_restriction_law_context", "cohort_ids": ids, "requested_calls": len(ids) * 2, "observed_calls": len(entries), "arms": {}}
    for arm in ("control", "law"):
        arm_entries = [entry for entry in entries if entry["arm"] == arm]
        tp = fp = fn = positives = valid = 0; per_item = []
        for item in ITEMS:
            itp = ifp = ifn = 0
            for entry in arm_entries:
                gold = int(labels[entry["id"]][item])
                pred = int(entry.get("judgment", {}).get(item, {}).get("위반여부", 0))
                itp += gold and pred; ifp += not gold and pred; ifn += gold and not pred
                if pred:
                    positives += 1; valid += bool(entry["judgment"][item]["근거문구"] in "\n".join(doc["text"] for doc in records[entry["id"]]["docs"]))
            tp += itp; fp += ifp; fn += ifn; per_item.append({"item": item, "tp": itp, "fp": ifp, "fn": ifn, "f1": f1(itp, ifp, ifn)})
        output["arms"][arm] = {"successful_calls": sum(entry["success"] for entry in arm_entries), "failure_count": sum(not entry["success"] for entry in arm_entries), "macro_f1": sum(row["f1"] for row in per_item) / len(ITEMS), "tp": tp, "fp": fp, "fn": fn, "recall_micro": tp / (tp + fn) if tp + fn else 0.0, "evidence_validity": valid / positives if positives else None, "reported_cost_usd": sum(float(entry["usage"].get("cost", 0) or 0) for entry in arm_entries), "per_item": per_item}
    common.write_json(OUTPUT / "metrics.json", output); common.write_jsonl(OUTPUT / "responses.jsonl", entries); print(json.dumps(output, ensure_ascii=False, indent=2))


def preflight() -> None:
    records, labels, table = load_inputs(); ids = cohort(records, labels)
    manifest = []
    for record_id in ids:
        record = records[record_id]
        manifest.append({"id": record_id, "stratum": stratum(record), "target_positive_count": sum(labels[record_id][item] == "1" for item in ITEMS), "control_prompt_sha256": common.sha256_text(json.dumps(messages(record, table, "control"), ensure_ascii=False, sort_keys=True)), "law_prompt_sha256": common.sha256_text(json.dumps(messages(record, table, "law"), ensure_ascii=False, sort_keys=True))})
    common.write_json(OUTPUT / "config.json", {"items": ITEMS, "model": request_config(), "max_calls": 72, "max_cost_usd": 0.25})
    common.write_jsonl(OUTPUT / "cohort.jsonl", manifest)
    print(json.dumps({"status": "preflight_ok", "notice_count": len(ids), "calls": len(ids) * 2, "ids": ids}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--mode", choices=("preflight", "run", "aggregate"), required=True); parser.add_argument("--id"); parser.add_argument("--arm", choices=("control", "law"))
    args = parser.parse_args(); load_dotenv(ROOT / ".env"); OUTPUT.mkdir(parents=True, exist_ok=True)
    if args.mode == "preflight": preflight()
    elif args.mode == "aggregate": aggregate()
    elif not args.id or not args.arm: parser.error("run requires --id and --arm")
    else: run_one(args.id, args.arm)


if __name__ == "__main__": main()
