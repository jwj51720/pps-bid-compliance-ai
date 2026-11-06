#!/usr/bin/env python3
"""Evaluate full-notice external-teacher legal contexts on dev-200.

The evaluator reads dev labels only after every request is prepared.  Labels are
never part of an LLM message.  This script is isolated from the shared pipeline.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import os
import time
from collections import Counter
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

import inc001_simple_joint24 as common


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/raw/open"
CARDS = ROOT / "incubator/reference/dev_history/decision_cards_v6.json"
LEDGER = ROOT / "incubator/reference/dev_history/legal_condition_ledger_v1.json"
DEFAULT_MODEL = "google/gemini-2.5-flash"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENAI_API_URL = "https://api.openai.com/v1/responses"
MAX_TOKENS = 768
CONCURRENCY = 12
MAX_COST_USD = 20.0


def schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(common.ITEMS),
        "properties": {item: {"type": "integer", "enum": [0, 1]} for item in common.ITEMS},
    }


def profile(record: dict[str, Any]) -> str:
    meta = record["meta"]
    if meta.get("적용계약법") == "국가계약법":
        return "national"
    if meta.get("계약방법") == "수의계약":
        return "local_small"
    if meta.get("낙찰방법") == "협상에의한계약":
        return "local_negotiated"
    return "local_general"


def render_documents(record: dict[str, Any]) -> str:
    order = {name: index for index, name in enumerate(common.DOCUMENT_ORDER)}
    return "\n\n".join(
        f"[{document['type']} | {document['doc_id']}]\n{document['text']}"
        for document in sorted(record["docs"], key=lambda document: (order[document["type"]], document["doc_id"]))
    )


def item_catalog(table: dict[str, Any]) -> str:
    return "\n".join(
        f"- {item}: {row['항목명']}" + (f" / 비고: {row['비고']}" if row.get("비고") else "")
        + (" [부재탐지]" if row.get("부재탐지") else "")
        for item, row in table.items()
    )


def card_context(cards: dict[str, Any]) -> str:
    return "\n".join(
        f"[{item} | {card['item_name']}]\n{card['prompt_text']}"
        for item, card in cards["cards"].items()
    )


def ledger_context(ledger: dict[str, Any], active_profile: str) -> str:
    entries = [entry for key, entry in ledger["entries"].items() if key.startswith(active_profile + "/")]
    summaries: list[str] = []
    sources: dict[str, dict[str, Any]] = {}
    for entry in sorted(entries, key=lambda entry: entry["group"]):
        for item in entry["items"]:
            inactive = f" / 비적용: {item['inactive_reason']}" if item.get("inactive_reason") else ""
            summaries.append(f"[{item['item']}] {item['model_summary']}{inactive}")
            for source in item["official_sources"]:
                sources[source["chunk_sha256"]] = source
    source_text = "\n\n".join(
        f"[공식 조문 | {source['title']} | {source['selector']}]\n{source['official_text']}"
        for source in sources.values()
    )
    return "[항목별 법령 판단 요약]\n" + "\n".join(summaries) + "\n\n[공식 법령 원문]\n" + source_text


def messages(record: dict[str, Any], table: dict[str, Any], legal_context: str, arm: str, prompt_mode: str) -> list[dict[str, str]]:
    system = """당신은 한국 공공입찰 법령 위반을 판정하는 독립 법률 검토자다.
현재 공고의 모든 원문 문서, 나라장터 메타데이터, 그리고 제공된 공식 법령 자료만 사용한다.
각 항목은 별개의 법적 요건이다. 키워드만으로 위반을 단정하지 말고 적용 법령, 금액, 계약방식,
제품성격, 예외, 실제 참가제한·문서부재·메타 불일치를 함께 확인한다. [부재탐지]는 적용대상임이
확인된 뒤 필요한 문구/조건이 공고 전체에 없을 때만 1이다. 불확실한 외부 사실은 만들지 않는다.
내부적으로 조문과 모든 문서를 검토한 뒤, 최종 24개 0/1만 JSON으로 출력한다."""
    operations = ""
    if prompt_mode == "operational":
        operations = """\n\n[반드시 따를 판단 연산]
1) 제한·실적·제품 항목: 먼저 원문/메타에서 관찰된 제한 사실을 찾고, 그 다음에만 카드의 적용대상·금액·예외 조건을 대조한다. 제한 표현 자체와 법률상 위반 결론을 혼동하지 않는다.
2) [부재탐지] 항목: 적용대상임을 먼저 확인한 뒤, 모든 제공 문서에서 필요한 조건의 존재를 검토한다. 적용대상이 불명확하면 부재를 위반으로 단정하지 않는다.
3) v24: 예산은 예산, 계약방법은 계약방법, 지역제한은 참가자격 지역제한, 업종은 업종으로만 같은 필드를 대조한다. 문서에 대응 값이 없거나 표현·분류만 다르면 불일치가 아니다. 다른 필드, 일반 지역 언급, 문맥 설명을 비교 근거로 쓰지 않는다.
4) 위 절차를 24개 항목 각각에 독립 적용한 뒤 JSON만 출력한다."""
    elif prompt_mode == "clause_salient":
        clause = record["meta"].get("조항호내용")
        operations = """\n\n[주요 적용성 metadata]
나라장터가 이 공고에 기록한 법률·조항 분류는 아래와 같다. 이것은 일반 배경설명이 아니라 적용대상과 예외를 판단하는 제공된 사실이다. 원문과 함께 우선 검토하되, 그 자체만으로 제한의 존재를 만들어내지는 말고 각 카드의 필요한 제한/부재 조건을 계속 확인한다.
""" + json.dumps({"조항호내용": clause}, ensure_ascii=False)
    user = "\n\n".join(
        [
            f"[calibration arm]\n{arm}",
            "[판정 항목]\n" + item_catalog(table),
            "[나라장터 메타]\n" + json.dumps(record["meta"], ensure_ascii=False, sort_keys=True),
            "[누락 문서 정보]\n" + json.dumps(record.get("dropped_doc_counts") or {}, ensure_ascii=False, sort_keys=True),
            "[법령 판단 자료]\n" + legal_context,
            "[공고 원문 전체]\n" + render_documents(record),
            operations,
        ]
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def complete(api_key: str, prepared: dict[str, Any], model: str, provider: str, max_tokens: int, reasoning_effort: str | None) -> dict[str, Any]:
    if provider == "openai":
        payload = {
            "model": model,
            "input": prepared["messages"],
            "max_output_tokens": max_tokens,
            "store": False,
            "text": {"format": {"type": "json_schema", "name": "inc081_labels", "strict": True, "schema": schema()}},
        }
        if reasoning_effort:
            payload["reasoning"] = {"effort": reasoning_effort}
        url = OPENAI_API_URL
    else:
        payload = {
            "model": model,
            "messages": prepared["messages"],
            "temperature": 0.0,
            "max_tokens": max_tokens,
            "stream": False,
        }
        url = API_URL
    error = "unknown"
    raw_content = ""
    for attempt in range(4):
        started = time.monotonic()
        try:
            response = requests.post(url, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json=payload, timeout=240)
            if response.ok:
                body = response.json()
                if provider == "openai":
                    content = body.get("output_text")
                    if not isinstance(content, str):
                        content = "".join(
                            block.get("text", "")
                            for message in body.get("output", []) if message.get("type") == "message"
                            for block in message.get("content", []) if block.get("type") == "output_text"
                        )
                else:
                    content = body["choices"][0]["message"]["content"]
                raw_content = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
                candidate = raw_content.strip()
                if candidate.startswith("```"):
                    lines = candidate.splitlines()
                    candidate = "\n".join(lines[1:-1]).strip()
                parsed = json.loads(candidate)
                if set(parsed) != set(common.ITEMS) or any(parsed[item] not in (0, 1) for item in common.ITEMS):
                    raise ValueError("schema-valid response has invalid labels")
                return {"id": prepared["id"], "arm": prepared["arm"], "success": True, "labels": parsed, "raw_response": raw_content, "usage": body.get("usage", {}), "latency_seconds": round(time.monotonic() - started, 3), "model": body.get("model", model)}
            error = f"HTTP {response.status_code}: {response.text[:300]}"
            if response.status_code not in {408, 409, 429, 500, 502, 503, 504}:
                break
        except (requests.RequestException, ValueError, KeyError, IndexError, json.JSONDecodeError) as exc:
            error = f"{type(exc).__name__}: {exc}"
        time.sleep(2**attempt)
    return {"id": prepared["id"], "arm": prepared["arm"], "success": False, "error": error, "labels": {item: 0 for item in common.ITEMS}, "raw_response": raw_content, "usage": {}, "latency_seconds": 0.0, "model": model}


def score(rows: list[dict[str, Any]], labels: dict[str, dict[str, str]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    output: list[dict[str, Any]] = []
    for item in common.ITEMS:
        tp = fp = fn = 0
        for row in rows:
            gold, prediction = int(labels[row["id"]][item]), int(row["labels"][item])
            tp += int(gold == prediction == 1); fp += int(gold == 0 and prediction == 1); fn += int(gold == 1 and prediction == 0)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        output.append({"item": item, "gold_positive": tp + fn, "predicted_positive": tp + fp, "tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0})
    return {"macro_f1": sum(row["f1"] for row in output) / len(output)}, output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "run"), default="preflight")
    parser.add_argument("--arms", nargs="+", choices=("card_v6", "official_ledger"), default=("card_v6", "official_ledger"))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--concurrency", type=int, default=CONCURRENCY)
    parser.add_argument("--run-id", default="inc081_teacher_full_context_calibration")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--provider", choices=("openrouter", "openai"), default="openrouter")
    parser.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    parser.add_argument("--reasoning-effort", choices=("none", "low", "medium", "high", "xhigh"))
    parser.add_argument("--prompt-mode", choices=("baseline", "operational", "clause_salient"), default="baseline")
    parser.add_argument("--ids-manifest", type=Path, help="JSONL records with an id field; preserves a pre-frozen cohort")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    api_key = os.environ.get("OPENAI_API_KEY" if args.provider == "openai" else "OPENROUTER_API_KEY", "")
    if args.mode == "run" and not api_key:
        raise RuntimeError("missing OPENROUTER_API_KEY")
    output = ROOT / "incubator/runs" / args.run_id
    output.mkdir(parents=True, exist_ok=True)
    records = common.read_jsonl_gz(DATA / "dev.jsonl.gz")
    if args.ids_manifest:
        wanted = [json.loads(line)["id"] for line in args.ids_manifest.read_text(encoding="utf-8").splitlines() if line]
        by_id = {record["id"]: record for record in records}
        if len(wanted) != len(set(wanted)) or any(record_id not in by_id for record_id in wanted):
            raise ValueError("ids manifest must contain unique dev IDs")
        records = [by_id[record_id] for record_id in wanted]
    if args.limit is not None:
        records = records[:args.limit]
    labels = {row["id"]: row for row in common.read_csv(DATA / "dev_labels.csv")}
    table = json.loads((DATA / "data/항목표.json").read_text(encoding="utf-8"))["항목"]
    cards = json.loads(CARDS.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    prepared = []
    for arm in args.arms:
        for record in records:
            legal = card_context(cards) if arm == "card_v6" else ledger_context(ledger, profile(record))
            value = {"id": record["id"], "arm": arm, "messages": messages(record, table, legal, arm, args.prompt_mode)}
            value["prompt_sha256"] = common.sha256_text(json.dumps(value["messages"], ensure_ascii=False, sort_keys=True))
            value["prompt_characters"] = sum(len(message["content"]) for message in value["messages"])
            prepared.append(value)
    if args.concurrency < 1 or args.max_tokens < 128:
        raise ValueError("concurrency must be positive and max-tokens >= 128")
    report = {"experiment_id": args.run_id, "mode": args.mode, "arms": list(args.arms), "model": args.model, "provider": args.provider, "max_tokens": args.max_tokens, "reasoning_effort": args.reasoning_effort, "prompt_mode": args.prompt_mode, "ids_manifest": str(args.ids_manifest) if args.ids_manifest else None, "request_count": len(prepared), "concurrency": args.concurrency, "max_cost_usd": MAX_COST_USD, "source_sha256": {"dev": common.sha256_file(DATA / "dev.jsonl.gz"), "labels": common.sha256_file(DATA / "dev_labels.csv"), "item_table": common.sha256_file(DATA / "data/항목표.json"), "cards": common.sha256_file(CARDS), "ledger": common.sha256_file(LEDGER)}, "prompt_characters": {arm: [entry["prompt_characters"] for entry in prepared if entry["arm"] == arm] for arm in args.arms}, "labels_excluded_from_messages": True}
    report["prompt_characters"] = {arm: {"min": min(values), "max": max(values), "mean": sum(values) / len(values)} for arm, values in report["prompt_characters"].items()}
    common.write_json(output / "preflight.json", report)
    common.write_jsonl(output / "inputs.jsonl", prepared)
    if args.mode == "preflight":
        print(json.dumps({"status": "preflight_ok", **report}, ensure_ascii=False, indent=2)); return
    checkpoint = output / "checkpoint.jsonl"
    done: dict[tuple[str, str], dict[str, Any]] = {}
    if checkpoint.exists():
        for line in checkpoint.read_text(encoding="utf-8").splitlines():
            row = json.loads(line); done[(row["arm"], row["id"])] = row
    pending = [entry for entry in prepared if not done.get((entry["arm"], entry["id"]), {}).get("success")]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {executor.submit(complete, api_key, entry, args.model, args.provider, args.max_tokens, args.reasoning_effort): entry for entry in pending}
        for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            row = future.result(); done[(row["arm"], row["id"])] = row; common.append_jsonl(checkpoint, row)
            print(f"[{index}/{len(pending)}] {row['arm']} {row['id']} success={row['success']}", flush=True)
    all_rows = list(done.values())
    results: dict[str, Any] = {"preflight": report, "arms": {}}
    for arm in args.arms:
        rows = [row for row in all_rows if row["arm"] == arm]
        metrics, per_item = score(rows, labels)
        metrics.update({"success_count": sum(row["success"] for row in rows), "reported_cost_usd": sum(float(row.get("usage", {}).get("cost", 0.0) or 0.0) for row in rows), "mean_latency_seconds": sum(row["latency_seconds"] for row in rows) / len(rows)})
        results["arms"][arm] = metrics
        with (output / f"per_item_{arm}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(per_item[0])); writer.writeheader(); writer.writerows(per_item)
    common.write_jsonl(output / "responses.jsonl", all_rows)
    common.write_json(output / "metrics.json", results)
    print(json.dumps({"status": "complete", "arms": results["arms"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
