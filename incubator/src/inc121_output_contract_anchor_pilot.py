#!/usr/bin/env python3
"""Paired EXP-120-style output-contract pilot with deterministic source anchors."""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import fcntl
import gzip
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "incubator/configs/inc121_output_contract_anchor_pilot.json"
OUT = ROOT / "incubator/runs/inc121_output_contract_anchor_pilot"
RAW = ROOT / "data/raw/open"
CARDS = ROOT / "incubator/reference/dev_history/decision_cards_v6.json"
ITEMS = tuple(f"v{index}" for index in range(1, 25))
ABSENCE = frozenset({"v10", "v11", "v16", "v18", "v20"})
ORDER = {name: index for index, name in enumerate(("공고문", "규격서", "과업지시서", "제안요청서", "예외공표서"))}


def sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: Any) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def load_inputs() -> tuple[dict[str, Any], dict[str, dict[str, str]], dict[str, Any], dict[str, Any]]:
    with gzip.open(RAW / "dev.jsonl.gz", "rt", encoding="utf-8") as handle:
        records = {row["id"]: row for row in (json.loads(line) for line in handle if line.strip())}
    with (RAW / "dev_labels.csv").open(encoding="utf-8", newline="") as handle:
        labels = {row["id"]: row for row in csv.DictReader(handle)}
    item_table = json.loads((RAW / "data/항목표.json").read_text(encoding="utf-8"))["항목"]
    cards = json.loads(CARDS.read_text(encoding="utf-8"))["cards"]
    if set(records) != set(labels) or set(item_table) != set(ITEMS) or set(cards) != set(ITEMS):
        raise RuntimeError("dev/item/card source mismatch")
    return records, labels, item_table, cards


def stable_rank(namespace: str, record_id: str) -> str:
    return sha256_text(f"{namespace}:{record_id}")


def source_length(record: dict[str, Any]) -> int:
    return sum(len(document["text"]) for document in record["docs"])


def exploration_ids(records: dict[str, Any], labels: dict[str, dict[str, str]], size: int) -> list[str]:
    """Fixed coverage plus non-label structural strata; no prompt sees labels."""
    chosen: set[str] = set()
    for item in ITEMS:
        positives = [record_id for record_id in records if int(labels[record_id][item]) == 1]
        if not positives:
            raise RuntimeError(f"no dev positive for {item}")
        chosen.add(min(positives, key=lambda record_id: stable_rank(f"inc121-positive-{item}", record_id)))
    lengths = sorted(source_length(record) for record in records.values())
    lower, upper = lengths[len(lengths) // 3], lengths[(2 * len(lengths)) // 3]
    def length_bin(record: dict[str, Any]) -> str:
        value = source_length(record)
        return "short" if value <= lower else "medium" if value <= upper else "long"
    strata: dict[tuple[str, str, str], list[str]] = {}
    for record_id, record in records.items():
        doc_bucket = "3+" if len(record["docs"]) >= 3 else str(len(record["docs"]))
        complete = "complete" if record.get("input_completeness", {}).get("완전관측", True) else "incomplete"
        strata.setdefault((doc_bucket, complete, length_bin(record)), []).append(record_id)
    for key in sorted(strata):
        candidates = [record_id for record_id in strata[key] if record_id not in chosen]
        if candidates and len(chosen) < size:
            chosen.add(min(candidates, key=lambda record_id: stable_rank(f"inc121-stratum-{key}", record_id)))
    for record_id in sorted(records, key=lambda value: stable_rank("inc121-fill", value)):
        if len(chosen) >= size:
            break
        chosen.add(record_id)
    if len(chosen) != size:
        raise RuntimeError(f"cohort size mismatch: {len(chosen)}")
    return sorted(chosen)


def admitted_spans(record: dict[str, Any], context_chars: int) -> list[dict[str, str]]:
    """Mirror EXP-120 ordered prefix admission, then split only into source substrings."""
    remaining = context_chars
    spans: list[dict[str, str]] = []
    for document in sorted(record["docs"], key=lambda value: (ORDER.get(value["type"], len(ORDER)), value["doc_id"])):
        header = f"[{document['type']}:{document['doc_id']}]\n"
        if remaining <= len(header):
            continue
        available = remaining - len(header)
        text = document["text"][:available]
        remaining -= len(header) + len(text)
        offset = 0
        for line in text.splitlines(keepends=True) or [text]:
            if not line:
                continue
            for start in range(0, len(line), 500):
                value = line[start : start + 500]
                if value:
                    spans.append({"doc_id": document["doc_id"], "text": value})
            offset += len(line)
        if len(document["text"]) > available:
            break
    if not spans:
        raise RuntimeError(f"no admitted source spans: {record['id']}")
    return spans


def numbered_context(record: dict[str, Any], spans: list[dict[str, str]]) -> str:
    grouped: dict[str, list[tuple[int, str]]] = {}
    types = {document["doc_id"]: document["type"] for document in record["docs"]}
    for index, span in enumerate(spans):
        grouped.setdefault(span["doc_id"], []).append((index, span["text"]))
    blocks = []
    for document in sorted(record["docs"], key=lambda value: (ORDER.get(value["type"], len(ORDER)), value["doc_id"])):
        entries = grouped.get(document["doc_id"], [])
        if entries:
            blocks.append(f"[{types[document['doc_id']]}:{document['doc_id']}]\n" + "".join(f"<S{index}>{text}" for index, text in entries))
    return "\n".join(blocks)


def system_prompt(item_table: dict[str, Any], cards: dict[str, Any], arm: str) -> str:
    item_lines = "\n".join(f"- {item}: {item_table[item]['항목명']}" + (" [부재탐지]" if item in ABSENCE else "") for item in ITEMS)
    card_text = "\n\n".join(f"[{item} | {cards[item]['item_name']}]\n{cards[item]['prompt_text']}" for item in ITEMS)
    shared = f"""당신은 공공 입찰공고의 법령 위반 여부를 점검한다. 제공된 원문과 나라장터 메타를 함께 읽고 각 항목을 독립적으로 판정한다.

판정 원칙:
1. 키워드 하나, 숫자 하나, 일반 관행만으로 위반을 단정하지 않는다. 적용성, 실제 제한·요구·불일치, 예외를 함께 확인한다.
2. 카드의 1 조건을 모두 만족할 때만 1이다. 0 조건이 있거나 확인할 수 없으면 0이다.
3. 부재탐지 항목은 적용대상이 확인된 뒤 필요한 조건이 없을 때만 1이다.
4. `<S번호>`는 제공된 원문 그대로의 연속 source span이다. model이 문구를 새로 쓰거나 수정해서는 안 된다.

판정 항목:
{item_lines}

[항목별 상세 판정 카드]
{card_text}
"""
    if arm == "control_ve":
        contract = """JSON 객체 하나만 출력한다. v1~v24 각각은 `위반여부`(0 또는 1)와 `근거문구`(문자열 또는 null)를 가진다. non-absence 항목이 1이면 `<S번호>` 안에서 변경 없는 문자열을 근거문구로 복사하고, 0이면 null이다. 부재탐지는 근거문구가 null이다."""
    elif arm == "a1_v_only":
        contract = """JSON 객체 하나만 출력한다. v1~v24 각각의 값은 0 또는 1 정수다. 근거문구·설명·추가 키를 출력하지 않는다."""
    elif arm == "a2_anchor":
        contract = """JSON 객체 하나만 출력한다. v1~v24 각각은 `위반여부`(0 또는 1)와 `anchor_id`(정수)를 가진다. non-absence 항목은 위반여부가 1일 때 그 판단을 직접 뒷받침하는 `<S번호>`의 번호를 anchor_id로 출력하고, 0일 때 -1을 출력한다. 부재탐지 항목은 언제나 anchor_id -1이다. 유효한 source anchor가 없으면 위반여부를 0으로 둔다."""
    else:
        raise ValueError(f"unknown arm {arm}")
    return shared + "\n" + contract


def schema(arm: str, span_count: int) -> dict[str, Any]:
    if arm == "a1_v_only":
        properties = {item: {"type": "integer", "enum": [0, 1]} for item in ITEMS}
    else:
        properties = {}
        for item in ITEMS:
            detail: dict[str, Any] = {
                "type": "object", "additionalProperties": False,
                "required": ["위반여부", "근거문구"] if arm == "control_ve" else ["위반여부", "anchor_id"],
                "properties": {"위반여부": {"type": "integer", "enum": [0, 1]}},
            }
            if arm == "control_ve":
                detail["properties"]["근거문구"] = {"type": ["string", "null"], "maxLength": 500}
            else:
                detail["properties"]["anchor_id"] = {"type": "integer", "enum": [-1, *range(span_count)]}
            properties[item] = detail
    return {"type": "object", "additionalProperties": False, "required": list(ITEMS), "properties": properties}


def messages(record: dict[str, Any], item_table: dict[str, Any], cards: dict[str, Any], arm: str, spans: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt(item_table, cards, arm)},
        {"role": "user", "content": "[나라장터 메타]\n" + json.dumps(record["meta"], ensure_ascii=False, sort_keys=True) + "\n\n[공고 원문]\n" + numbered_context(record, spans)},
    ]


def call(config: dict[str, Any], request_messages: list[dict[str, str]], response_schema: dict[str, Any]) -> dict[str, Any]:
    key = os.environ.get(config["api_key_env"], "")
    if not key:
        raise RuntimeError(f"missing {config['api_key_env']}")
    payload = {"model": config["model"], "messages": request_messages, "temperature": config["temperature"], "seed": config["seed"], "max_tokens": config["max_tokens"], "stream": False, "provider": {"require_parameters": True, "sort": "throughput"}, "response_format": {"type": "json_schema", "json_schema": {"name": "inc121_output_contract", "strict": True, "schema": response_schema}}}
    errors = []
    for attempt in range(config["request_retries"] + 1):
        started = time.monotonic()
        try:
            response = requests.post(config["api_url"], headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json=payload, timeout=config["timeout_seconds"])
            body = response.json()
            if response.ok:
                content = body["choices"][0]["message"]["content"]
                return {"success": True, "raw_response": content, "payload": json.loads(content), "usage": body.get("usage", {}), "model": body.get("model", config["model"]), "latency_seconds": round(time.monotonic() - started, 3)}
            errors.append(f"HTTP {response.status_code}: {str(body)[:300]}")
            if response.status_code not in {408, 409, 429, 500, 502, 503, 504}:
                break
        except (requests.RequestException, ValueError, KeyError, IndexError, json.JSONDecodeError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
        if attempt < config["request_retries"]:
            time.sleep(2 ** attempt)
    return {"success": False, "error": " | ".join(errors), "raw_response": "", "usage": {}, "model": config["model"], "latency_seconds": 0.0}


def judgment_from_payload(arm: str, payload: dict[str, Any], spans: list[dict[str, str]]) -> tuple[dict[str, int], dict[str, str], list[str]]:
    labels: dict[str, int] = {}
    evidence: dict[str, str] = {}
    errors: list[str] = []
    for item in ITEMS:
        cell = payload.get(item)
        if arm == "a1_v_only":
            if cell not in (0, 1):
                errors.append(f"{item}: invalid binary")
                continue
            labels[item] = int(cell); evidence[item] = ""
            continue
        if not isinstance(cell, dict) or cell.get("위반여부") not in (0, 1):
            errors.append(f"{item}: invalid object")
            continue
        labels[item] = int(cell["위반여부"])
        if arm == "control_ve":
            quote = cell.get("근거문구")
            source = "\n".join(span["text"] for span in spans)
            evidence[item] = quote if labels[item] and item not in ABSENCE and isinstance(quote, str) and quote in source and len(quote) <= 500 else ""
        else:
            anchor = cell.get("anchor_id")
            if item in ABSENCE:
                if anchor != -1:
                    errors.append(f"{item}: absence anchor must be -1")
                evidence[item] = ""
            elif labels[item] == 1:
                if not isinstance(anchor, int) or anchor < 0 or anchor >= len(spans):
                    errors.append(f"{item}: positive without valid anchor")
                    evidence[item] = ""
                else:
                    evidence[item] = spans[anchor]["text"]
            elif anchor != -1:
                errors.append(f"{item}: negative anchor must be -1")
                evidence[item] = ""
    return labels, evidence, errors


def metric(entries: list[dict[str, Any]], labels: dict[str, dict[str, str]], ids: list[str]) -> dict[str, Any]:
    per_item = []
    for item in ITEMS:
        tp = fp = fn = 0
        for record_id in ids:
            gold, predicted = int(labels[record_id][item]), int(entries[record_id]["labels"][item])
            tp += int(gold == predicted == 1); fp += int(gold == 0 and predicted == 1); fn += int(gold == 1 and predicted == 0)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        per_item.append({"item": item, "tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0})
    positive = sum(entry["labels"][item] for entry in entries.values() for item in ITEMS if item not in ABSENCE)
    valid = sum(bool(entry["evidence"][item]) for entry in entries.values() for item in ITEMS if item not in ABSENCE and entry["labels"][item])
    return {"macro_f1": sum(row["f1"] for row in per_item) / len(per_item), "recall_micro": sum(row["tp"] for row in per_item) / max(1, sum(row["tp"] + row["fn"] for row in per_item)), "per_item": per_item, "non_absence_evidence_validity": valid / positive if positive else None}


def prepared(records: dict[str, Any], labels: dict[str, dict[str, str]], item_table: dict[str, Any], cards: dict[str, Any], config: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    ids = exploration_ids(records, labels, int(config["cohort_size"]))
    rows = []
    for record_id in ids:
        spans = admitted_spans(records[record_id], int(config["context_chars"]))
        arm_messages = {arm: messages(records[record_id], item_table, cards, arm, spans) for arm in config["arms"]}
        rows.append({"id": record_id, "span_count": len(spans), "source_span_valid": all(span["text"] in next(document["text"] for document in records[record_id]["docs"] if document["doc_id"] == span["doc_id"]) and len(span["text"]) <= 500 for span in spans), "prompt_sha256": {arm: sha256_text(json.dumps(value, ensure_ascii=False, sort_keys=True)) for arm, value in arm_messages.items()}, "message_characters": {arm: sum(len(message["content"]) for message in value) for arm, value in arm_messages.items()}})
    return ids, rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("preflight", "mock", "run", "aggregate"))
    args = parser.parse_args()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    records, labels, item_table, cards = load_inputs()
    OUT.mkdir(parents=True, exist_ok=True)
    ids, manifest = prepared(records, labels, item_table, cards, config)
    preflight = {"experiment_id": config["experiment_id"], "config": config, "source_sha256": {"dev": sha256_bytes(RAW / "dev.jsonl.gz"), "labels": sha256_bytes(RAW / "dev_labels.csv"), "item_table": sha256_bytes(RAW / "data/항목표.json"), "cards": sha256_bytes(CARDS)}, "ids_sha256": sha256_text("\n".join(ids)), "request_count": len(ids) * len(config["arms"]), "source_span_valid": all(row["source_span_valid"] for row in manifest), "max_message_characters": {arm: max(row["message_characters"][arm] for row in manifest) for arm in config["arms"]}}
    write_json(OUT / "config.json", config); write_json(OUT / "preflight.json", preflight)
    (OUT / "cohort.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in manifest), encoding="utf-8")
    if not preflight["source_span_valid"] or preflight["request_count"] > config["max_requests"]:
        raise RuntimeError("preflight gate failed")
    if args.mode == "preflight":
        print(json.dumps({"status": "preflight_ok", **preflight}, ensure_ascii=False, indent=2)); return
    if args.mode == "mock":
        for record_id in ids:
            spans = admitted_spans(records[record_id], int(config["context_chars"]))
            for arm in config["arms"]:
                payload = {item: 0 for item in ITEMS} if arm == "a1_v_only" else {item: {"위반여부": 0, "근거문구": None} if arm == "control_ve" else {"위반여부": 0, "anchor_id": -1} for item in ITEMS}
                _, _, errors = judgment_from_payload(arm, payload, spans)
                if errors:
                    raise RuntimeError(f"mock validator failure {record_id}/{arm}: {errors}")
        print(json.dumps({"status": "mock_ok", "records": len(ids), "requests": preflight["request_count"]}, ensure_ascii=False)); return
    checkpoint = OUT / "checkpoint.jsonl"
    completed: dict[tuple[str, str], dict[str, Any]] = {}
    if checkpoint.exists():
        for line in checkpoint.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            completed[(row["id"], row["arm"])] = row
    if args.mode == "run":
        load_dotenv(ROOT / ".env")
        lock = (OUT / ".active.lock").open("w", encoding="utf-8")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SystemExit("INC-121 already has an active launcher") from exc
        lock.write(str(os.getpid())); lock.flush()
        pending = [(record_id, arm) for record_id in ids for arm in config["arms"] if (record_id, arm) not in completed]
        spent = sum(float(row.get("usage", {}).get("cost", 0) or 0) for row in completed.values())
        if spent >= config["max_cost_usd"]:
            raise RuntimeError("cost ceiling already reached")
        def worker(record_id: str, arm: str) -> dict[str, Any]:
            spans = admitted_spans(records[record_id], int(config["context_chars"]))
            response = call(config, messages(records[record_id], item_table, cards, arm, spans), schema(arm, len(spans)))
            row: dict[str, Any] = {"id": record_id, "arm": arm, **response}
            if response["success"]:
                result_labels, evidence, errors = judgment_from_payload(arm, response["payload"], spans)
                row.update({"labels": result_labels, "evidence": evidence, "semantic_errors": errors, "success": not errors})
                if errors:
                    row["error"] = "; ".join(errors)
                del row["payload"]
            return row
        with concurrent.futures.ThreadPoolExecutor(max_workers=int(config["max_workers"])) as executor:
            futures = {executor.submit(worker, record_id, arm): (record_id, arm) for record_id, arm in pending}
            for count, future in enumerate(concurrent.futures.as_completed(futures), 1):
                row = future.result(); spent += float(row.get("usage", {}).get("cost", 0) or 0); append_jsonl(checkpoint, row)
                print(f"completed={count}/{len(pending)} {row['id']}/{row['arm']} success={row['success']} cost=${spent:.6f}", flush=True)
                if spent >= config["max_cost_usd"]:
                    for pending_future in futures:
                        pending_future.cancel()
                    raise RuntimeError("reported cost ceiling reached")
        return
    report: dict[str, Any] = {"experiment_id": config["experiment_id"], "cohort_size": len(ids), "arms": {}}
    entries_by_arm: dict[str, dict[str, Any]] = {}
    for arm in config["arms"]:
        rows = [completed.get((record_id, arm)) for record_id in ids]
        failures = [row for row in rows if not row or not row.get("success")]
        report["arms"][arm] = {"success": len(rows) - len(failures), "failures": len(failures), "reported_cost_usd": sum(float((row or {}).get("usage", {}).get("cost", 0) or 0) for row in rows)}
        if not failures:
            entries = {row["id"]: row for row in rows if row}
            entries_by_arm[arm] = entries
            report["arms"][arm].update(metric(entries, labels, ids))
    control = report["arms"].get("control_ve", {})
    anchor = report["arms"].get("a2_anchor", {})
    if "macro_f1" in control and "macro_f1" in anchor:
        report["a2_minus_control"] = {"macro_f1": anchor["macro_f1"] - control["macro_f1"], "recall_micro": anchor["recall_micro"] - control["recall_micro"], "evidence_validity": anchor["non_absence_evidence_validity"]}
    write_json(OUT / "metrics.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
