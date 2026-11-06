#!/usr/bin/env python3
"""Replicated, source-validated active v2/v4 law-context pilot."""

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
from inc023_article_context_audit import active_body
from inc038_qualification_family_fact_coverage_audit import source_facts


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "incubator/runs/inc042_v2_v4_replicated_law_adjudication"
LAW_DIR = ROOT / "data/raw/open/data/법령패키지/법령"
ITEMS = ("v2", "v4")
ARMS = ("control_r1", "law_r1", "control_r2", "law_r2")


def load_inputs() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, str]], dict[str, Any]]:
    data = ROOT / "data/raw/open"
    records = {row["id"]: row for row in common.read_jsonl_gz(data / "dev.jsonl.gz")}
    labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}
    table = json.loads((data / "data/항목표.json").read_text(encoding="utf-8"))["항목"]
    return records, labels, table


def cohort(records: dict[str, dict[str, Any]], labels: dict[str, dict[str, str]]) -> list[str]:
    positives = {record_id for record_id, row in labels.items() if any(row[item] == "1" for item in ITEMS)}
    hard_negatives = {
        record_id for record_id, record in records.items()
        if all(labels[record_id][item] == "0" for item in ITEMS)
        and bool(source_facts(record).get("performance_amount"))
    }
    result = sorted(positives | hard_negatives)
    if len(positives) != 10 or len(hard_negatives) != 26 or len(result) != 36:
        raise RuntimeError(f"unexpected frozen cohort sizes: positives={len(positives)} hard_negatives={len(hard_negatives)} total={len(result)}")
    return result


def complete_article(filename: str, article: str) -> str:
    text = active_body((LAW_DIR / filename).read_text(encoding="utf-8"))
    start = text.find(f"제{article}")
    if start < 0:
        raise RuntimeError(f"missing article {article} in {filename}")
    import re
    next_match = re.search(r"(?m)^제\d+조(?:의\d+)?(?:\s*\([^\n]*\))?", text[start + 1:])
    end = start + 1 + next_match.start() if next_match else len(text)
    return text[start:end].strip()


def between(filename: str, start_text: str, end_text: str) -> str:
    text = active_body((LAW_DIR / filename).read_text(encoding="utf-8"))
    start = text.find(start_text)
    end = text.find(end_text, start + len(start_text))
    if start < 0 or end < 0:
        raise RuntimeError(f"missing named section in {filename}")
    return text[start:end].strip()


def law_context(contract_law: str) -> str:
    notice = (LAW_DIR / "국가를 당사자로 하는 계약에 관한 법률 등의 재정경제부장관이 정하는 고시금액.txt").read_text(encoding="utf-8").strip()
    if contract_law == "국가계약법":
        units = [
            ("2026 고시금액", notice),
            ("정부 입찰·계약 집행기준 제5조", complete_article("(계약예규) 정부 입찰·계약 집행기준.txt", "5조")),
            ("국가계약법 시행규칙 제25조", complete_article("국가를 당사자로 하는 계약에 관한 법률 시행규칙.txt", "25조")),
        ]
    elif contract_law == "지방계약법":
        units = [
            ("2026 고시금액", notice),
            ("지방계약법 시행규칙 제25조", complete_article("지방자치단체를 당사자로 하는 계약에 관한 법률 시행규칙.txt", "25조")),
            ("지방계약 집행기준 계약담당자 주의사항", between("지방자치단체 입찰 및 계약 집행기준.txt", "7. 계약담당자 주의사항", "8. 계약정보의 공개")),
        ]
    else:
        raise RuntimeError(f"unsupported contract law: {contract_law}")
    return "\n\n".join(f"[법령: {name}]\n{text}" for name, text in units)


def render_docs(record: dict[str, Any]) -> str:
    docs = sorted(record["docs"], key=lambda doc: (common.DOCUMENT_ORDER[doc["type"]], doc["doc_id"]))
    return "\n\n".join(f"[{doc['type']}:{doc['doc_id']}]\n{doc['text']}" for doc in docs)


def schema() -> dict[str, Any]:
    return {"type": "object", "additionalProperties": False, "required": list(ITEMS), "properties": {
        item: {"type": "object", "additionalProperties": False, "required": ["위반여부", "근거문구"], "properties": {
            "위반여부": {"type": "integer", "enum": [0, 1]},
            "근거문구": {"type": ["string", "null"], "maxLength": 500},
        }} for item in ITEMS
    }}


def messages(record: dict[str, Any], table: dict[str, Any], arm: str) -> list[dict[str, str]]:
    system = "\n".join([
        "당신은 공공입찰 공고의 법령 위반을 독립적으로 판정한다.",
        "모든 메타데이터와 원문 문서를 읽고 v2와 v4를 각각 판정한다. 두 항목은 동시에 1일 수 있다.",
        f"- v2: {table['v2']['항목명']}",
        f"- v4: {table['v4']['항목명']}",
        "키워드만으로 단정하지 말고, 실제 입찰참가자격 제한인지와 적용되는 금액·계약법·실적 역할을 확인한다.",
        "1이면 근거문구는 원문 문서의 변경 없는 연속 부분문자열(500자 이하)이어야 한다. 법령은 판단기준일 뿐 근거문구가 아니다.",
        "0이면 근거문구는 null이다. JSON 객체 하나만 출력한다.",
    ])
    content = "[메타]\n" + json.dumps(record["meta"], ensure_ascii=False, sort_keys=True)
    if arm.startswith("law_"):
        content += "\n\n[적용 법령: 메타 계약법으로 선택된 완결 단위]\n" + law_context(str(record["meta"]["적용계약법"]))
    content += "\n\n[원문 문서]\n" + render_docs(record)
    return [{"role": "system", "content": system}, {"role": "user", "content": content}]


def request_config() -> dict[str, Any]:
    return {"model": "google/gemma-4-26b-a4b-it", "api_url": "https://openrouter.ai/api/v1/chat/completions", "api_key_env": "OPENROUTER_API_KEY", "temperature": 0.0, "seed": 20260905, "max_tokens": 500, "timeout_seconds": 120, "request_retries": 1}


def validate(payload: dict[str, Any], record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    source = "\n".join(doc["text"] for doc in record["docs"])
    result = {}
    for item in ITEMS:
        cell = payload.get(item)
        if not isinstance(cell, dict) or cell.get("위반여부") not in (0, 1):
            raise ValueError(f"invalid structured cell: {item}")
        evidence = cell.get("근거문구")
        evidence = evidence.strip() if isinstance(evidence, str) else ""
        violation = int(cell["위반여부"])
        if violation and (not evidence or evidence not in source):
            raise ValueError(f"invalid source evidence: {item}")
        result[item] = {"위반여부": violation, "근거문구": evidence if violation else ""}
    return result


def append_checkpoint(entry: dict[str, Any]) -> None:
    path = OUTPUT / "checkpoint.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        handle.flush(); os.fsync(handle.fileno()); fcntl.flock(handle, fcntl.LOCK_UN)


def run_one(record_id: str, arm: str) -> None:
    records, _, table = load_inputs()
    path = OUTPUT / "records" / f"{record_id}_{arm}.json"
    if path.exists():
        return
    record = records[record_id]
    response: Any = None
    try:
        response = common.completion(request_config(), messages(record, table, arm), schema())
        entry = {"id": record_id, "arm": arm, "success": True, "usage": response.usage, "raw_response": response.content, "judgment": validate(common.parse_json(response.content), record)}
    except Exception as exc:
        entry = {"id": record_id, "arm": arm, "success": False, "error": f"{type(exc).__name__}: {exc}", "usage": {} if response is None else response.usage, "raw_response": "" if response is None else response.content}
    path.parent.mkdir(parents=True, exist_ok=True)
    common.write_json(path, entry)
    append_checkpoint(entry)


def f1(tp: int, fp: int, fn: int) -> float:
    return 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0


def aggregate() -> None:
    records, labels, _ = load_inputs(); ids = cohort(records, labels)
    report: dict[str, Any] = {"experiment_id": "inc042_v2_v4_replicated_law_adjudication", "cohort_size": len(ids), "requested_calls": len(ids) * len(ARMS), "arms": {}}
    for arm in ARMS:
        entries = []
        for record_id in ids:
            path = OUTPUT / "records" / f"{record_id}_{arm}.json"
            if path.exists(): entries.append(json.loads(path.read_text(encoding="utf-8")))
        failures = [entry for entry in entries if not entry["success"]]
        arm_report: dict[str, Any] = {"successful_calls": len(entries) - len(failures), "failure_count": len(failures), "reported_cost_usd": sum(float(entry.get("usage", {}).get("cost", 0) or 0) for entry in entries)}
        if not failures and len(entries) == len(ids):
            per_item = []
            for item in ITEMS:
                tp = fp = fn = positives = valid = 0
                for entry in entries:
                    record_id = entry["id"]; pred = entry["judgment"][item]["위반여부"]; gold = int(labels[record_id][item])
                    tp += gold and pred; fp += not gold and pred; fn += gold and not pred
                    if pred:
                        positives += 1
                        valid += bool(entry["judgment"][item]["근거문구"] in "\n".join(doc["text"] for doc in records[record_id]["docs"]))
                per_item.append({"item": item, "tp": tp, "fp": fp, "fn": fn, "f1": f1(tp, fp, fn), "evidence_validity": valid / positives if positives else None})
            arm_report["target_macro_f1"] = sum(row["f1"] for row in per_item) / len(per_item)
            arm_report["per_item"] = per_item
        report["arms"][arm] = arm_report
    deltas = {}
    for repeat in ("r1", "r2"):
        control, law = report["arms"][f"control_{repeat}"], report["arms"][f"law_{repeat}"]
        if "target_macro_f1" in control and "target_macro_f1" in law:
            deltas[repeat] = law["target_macro_f1"] - control["target_macro_f1"]
    report["law_minus_control_deltas"] = deltas
    report["promotion_gate_passed"] = len(deltas) == 2 and all(delta >= 0 for delta in deltas.values())
    common.write_json(OUTPUT / "metrics.json", report)
    common.write_jsonl(OUTPUT / "responses.jsonl", [json.loads(path.read_text(encoding="utf-8")) for arm in ARMS for record_id in ids if (path := OUTPUT / "records" / f"{record_id}_{arm}.json").exists()])
    print(json.dumps(report, ensure_ascii=False, indent=2))


def preflight() -> None:
    records, labels, table = load_inputs(); ids = cohort(records, labels); manifest = []
    for record_id in ids:
        record = records[record_id]
        for arm in ARMS:
            request = messages(record, table, arm)
            manifest.append({"id": record_id, "arm": arm, "prompt_sha256": common.sha256_text(json.dumps(request, ensure_ascii=False, sort_keys=True)), "message_characters": sum(len(message["content"]) for message in request), "contract_law": record["meta"]["적용계약법"]})
    common.write_json(OUTPUT / "config.json", {"items": ITEMS, "arms": ARMS, "model": request_config(), "max_calls": len(manifest), "max_cost_usd": 0.55, "cohort_definition": "all v2/v4 positives plus all dual-negative performance-amount hard negatives"})
    common.write_jsonl(OUTPUT / "cohort.jsonl", manifest)
    print(json.dumps({"status": "preflight_ok", "notice_count": len(ids), "calls": len(manifest), "max_message_characters": max(row["message_characters"] for row in manifest)}, ensure_ascii=False, indent=2))


def run_all(workers: int) -> None:
    records, labels, _ = load_inputs(); jobs = [(record_id, arm) for record_id in cohort(records, labels) for arm in ARMS]
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


if __name__ == "__main__":
    main()
