#!/usr/bin/env python3
"""Label-blind transport audit for per-item e-prime extraction (v10-v18).

This is intentionally an eight-notice gate, not a score-selection experiment.
Stage A sees the full notice and writes a compact, source-grounded fact record
for every legally compositional product item.  Stage B sees only that record,
metadata, and the corresponding decision cards.  The run may advance only if
all Stage-A records are complete and their quoted anchors resolve to source.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import gzip
import hashlib
import json
import os
import sys
import time
import fcntl
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "incubator/src"))
from evidence_resolver import resolve_quote

RAW = ROOT / "data/raw/open"
CARDS = ROOT / "incubator/reference/dev_history/decision_cards_v6.json"
OUT = ROOT / "incubator/runs/inc117_item_eprime_transport_pilot"
ITEMS = [f"v{i}" for i in range(10, 19)]


def jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def completed(path: Path) -> dict[str, dict[str, Any]]:
    return {row["id"]: row for row in jsonl(path) if row.get("success")}


def schema_eprime() -> dict[str, Any]:
    unit = {
        "type": "object", "additionalProperties": False,
        "required": ["eprime", "quote"],
        "properties": {
            "eprime": {"type": "string", "maxLength": 900},
            "quote": {"type": "string", "maxLength": 500},
        },
    }
    return {"type": "object", "additionalProperties": False, "required": ITEMS,
            "properties": {item: unit for item in ITEMS}}


def schema_labels() -> dict[str, Any]:
    return {"type": "object", "additionalProperties": False, "required": ITEMS,
            "properties": {item: {"type": "integer", "enum": [0, 1]} for item in ITEMS}}


def cards_text(cards: dict[str, Any]) -> str:
    return "\n\n".join(
        f"[{item} | {cards['cards'][item]['item_name']}]\n{cards['cards'][item]['prompt_text']}"
        for item in ITEMS
    )


def document_text(record: dict[str, Any]) -> str:
    return "\n\n".join(f"[{doc['type']}]\n{doc['text']}" for doc in record["docs"])


def extract_messages(record: dict[str, Any], cards: dict[str, Any]) -> list[dict[str, str]]:
    system = """당신은 한국 공공입찰 공고의 사실 추출자다. 위반 여부를 판정하지 않는다.
v10~v18 각각에 대해, 그 항목의 적용성·금액/제품 구간·실제 참가자격 제한·명시적 예외를
후속 검토자가 판정할 수 있도록 eprime에 짧게 기록한다. eprime은 원문에서 확인되는 사실만
쓴다. quote에는 eprime의 핵심을 뒷받침하는 변경 없는 원문 연속 substring 하나를 넣는다.
해당 항목에 쓸 사실이 없으면 eprime과 quote를 빈 문자열로 둔다. 제품코드/메타는 원문이
아니므로 quote로 쓰지 않는다. JSON만 출력한다."""
    user = "[항목별 판정카드]\n" + cards_text(cards)
    user += "\n\n[나라장터 메타]\n" + json.dumps(record["meta"], ensure_ascii=False, sort_keys=True)
    user += "\n\n[공고 원문 전체]\n" + document_text(record)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def judge_messages(record: dict[str, Any], cards: dict[str, Any], eprime: dict[str, Any]) -> list[dict[str, str]]:
    system = """당신은 한국 공공입찰 법령 위반을 판정하는 독립 검토자다. 아래 eprime은
원문 전체를 읽은 사실 추출 단계의 결과다. 각 항목은 독립적인 법적 요건이며 키워드만으로
위반을 단정하지 말고 적용성, 금액·제품 구간, 실제 참가자격 제한, 예외를 함께 판단한다.
부재탐지는 적용대상임이 확인된 뒤 필요한 조건이 없을 때만 1이다. eprime에 필요한 사실이
없거나 적용성이 불명확하면 추측해 1로 만들지 않는다. JSON만 출력한다."""
    user = "[항목별 판정카드]\n" + cards_text(cards)
    user += "\n\n[나라장터 메타]\n" + json.dumps(record["meta"], ensure_ascii=False, sort_keys=True)
    user += "\n\n[원문 기반 eprime]\n" + json.dumps(eprime, ensure_ascii=False, sort_keys=True)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def output_text(body: dict[str, Any]) -> str:
    if isinstance(body.get("output_text"), str):
        return body["output_text"]
    return "".join(part.get("text", "") for item in body.get("output", []) if item.get("type") == "message"
                   for part in item.get("content", []) if part.get("type") == "output_text")


def call(key: str, messages: list[dict[str, str]], cap: int, schema: dict[str, Any], name: str) -> dict[str, Any]:
    payload = {"model": "gpt-5.6-luna", "input": messages, "max_output_tokens": cap, "store": False,
               "reasoning": {"effort": "high"},
               "text": {"format": {"type": "json_schema", "name": name, "strict": True, "schema": schema}}}
    errors: list[str] = []
    for attempt in range(2):
        try:
            response = requests.post("https://api.openai.com/v1/responses", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json=payload, timeout=300)
            body = response.json()
            text = output_text(body)
            if response.ok and text:
                return {"success": True, "value": json.loads(text), "usage": body.get("usage", {}), "raw_response": text}
            errors.append(f"{response.status_code}:{body.get('status')}:{body.get('incomplete_details')}")
        except Exception as exc:
            errors.append(f"{type(exc).__name__}:{exc}")
        time.sleep(2 ** attempt)
    return {"success": False, "error": " | ".join(errors)}


def candidate_ids(records: dict[str, dict[str, Any]], count: int) -> list[str]:
    # Fixed label-blind rank.  This is a transport QA sample, not a tuned cohort.
    return sorted(records, key=lambda value: hashlib.sha256(f"inc117-transport:{value}".encode()).hexdigest())[:count]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("extract", "judge", "audit"), default="extract")
    parser.add_argument("--count", type=int, default=8)
    args = parser.parse_args()
    cards = json.loads(CARDS.read_text(encoding="utf-8"))
    with gzip.open(RAW / "dev.jsonl.gz", "rt", encoding="utf-8") as handle:
        records = {row["id"]: row for row in (json.loads(line) for line in handle)}
    ids = candidate_ids(records, args.count)
    OUT.mkdir(parents=True, exist_ok=True)
    # A transport audit is expensive enough that a second local launcher must
    # fail before it can submit any duplicate request.  The handle stays open
    # for this process lifetime and is released automatically on exit.
    lock_handle = (OUT / ".active.lock").open("w", encoding="utf-8")
    try:
        fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise SystemExit("another INC-117 process is active; refusing duplicate API calls") from exc
    lock_handle.write(str(os.getpid()))
    lock_handle.flush()
    (OUT / "manifest.json").write_text(json.dumps({"ids": ids, "selection": "sha256 inc117-transport:id, label-blind", "purpose": "transport audit only"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    load_dotenv(ROOT / ".env")
    key = os.environ["OPENAI_API_KEY"]
    extraction_path = OUT / "extract.jsonl"
    if args.stage == "extract":
        old = completed(extraction_path)
        pending = [notice_id for notice_id in ids if notice_id not in old]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(call, key, extract_messages(records[notice_id], cards), 8192, schema_eprime(), "inc117_eprime"): notice_id for notice_id in pending}
            for number, future in enumerate(concurrent.futures.as_completed(futures), 1):
                notice_id = futures[future]
                row = future.result()
                if row.get("success"):
                    row["eprime"] = row.pop("value")
                row.update({"id": notice_id, "stage": "extract"})
                with extraction_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                print(f"extract {number}/{len(futures)} {notice_id} {row['success']}", flush=True)
    elif args.stage == "judge":
        extractions = completed(extraction_path)
        if set(ids) - set(extractions):
            raise SystemExit("all extraction rows must succeed before adjudication")
        path = OUT / "judge.jsonl"
        old = completed(path)
        pending = [notice_id for notice_id in ids if notice_id not in old]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(call, key, judge_messages(records[notice_id], cards, extractions[notice_id]["eprime"]), 8192, schema_labels(), "inc117_labels"): notice_id for notice_id in pending}
            for number, future in enumerate(concurrent.futures.as_completed(futures), 1):
                notice_id = futures[future]
                row = future.result()
                if row.get("success"):
                    row["labels"] = row.pop("value")
                row.update({"id": notice_id, "stage": "judge"})
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                print(f"judge {number}/{len(futures)} {notice_id} {row['success']}", flush=True)
    else:
        extractions = completed(extraction_path)
        audit_rows = []
        for notice_id in ids:
            row = extractions.get(notice_id)
            if not row:
                audit_rows.append({"id": notice_id, "success": False, "reason": "missing_extraction"})
                continue
            entries = []
            for item, value in row["eprime"].items():
                quote = value["quote"]
                resolved, status = resolve_quote(quote, records[notice_id]["docs"])
                entries.append({"item": item, "has_eprime": bool(value["eprime"]), "quote_status": status, "resolved_quote": resolved})
            audit_rows.append({"id": notice_id, "success": True, "entries": entries})
        stats = {"records": len(audit_rows), "successful_extractions": sum(row["success"] for row in audit_rows),
                 "nonempty_eprimes": sum(entry["has_eprime"] for row in audit_rows if row["success"] for entry in row["entries"]),
                 "nonempty_quotes": sum(bool(entry["resolved_quote"]) for row in audit_rows if row["success"] for entry in row["entries"]),
                 "unresolved_nonempty_quotes": sum(entry["quote_status"] in {"not_found", "ambiguous"} for row in audit_rows if row["success"] for entry in row["entries"])}
        (OUT / "audit.json").write_text(json.dumps({"stats": stats, "records": audit_rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
