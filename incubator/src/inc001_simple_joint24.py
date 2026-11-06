#!/usr/bin/env python3
"""Independent, deliberately simple 24-item Gemma pilot for INC-001.

This script neither imports nor changes the parent pipeline. It uses a fixed,
label-stratified dev cohort only for offline evaluation, saves every actual
message/response locally, and enforces request and reported-cost ceilings.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


ITEMS = tuple(f"v{index}" for index in range(1, 25))
ABSENCE_ITEMS = frozenset({"v10", "v11", "v16", "v18", "v20"})
DOCUMENT_ORDER = {name: index for index, name in enumerate(("공고문", "규격서", "과업지시서", "제안요청서", "예외공표서"))}
CSV_COLUMNS = ("id", *ITEMS, *(f"e{index}" for index in range(1, 25)))
FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


@dataclass(frozen=True)
class Completion:
    content: str
    model: str
    usage: dict[str, Any]
    latency_seconds: float
    finish_reason: str | None


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def read_jsonl_gz(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_historical_false_positives(path: Path, labels: dict[str, dict[str, str]]) -> dict[str, int]:
    if not path.exists():
        return {}
    result: dict[str, int] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            payload = json.loads(line)
            record_id = payload.get("id")
            judgment = payload.get("judgment", {})
            if record_id not in labels or not isinstance(judgment, dict):
                continue
            result[record_id] = sum(
                int(labels[record_id][item]) == 0
                and int(judgment.get(item, {}).get("위반여부", 0)) == 1
                for item in ITEMS
            )
    return result


def select_cohort(
    labels: list[dict[str, str]],
    historical_fp: dict[str, int],
    positive_seed_limit: int,
    hard_negative_limit: int,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Greedily cover item positives, then add historically hard all-negative notices."""
    remaining = list(labels)
    uncovered = set(ITEMS)
    selected: list[dict[str, str]] = []
    while uncovered and len(selected) < positive_seed_limit:
        candidate = max(
            remaining,
            key=lambda row: (
                sum(row[item] == "1" for item in uncovered),
                sum(row[item] == "1" for item in ITEMS),
                row["id"],
            ),
        )
        gain = {item for item in uncovered if candidate[item] == "1"}
        if not gain:
            break
        selected.append(candidate)
        remaining.remove(candidate)
        uncovered -= gain
    negative_rows = [row for row in remaining if all(row[item] == "0" for item in ITEMS)]
    negative_rows.sort(key=lambda row: (-historical_fp.get(row["id"], 0), row["id"]))
    selected.extend(negative_rows[:hard_negative_limit])
    selected.sort(key=lambda row: row["id"])
    metadata = {
        "selection": "greedy positive-label coverage then historically false-positive all-negative hard negatives",
        "positive_seed_limit": positive_seed_limit,
        "hard_negative_limit": hard_negative_limit,
        "selected_count": len(selected),
        "covered_items": sorted({item for row in selected for item in ITEMS if row[item] == "1"}),
        "uncovered_items": sorted(uncovered),
        "selected_id_sha256": sha256_text("\n".join(row["id"] for row in selected)),
    }
    return selected, metadata


def build_system_prompt(item_table: dict[str, dict[str, Any]]) -> str:
    lines = []
    for item in ITEMS:
        definition = item_table[item]
        absence = " [부재탐지]" if item in ABSENCE_ITEMS else ""
        note = definition.get("비고") or ""
        suffix = f" (참고: {note})" if note else ""
        lines.append(f"- {item}: {definition['항목명']}{absence}{suffix}")
    return "\n".join(
        [
            "당신은 공공 입찰공고의 법령 위반 여부를 점검한다.",
            "공고문, 제공된 첨부문서, 나라장터 입력 메타를 읽고 24개 항목을 각각 판정한다.",
            "판단이 어려우면 0으로 둔다. 키워드만으로 위반을 단정하지 말고 실제 제한·부재·불일치를 확인한다.",
            "1인 non-absence 항목의 근거문구는 제공 문서에 있는 변경 없는 연속 부분문자열이고 500자 이하여야 한다.",
            "0이면 근거문구는 null이다. 부재탐지 항목(v10,v11,v16,v18,v20)은 근거문구를 항상 null로 둔다.",
            "v24는 문서의 명시 내용과 메타의 대응 값이 실제로 다를 때만 1이다.",
            "판정 항목:",
            *lines,
            "JSON 객체 하나만 출력한다. v1~v24 각각은 {\"위반여부\": 0 또는 1, \"근거문구\": 문자열 또는 null}이다.",
        ]
    )


def render_documents(record: dict[str, Any], limit: int) -> tuple[str, dict[str, Any]]:
    """Keep ordered document prefixes within one transparent total character budget."""
    remaining = limit
    parts: list[str] = []
    included: list[dict[str, Any]] = []
    documents = sorted(record["docs"], key=lambda doc: (DOCUMENT_ORDER[doc["type"]], doc["doc_id"]))
    for document in documents:
        header = f"[{document['type']}:{document['doc_id']}]\n"
        if remaining <= len(header):
            break
        text = document["text"][: remaining - len(header)]
        parts.append(header + text)
        included.append({"doc_id": document["doc_id"], "type": document["type"], "chars": len(text), "complete": len(text) == len(document["text"])})
        remaining -= len(header) + len(text)
        if len(text) < len(document["text"]):
            break
    return "\n\n".join(parts), {"max_document_chars_total": limit, "included_documents": included}


def build_messages(record: dict[str, Any], system_prompt: str, char_limit: int) -> tuple[list[dict[str, str]], dict[str, Any]]:
    documents, rendering = render_documents(record, char_limit)
    unavailable = record.get("dropped_doc_counts") or {}
    user = "\n\n".join(
        [
            f"[공고 ID]\n{record['id']}",
            "[나라장터 입력 메타]\n" + json.dumps(record["meta"], ensure_ascii=False, sort_keys=True),
            "[미수록 문서]\n" + json.dumps(unavailable, ensure_ascii=False, sort_keys=True),
            "[문서]\n" + documents,
        ]
    )
    return [{"role": "system", "content": system_prompt}, {"role": "user", "content": user}], rendering


def judgment_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(ITEMS),
        "properties": {
            item: {
                "type": "object",
                "additionalProperties": False,
                "required": ["위반여부", "근거문구"],
                "properties": {
                    "위반여부": {"type": "integer", "enum": [0, 1]},
                    "근거문구": {"type": ["string", "null"], "maxLength": 2000},
                },
            }
            for item in ITEMS
        },
    }


def parse_json(content: str) -> dict[str, Any]:
    candidates = [content.strip(), *(match.group(1) for match in FENCE.finditer(content))]
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload.get("판정", payload)
    start, end = content.find("{"), content.rfind("}")
    if start >= 0 and end > start:
        payload = json.loads(content[start : end + 1])
        return payload.get("판정", payload) if isinstance(payload, dict) else {}
    raise ValueError("response is not JSON")


def postprocess(payload: dict[str, Any], record: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    source = "\n".join(document["text"] for document in record["docs"])
    result: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []
    for item in ITEMS:
        cell = payload.get(item)
        if not isinstance(cell, dict) or cell.get("위반여부") not in (0, 1):
            raise ValueError(f"invalid cell {item}")
        violation = int(cell["위반여부"])
        evidence = cell.get("근거문구")
        if item in ABSENCE_ITEMS:
            evidence = ""
        elif violation == 1:
            evidence = evidence.strip() if isinstance(evidence, str) else ""
            if evidence not in source:
                warnings.append(f"{item}: invalid evidence")
                evidence = ""
            evidence = evidence[:500]
        else:
            evidence = ""
        result[item] = {"위반여부": violation, "근거문구": evidence}
    return result, warnings


def completion(
    config: dict[str, Any],
    messages: list[dict[str, str]],
    response_schema: dict[str, Any] | None = None,
) -> Completion:
    api_key = os.environ.get(config["api_key_env"], "")
    if not api_key:
        raise RuntimeError(f"missing {config['api_key_env']}")
    payload = {
        "model": config["model"], "messages": messages, "temperature": config["temperature"],
        "max_tokens": config["max_tokens"], "seed": config["seed"], "stream": False,
        "provider": {"require_parameters": True, "sort": "throughput"},
        "response_format": {"type": "json_schema", "json_schema": {"name": "inc001_judgment", "strict": True, "schema": response_schema or judgment_schema()}},
    }
    last_error = "unknown"
    for attempt in range(config["request_retries"] + 1):
        started = time.monotonic()
        try:
            response = requests.post(config["api_url"], headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json=payload, timeout=config["timeout_seconds"])
            if response.ok:
                body = response.json()
                choice = body["choices"][0]
                content = choice["message"]["content"]
                if not isinstance(content, str) or not content.strip():
                    raise ValueError("empty content")
                return Completion(content, str(body.get("model", config["model"])), body.get("usage", {}), round(time.monotonic() - started, 3), choice.get("finish_reason"))
            last_error = f"HTTP {response.status_code}: {response.text[:300]}"
            if response.status_code not in {408, 409, 429, 500, 502, 503, 504}:
                break
        except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        if attempt < config["request_retries"]:
            time.sleep(2**attempt)
    raise RuntimeError(last_error)


def to_row(record_id: str, judgment: dict[str, dict[str, Any]]) -> dict[str, Any]:
    row: dict[str, Any] = {"id": record_id}
    for index, item in enumerate(ITEMS, 1):
        row[item] = judgment[item]["위반여부"]
        row[f"e{index}"] = judgment[item]["근거문구"]
    return row


def zero_judgment() -> dict[str, dict[str, Any]]:
    return {item: {"위반여부": 0, "근거문구": ""} for item in ITEMS}


def evaluate(rows: list[dict[str, Any]], labels: dict[str, dict[str, str]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    per_item: list[dict[str, Any]] = []
    for item in ITEMS:
        tp = fp = fn = 0
        for row in rows:
            gold, prediction = int(labels[row["id"]][item]), int(row[item])
            tp += gold == prediction == 1
            fp += gold == 0 and prediction == 1
            fn += gold == 1 and prediction == 0
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_item.append({"item": item, "gold_positive": tp + fn, "predicted_positive": tp + fp, "tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1})
    return {"macro_f1": sum(item["f1"] for item in per_item) / len(per_item)}, per_item


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="incubator/configs/inc001_simple_joint24_pilot.json")
    parser.add_argument("--mode", choices=("preflight", "run"), default="preflight")
    args = parser.parse_args()
    root = repo_root()
    config = json.loads((root / args.config).read_text(encoding="utf-8"))
    load_dotenv(root / ".env")
    output = root / "incubator" / "runs" / config["experiment_id"]
    output.mkdir(parents=True, exist_ok=True)
    data_root = root / config["data_root"]
    records = read_jsonl_gz(data_root / "dev.jsonl.gz")
    label_rows = read_csv(data_root / "dev_labels.csv")
    labels = {row["id"]: row for row in label_rows}
    item_payload = json.loads((data_root / "data" / "항목표.json").read_text(encoding="utf-8"))
    item_table = item_payload["항목"]
    historical_fp = load_historical_false_positives(root / config["historical_prediction_path"], labels)
    cohort_labels, cohort_meta = select_cohort(label_rows, historical_fp, config["positive_seed_limit"], config["hard_negative_limit"])
    record_by_id = {record["id"]: record for record in records}
    cohort = [record_by_id[row["id"]] for row in cohort_labels]
    system = build_system_prompt(item_table)
    inputs: list[dict[str, Any]] = []
    for record in cohort:
        messages, rendering = build_messages(record, system, config["max_document_chars_total"])
        inputs.append({"id": record["id"], "messages": messages, "rendering": rendering, "prompt_sha256": sha256_text(json.dumps(messages, ensure_ascii=False, sort_keys=True))})
    preflight = {"experiment_id": config["experiment_id"], "config": config, "source_sha256": {"dev": sha256_file(data_root / "dev.jsonl.gz"), "labels": sha256_file(data_root / "dev_labels.csv"), "item_table": sha256_file(data_root / "data" / "항목표.json")}, "cohort": cohort_meta, "input_count": len(inputs), "all_items_covered": not cohort_meta["uncovered_items"], "mode": args.mode}
    write_json(output / "config.json", config)
    write_json(output / "preflight.json", preflight)
    write_jsonl(output / "inputs.jsonl", inputs)
    if args.mode == "preflight":
        print(json.dumps({"status": "preflight_ok", **preflight}, ensure_ascii=False, indent=2))
        return
    if len(inputs) > config["max_requests"]:
        raise RuntimeError("cohort exceeds max_requests")
    checkpoint_path = output / "checkpoint.jsonl"
    completed: dict[str, dict[str, Any]] = {}
    if checkpoint_path.exists():
        for line in checkpoint_path.read_text(encoding="utf-8").splitlines():
            entry = json.loads(line)
            completed[entry["id"]] = entry
    responses: list[dict[str, Any]] = [entry["response"] for entry in completed.values()]
    rows: list[dict[str, Any]] = [entry["row"] for entry in completed.values()]
    warnings: list[dict[str, Any]] = [warning for entry in completed.values() for warning in entry["warnings"]]
    total_cost = sum(float(response["usage"].get("cost", 0.0) or 0.0) for response in responses)
    for index, (record, prepared) in enumerate(zip(cohort, inputs), 1):
        if record["id"] in completed:
            print(f"[{index}/{len(cohort)}] {record['id']} resumed", flush=True)
            continue
        if total_cost >= config["max_cost_usd"]:
            raise RuntimeError("reported cost ceiling reached before next request")
        try:
            result = completion(config, prepared["messages"])
            payload = parse_json(result.content)
            judgment, record_warnings = postprocess(payload, record)
            response_row = {"id": record["id"], "raw_response": result.content, "model": result.model, "usage": result.usage, "latency_seconds": result.latency_seconds, "finish_reason": result.finish_reason, "evidence_warnings": record_warnings, "success": True}
        except (RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            judgment = zero_judgment()
            record_warnings = [f"transport_or_parse_failure: {type(exc).__name__}: {str(exc)[:300]}"]
            response_row = {"id": record["id"], "raw_response": "", "model": config["model"], "usage": {}, "latency_seconds": 0.0, "finish_reason": None, "evidence_warnings": record_warnings, "success": False}
        row = to_row(record["id"], judgment)
        cost = float(response_row["usage"].get("cost", 0.0) or 0.0)
        total_cost += cost
        rows.append(row)
        record_warning_rows = [{"id": record["id"], "warning": warning} for warning in record_warnings]
        warnings.extend(record_warning_rows)
        responses.append(response_row)
        append_jsonl(checkpoint_path, {"id": record["id"], "row": row, "response": response_row, "warnings": record_warning_rows})
        print(f"[{index}/{len(cohort)}] {record['id']} cost=${cost:.6f} cumulative=${total_cost:.6f}", flush=True)
        if index < len(cohort):
            time.sleep(config["min_request_interval_seconds"])
    metrics, per_item = evaluate(rows, labels)
    valid_positive = 0
    valid_evidence = 0
    for row in rows:
        source = "\n".join(doc["text"] for doc in record_by_id[row["id"]]["docs"])
        for index, item in enumerate(ITEMS, 1):
            if row[item] == 1 and item not in ABSENCE_ITEMS:
                valid_positive += 1
                valid_evidence += bool(row[f"e{index}"]) and row[f"e{index}"] in source
    metrics.update({"request_count": len(responses), "successful_request_count": sum(bool(response.get("success", True)) for response in responses), "reported_cost_usd": total_cost, "evidence_validity": valid_evidence / valid_positive if valid_positive else None, "evidence_positive_cases": valid_positive, "warning_count": len(warnings), "latency_seconds": sum(response["latency_seconds"] for response in responses)})
    with (output / "predictions.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    with (output / "per_item_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(per_item[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(per_item)
    write_jsonl(output / "responses.jsonl", responses)
    write_jsonl(output / "warnings.jsonl", warnings)
    write_json(output / "metrics.json", metrics)
    print(json.dumps({"status": "complete", "metrics": metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
