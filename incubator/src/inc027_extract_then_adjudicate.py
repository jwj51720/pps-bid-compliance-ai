#!/usr/bin/env python3
"""Resumable, per-notice INC-027 extract-then-adjudicate pilot."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

import inc001_simple_joint24 as common
from inc006_input_budget_ablation import metric


ROOT = Path(__file__).resolve().parents[2]
IDS = (
    "PPS-DEV-01", "PPS-DEV-02", "PPS-DEV-033", "PPS-DEV-035",
    "PPS-DEV-034", "PPS-DEV-036", "PPS-DEV-049", "PPS-DEV-055",
)
TYPE_DESCRIPTIONS = {
    "money": "금액, 예산, 예정가격, 보증금 또는 금전 단위",
    "date_time": "날짜, 시각, 기간, 기한 또는 마감",
    "ratio": "비율, 점수, 지분 또는 퍼센트",
    "product_code": "물품·용역명, 세부품명, 업종 또는 코드",
    "method": "입찰·낙찰·계약·평가 방식",
    "qualification": "입찰참가 자격, 실적, 인력·면허·기업 조건",
    "region": "소재지·지역 제한 또는 지역 관련 조건",
    "restriction": "참여·공동수급·하도급 등을 제한하거나 금지하는 조건",
    "joint_contract": "공동계약, 공동수급, 분담·공동이행 또는 하도급 조건",
    "metadata_relation": "문서 내용과 제공 메타 사이의 명시적 대응값",
}


def render_docs(record: dict[str, Any]) -> str:
    ordered = sorted(record["docs"], key=lambda doc: (common.DOCUMENT_ORDER[doc["type"]], doc["doc_id"]))
    return "\n\n".join(f"[{doc['type']}:{doc['doc_id']}]\n{doc['text']}" for doc in ordered)


def fact_schema() -> dict[str, Any]:
    alternatives = []
    for name, description in TYPE_DESCRIPTIONS.items():
        alternatives.append({"type": "object", "additionalProperties": False,
            "required": ["type", "doc_id", "quote"], "properties": {
                "type": {"type": "string", "const": name, "description": description},
                "doc_id": {"type": "string", "description": "quote가 나온 원문 문서 ID"},
                "quote": {"type": "string", "maxLength": 500,
                          "description": "원문에서 변경 없이 복사한 연속 부분문자열"},
            }})
    return {"type": "object", "additionalProperties": False, "required": ["facts"],
            "properties": {"facts": {"type": "array", "items": {"oneOf": alternatives}}}}


def extractor_messages(record: dict[str, Any]) -> list[dict[str, str]]:
    taxonomy = "\n".join(f"- {name}: {description}" for name, description in TYPE_DESCRIPTIONS.items())
    return [{"role": "system", "content": (
        "공공입찰 문서에서 명시 사실만 추출한다. 추론·위반판정은 금지한다. "
        "각 사실은 type, 원문 doc_id, 변경 없는 quote를 가진다. quote 없는 사실은 내지 않는다.\n유형 분류:\n" + taxonomy)},
        {"role": "user", "content": "[메타]\n" + json.dumps(record["meta"], ensure_ascii=False, sort_keys=True)
         + "\n\n[문서]\n" + render_docs(record)}]


def adjudicator_messages(record: dict[str, Any], facts: list[dict[str, str]], item_table: dict[str, Any]) -> list[dict[str, str]]:
    return [{"role": "system", "content": common.build_system_prompt(item_table) + (
        "\n\n아래 추출 ledger는 참고다. 원문과 ledger를 대조해 24항목을 판정하라. "
        "non-absence 양성 근거는 ledger quote를 그대로 사용해야 한다.")},
        {"role": "user", "content": "[메타]\n" + json.dumps(record["meta"], ensure_ascii=False, sort_keys=True)
         + "\n[LEDGER]\n" + json.dumps(facts, ensure_ascii=False) + "\n[전체 문서]\n" + render_docs(record)}]


def config() -> dict[str, Any]:
    return {"model": "google/gemma-4-26b-a4b-it", "api_url": "https://openrouter.ai/api/v1/chat/completions",
            "api_key_env": "OPENROUTER_API_KEY", "temperature": 0.0, "seed": 20260905,
            "max_tokens": 1800, "timeout_seconds": 120, "request_retries": 1}


def valid_facts(payload: dict[str, Any], record: dict[str, Any]) -> list[dict[str, str]]:
    facts = []
    for fact in payload.get("facts", []):
        if not isinstance(fact, dict) or fact.get("type") not in TYPE_DESCRIPTIONS:
            continue
        quote, doc_id = fact.get("quote"), fact.get("doc_id")
        if isinstance(quote, str) and isinstance(doc_id, str) and any(
            doc["doc_id"] == doc_id and quote in doc["text"] for doc in record["docs"]):
            facts.append({"type": fact["type"], "doc_id": doc_id, "quote": quote})
    return facts


def gate_evidence(judgment: dict[str, dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Apply the preregistered ledger-evidence gate after source validation."""
    warnings = []
    for item in common.ITEMS:
        if item not in common.ABSENCE_ITEMS and judgment[item]["위반여부"] == 1 and not judgment[item]["근거문구"]:
            judgment[item] = {"위반여부": 0, "근거문구": ""}
            warnings.append(f"{item}: downgraded because source evidence was invalid")
    return judgment, warnings


def load_inputs() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, str]], dict[str, Any]]:
    data_root = ROOT / "data/raw/open"
    records = {row["id"]: row for row in common.read_jsonl_gz(data_root / "dev.jsonl.gz")}
    labels = {row["id"]: row for row in common.read_csv(data_root / "dev_labels.csv")}
    table = json.loads((data_root / "data/항목표.json").read_text(encoding="utf-8"))["항목"]
    return records, labels, table


def run_one(record_id: str, output: Path) -> None:
    records, _, item_table = load_inputs()
    record, checkpoint = records[record_id], output / "checkpoint.jsonl"
    result_path = output / "records" / f"{record_id}.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    extractor: Any = None
    try:
        extractor = common.completion(config(), extractor_messages(record), fact_schema())
        facts = valid_facts(common.parse_json(extractor.content), record)
    except Exception as exc:
        entry = {"id": record_id, "stage": "extractor", "success": False, "error": f"{type(exc).__name__}: {exc}",
                 "raw_response": "" if extractor is None else extractor.content,
                 "usage": {} if extractor is None else extractor.usage}
        common.append_jsonl(checkpoint, entry); common.write_json(result_path, entry); return
    common.append_jsonl(checkpoint, {"id": record_id, "stage": "extractor", "success": True,
                                     "raw_response": extractor.content, "usage": extractor.usage, "facts": facts})
    adjudicator: Any = None
    try:
        adjudicator = common.completion(config(), adjudicator_messages(record, facts, item_table), common.judgment_schema())
        judgment, warnings = common.postprocess(common.parse_json(adjudicator.content), record)
        judgment, gate_warnings = gate_evidence(judgment); warnings.extend(gate_warnings)
        row = common.to_row(record_id, judgment)
    except Exception as exc:
        entry = {"id": record_id, "stage": "adjudicator", "success": False, "facts": facts,
                 "extractor_usage": extractor.usage, "error": f"{type(exc).__name__}: {exc}",
                 "raw_response": "" if adjudicator is None else adjudicator.content,
                 "usage": {} if adjudicator is None else adjudicator.usage}
        common.append_jsonl(checkpoint, entry); common.write_json(result_path, entry); return
    entry = {"id": record_id, "stage": "complete", "success": True, "facts": facts,
             "extractor_usage": extractor.usage, "adjudicator_usage": adjudicator.usage,
             "extractor_raw_response": extractor.content, "adjudicator_raw_response": adjudicator.content,
             "warnings": warnings, "row": row}
    common.append_jsonl(checkpoint, entry); common.write_json(result_path, entry)


def aggregate(output: Path) -> None:
    records, labels, _ = load_inputs(); entries = []
    for record_id in IDS:
        path = output / "records" / f"{record_id}.json"
        if path.exists(): entries.append(json.loads(path.read_text(encoding="utf-8")))
    complete = [entry for entry in entries if entry.get("stage") == "complete"]
    cost = sum(float(entry["extractor_usage"].get("cost", 0) or 0) + float(entry["adjudicator_usage"].get("cost", 0) or 0) for entry in complete)
    result: dict[str, Any] = {"experiment_id": "inc027_extract_then_adjudicate_pilot_r1", "requested_notices": len(IDS),
                              "completed_notices": len(complete), "failure_count": len(entries) - len(complete), "reported_cost_usd": cost}
    if complete:
        rows = [entry["row"] for entry in complete]; metrics, per_item = metric(rows, labels, records)
        result.update({"metrics": metrics, "per_item": per_item})
        with (output / "predictions.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=common.CSV_COLUMNS, lineterminator="\n"); writer.writeheader(); writer.writerows(rows)
    common.write_json(output / "metrics.json", result); common.write_jsonl(output / "responses.jsonl", entries)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--id", choices=IDS); parser.add_argument("--aggregate", action="store_true")
    args = parser.parse_args()
    if not args.id and not args.aggregate: parser.error("use --id ID or --aggregate")
    load_dotenv(ROOT / ".env"); output = ROOT / "incubator/runs/inc027_extract_then_adjudicate_pilot_r1"; output.mkdir(parents=True, exist_ok=True)
    if args.id: run_one(args.id, output)
    if args.aggregate: aggregate(output)


if __name__ == "__main__": main()
