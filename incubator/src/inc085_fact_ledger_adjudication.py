#!/usr/bin/env python3
"""INC-085: test source-validated factual ledgers before legal adjudication.

The cohort is frozen from observable dev-record structure before dev labels are
read.  Stage A produces no verdict.  Stage B sees only the validated ledger,
metadata, and concise legal cores; it never sees the original document.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import json
import os
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

import inc001_simple_joint24 as common
import inc081_teacher_full_context_calibration as calibration


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/raw/open"
CARDS = ROOT / "incubator/reference/dev_history/decision_cards_v6.json"
RUN_ID = "inc085_fact_ledger_adjudication_dev64"
SEED = "inc085-fact-ledger-dev64-v1"
COHORT_SIZE = 64
MODEL = "gpt-5.6-luna"
API_URL = "https://api.openai.com/v1/responses"
EXTRACT_OUTPUT_TOKENS = 3072
ADJUDICATE_OUTPUT_TOKENS = 1536


def jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def stable_rank(record_id: str) -> str:
    return hashlib.sha256(f"{SEED}:{record_id}".encode()).hexdigest()


def document_signature(record: dict[str, Any]) -> str:
    counts = Counter(document["type"] for document in record["docs"])
    return "+".join(f"{kind}x{counts[kind]}" for kind in sorted(counts))


def freeze_cohort(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Round-robin across common observable structure, never looking at labels."""
    ordered_lengths = sorted((sum(len(doc["text"]) for doc in record["docs"]), record["id"]) for record in records)
    decile = {record_id: min(9, rank * 10 // len(records)) for rank, (_, record_id) in enumerate(ordered_lengths)}
    groups: dict[tuple[str, str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        meta = record["meta"]
        key = (str(meta.get("업무구분")), str(meta.get("계약방법")), document_signature(record), decile[record["id"]])
        groups[key].append(record)
    common_groups = sorted(groups.items(), key=lambda pair: (-len(pair[1]), pair[0]))[:COHORT_SIZE]
    selected = []
    for key, rows in common_groups:
        record = min(rows, key=lambda candidate: stable_rank(candidate["id"]))
        selected.append({
            "id": record["id"], "stratum": " | ".join(map(str, key)),
            "source_characters": sum(len(doc["text"]) for doc in record["docs"]),
            "input_sha256": common.sha256_text(json.dumps(record, ensure_ascii=False, sort_keys=True)),
        })
    return selected


def ledger_schema() -> dict[str, Any]:
    entry = {
        "type": "object", "additionalProperties": False, "required": ["fact", "quote"],
        "properties": {
            "fact": {"type": "string", "maxLength": 280},
            "quote": {"type": "string", "maxLength": 500},
        },
    }
    return {"type": "object", "additionalProperties": False, "required": list(common.ITEMS), "properties": {item: entry for item in common.ITEMS}}


def label_schema() -> dict[str, Any]:
    return {"type": "object", "additionalProperties": False, "required": list(common.ITEMS), "properties": {item: {"type": "integer", "enum": [0, 1]} for item in common.ITEMS}}


def legal_core(cards: dict[str, Any]) -> str:
    return "\n\n".join(f"[{item} | {card['item_name']}]\n{card['prompt_text']}" for item, card in cards["cards"].items())


def extract_messages(record: dict[str, Any], cards: dict[str, Any]) -> list[dict[str, str]]:
    system = """당신은 공공입찰 공고에서 법률 판단에 필요한 사실만 추출하는 기록관이다.
아래 24개 법령 판단 핵심 각각에 대해 원문에서 관찰되는 관련 사실을 짧게 요약한다. 이 단계에서는
위반 여부를 판단하거나 추론하지 않는다. 각 fact가 비어있지 않으면 quote에는 그 fact를 뒷받침하는
공고 원문의 변경 없는 연속 부분문자열을 넣어야 한다. quote가 500자를 넘거나 원문 근거가 없으면
fact와 quote를 모두 빈 문자열로 둔다. 적용 전제, 대상, 수치, 제한, 예외, 필요한 문구의 존재/부재를
혼동하지 말고, 관찰 가능한 내용만 기록한다. JSON 하나만 출력한다."""
    user = "\n\n".join([
        "[항목별 법령 판단 핵심]\n" + legal_core(cards),
        "[나라장터 메타]\n" + json.dumps(record["meta"], ensure_ascii=False, sort_keys=True),
        "[공고 원문 전체]\n" + calibration.render_documents(record),
    ])
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def adjudicate_messages(record: dict[str, Any], cards: dict[str, Any], ledger: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    system = """당신은 한국 공공입찰 법령 위반을 판단하는 독립 법률 검토자다.
제공된 항목별 법령 판단 핵심, 나라장터 메타, 그리고 원문 검증을 통과한 사실 ledger만 사용한다.
각 항목은 별개의 법적 요건이다. ledger가 빈 것은 무위반 사실이 아니라 이 절차에서 확인하지 못한
것이므로 위반을 단정하지 않는다. 키워드만으로 위반을 단정하지 말고 적용 법령, 계약방식, 대상,
수치, 예외, 실제 제한 또는 문서부재 요건을 함께 판단한다. 최종 24개 0/1 JSON만 출력한다."""
    user = "\n\n".join([
        "[항목별 법령 판단 핵심]\n" + legal_core(cards),
        "[나라장터 메타]\n" + json.dumps(record["meta"], ensure_ascii=False, sort_keys=True),
        "[원문 검증 사실 ledger]\n" + json.dumps(ledger, ensure_ascii=False, sort_keys=True),
    ])
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def call_openai(api_key: str, messages: list[dict[str, str]], output_tokens: int, schema: dict[str, Any], schema_name: str) -> dict[str, Any]:
    payload = {"model": MODEL, "input": messages, "max_output_tokens": output_tokens, "store": False,
               "text": {"format": {"type": "json_schema", "name": schema_name, "strict": True, "schema": schema}}}
    error = "unknown"
    for attempt in range(4):
        started = time.monotonic()
        try:
            response = requests.post(API_URL, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json=payload, timeout=240)
            if response.ok:
                body = response.json()
                content = body.get("output_text")
                if not isinstance(content, str) or not content:
                    content = "".join(
                        block.get("text", "")
                        for message in body.get("output", []) if message.get("type") == "message"
                        for block in message.get("content", []) if block.get("type") == "output_text"
                    )
                if isinstance(content, str) and content:
                    value = json.loads(content)
                    return {"success": True, "value": value, "raw_response": content, "usage": body.get("usage", {}), "latency_seconds": round(time.monotonic() - started, 3)}
                # A 2xx Responses object can still be incomplete (for example
                # output-token exhaustion). Preserve its status and reason so
                # the experiment is diagnosable rather than silently counted
                # as a generic parser failure.
                error = "incomplete response: " + json.dumps({
                    "status": body.get("status"), "incomplete_details": body.get("incomplete_details"),
                    "error": body.get("error"), "output": body.get("output"),
                }, ensure_ascii=False)[:1200]
                return {"success": False, "error": error, "raw_response": json.dumps(body, ensure_ascii=False), "usage": body.get("usage", {}), "latency_seconds": round(time.monotonic() - started, 3)}
            error = f"HTTP {response.status_code}: {response.text[:400]}"
            if response.status_code not in {408, 409, 429, 500, 502, 503, 504}:
                break
        except (requests.RequestException, KeyError, TypeError, json.JSONDecodeError) as exc:
            error = f"{type(exc).__name__}: {exc}"
        time.sleep(2 ** attempt)
    return {"success": False, "error": error, "raw_response": "", "usage": {}, "latency_seconds": 0.0}


def validate_ledger(value: Any, record: dict[str, Any]) -> tuple[dict[str, dict[str, str]], list[str]]:
    if not isinstance(value, dict) or set(value) != set(common.ITEMS):
        raise ValueError("ledger does not contain exactly v1-v24")
    source = "\n".join(document["text"] for document in record["docs"])
    cleaned: dict[str, dict[str, str]] = {}
    invalid: list[str] = []
    for item in common.ITEMS:
        entry = value[item]
        if not isinstance(entry, dict) or set(entry) != {"fact", "quote"}:
            raise ValueError(f"invalid ledger shape for {item}")
        fact, quote = entry["fact"].strip(), entry["quote"].strip()
        if not fact and not quote:
            cleaned[item] = {"fact": "", "quote": ""}
        elif fact and quote and len(fact) <= 280 and len(quote) <= 500 and quote in source:
            cleaned[item] = {"fact": fact, "quote": quote}
        else:
            cleaned[item] = {"fact": "", "quote": ""}
            invalid.append(item)
    return cleaned, invalid


def validate_labels(value: Any) -> dict[str, int]:
    if not isinstance(value, dict) or set(value) != set(common.ITEMS) or any(value[item] not in (0, 1) for item in common.ITEMS):
        raise ValueError("invalid 24-label output")
    return {item: int(value[item]) for item in common.ITEMS}


def run_stage(stage: str, records: dict[str, dict[str, Any]], selected: list[dict[str, Any]], cards: dict[str, Any], api_key: str, output: Path, workers: int) -> None:
    checkpoint = output / f"{stage}.jsonl"
    done = {row["id"]: row for row in jsonl(checkpoint)} if checkpoint.exists() else {}
    pending = [row for row in selected if not done.get(row["id"], {}).get("success")]
    # Checkpoints are append-only: an early failed transport attempt and a
    # later successful retry may coexist.  Select the last *successful* ledger
    # for each ID rather than assuming every historical row has a ledger.
    ledgers: dict[str, dict[str, dict[str, str]]] = {}
    if stage == "adjudicate":
        for row in jsonl(output / "extract.jsonl"):
            if row.get("success") and "ledger" in row:
                ledgers[row["id"]] = row["ledger"]
        missing = [manifest["id"] for manifest in selected if manifest["id"] not in ledgers]
        if missing:
            raise RuntimeError(f"cannot adjudicate without successful ledgers: {missing}")

    def one(manifest: dict[str, Any]) -> dict[str, Any]:
        record = records[manifest["id"]]
        if stage == "extract":
            response = call_openai(api_key, extract_messages(record, cards), EXTRACT_OUTPUT_TOKENS, ledger_schema(), "inc085_ledger")
            if response["success"]:
                try:
                    ledger, invalid = validate_ledger(response.pop("value"), record)
                    response.update({"ledger": ledger, "invalid_quote_items": invalid})
                except ValueError as exc:
                    response = {**response, "success": False, "error": f"validation: {exc}"}
        else:
            response = call_openai(api_key, adjudicate_messages(record, cards, ledgers[manifest["id"]]), ADJUDICATE_OUTPUT_TOKENS, label_schema(), "inc085_labels")
            if response["success"]:
                try:
                    response["labels"] = validate_labels(response.pop("value"))
                except ValueError as exc:
                    response = {**response, "success": False, "error": f"validation: {exc}"}
        return {"id": manifest["id"], "stage": stage, **response}

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(one, manifest) for manifest in pending]
        for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            row = future.result()
            common.append_jsonl(checkpoint, row)
            print(f"[{index}/{len(pending)}] {stage} {row['id']} success={row['success']}", flush=True)


def score(predictions: dict[str, dict[str, int]], gold: dict[str, dict[str, str]]) -> tuple[float, list[dict[str, Any]]]:
    rows = []
    for item in common.ITEMS:
        tp = fp = fn = 0
        for record_id, prediction in predictions.items():
            truth = int(gold[record_id][item]); value = prediction[item]
            tp += int(truth == value == 1); fp += int(value == 1 and truth == 0); fn += int(value == 0 and truth == 1)
        precision = tp / (tp + fp) if tp + fp else 0.0; recall = tp / (tp + fn) if tp + fn else 0.0
        rows.append({"item": item, "tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0})
    return sum(row["f1"] for row in rows) / len(rows), rows


def aggregate(output: Path, selected: list[dict[str, Any]], gold: dict[str, dict[str, str]]) -> None:
    extracts = {row["id"]: row for row in jsonl(output / "extract.jsonl")}
    adjudications = {row["id"]: row for row in jsonl(output / "adjudicate.jsonl")}
    ids = [row["id"] for row in selected]
    complete = [record_id for record_id in ids if extracts.get(record_id, {}).get("success") and adjudications.get(record_id, {}).get("success")]
    predictions = {record_id: adjudications[record_id]["labels"] for record_id in complete}
    macro, per_item = score(predictions, gold) if complete else (0.0, [])
    direct = {row["id"]: row["labels"] for row in jsonl(ROOT / "incubator/runs/inc084_openai_luna_full_dev_card/responses.jsonl")}
    direct_macro, direct_items = score({record_id: direct[record_id] for record_id in complete}, gold) if complete else (0.0, [])
    nonempty = sum(bool(extracts[record_id]["ledger"][item]["fact"]) for record_id in complete for item in common.ITEMS)
    invalid = sum(len(extracts[record_id].get("invalid_quote_items", [])) for record_id in complete)
    report = {"experiment_id": RUN_ID, "cohort_size": len(ids), "complete_pairs": len(complete), "extract_success": sum(row.get("success", False) for row in extracts.values()), "adjudicate_success": sum(row.get("success", False) for row in adjudications.values()), "validated_nonempty_ledger_rate": nonempty / (len(complete) * len(common.ITEMS)) if complete else 0.0, "invalid_quote_entries_discarded": invalid, "ledger_adjudication_macro_f1": macro, "direct_luna_same_cohort_macro_f1": direct_macro, "architectural_delta": macro - direct_macro, "note": "The direct comparison is diagnostic only. No post-hoc merge is selected.", "per_item": per_item, "direct_per_item": direct_items}
    common.write_json(output / "metrics.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "run", "aggregate"), default="preflight")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.workers < 1:
        raise ValueError("workers must be positive")
    records_list = common.read_jsonl_gz(DATA / "dev.jsonl.gz")
    records = {record["id"]: record for record in records_list}
    selected = freeze_cohort(records_list)
    cards = json.loads(CARDS.read_text(encoding="utf-8"))
    output = ROOT / "incubator/runs" / RUN_ID
    output.mkdir(parents=True, exist_ok=True)
    common.write_jsonl(output / "manifest.jsonl", selected)
    preflight = {"experiment_id": RUN_ID, "selection": {"size": COHORT_SIZE, "seed": SEED, "algorithm": "one deterministically ranked notice from each of 64 most common metadata/document-signature/length-decile strata", "labels_read_for_selection": False}, "stages": {"extract": {"output_tokens": EXTRACT_OUTPUT_TOKENS, "contains_original_documents": True, "emits_verdict": False}, "adjudicate": {"output_tokens": ADJUDICATE_OUTPUT_TOKENS, "contains_original_documents": False, "uses_validated_ledger_only": True}}, "model": MODEL, "source_sha256": common.sha256_file(DATA / "dev.jsonl.gz"), "cards_sha256": common.sha256_file(CARDS)}
    common.write_json(output / "preflight.json", preflight)
    if args.mode == "preflight":
        print(json.dumps({"status": "preflight_ok", **preflight}, ensure_ascii=False, indent=2)); return
    if args.mode == "run":
        load_dotenv(ROOT / ".env")
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required")
        run_stage("extract", records, selected, cards, api_key, output, args.workers)
        run_stage("adjudicate", records, selected, cards, api_key, output, args.workers)
    else:
        gold = {row["id"]: row for row in csv.DictReader((DATA / "dev_labels.csv").open(encoding="utf-8"))}
        aggregate(output, selected, gold)


if __name__ == "__main__":
    main()
