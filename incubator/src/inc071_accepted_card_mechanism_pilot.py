#!/usr/bin/env python3
"""INC-071: paired full-notice judgment with audited legal-essence cards only."""
from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

import inc001_simple_joint24 as common
import inc018_global_context_architecture as context

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "incubator/runs/inc071_accepted_card_mechanism_pilot"
ABSENCE = common.ABSENCE_ITEMS


def load() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    data = ROOT / "data/raw/open"
    records = {r["id"]: r for r in common.read_jsonl_gz(data / "dev.jsonl.gz")}
    labels = {r["id"]: r for r in common.read_csv(data / "dev_labels.csv")}
    cards = json.loads((ROOT / "incubator/data/derived/legal_essence_cards_v1.json").read_text(encoding="utf-8"))["cards"]
    return records, labels, cards


def items(cards: dict[str, Any]) -> tuple[str, ...]:
    return tuple(item for item in common.ITEMS if item in cards)


def cohort(records: dict[str, Any], labels: dict[str, Any], target: tuple[str, ...]) -> list[str]:
    selected = set()
    for item in target:
        positive = [rid for rid in records if labels[rid][item] == "1"]
        if not positive:
            raise RuntimeError(f"no dev positive for {item}")
        selected.add(min(positive, key=lambda rid: hashlib.sha256(f"inc071:{item}:{rid}".encode()).hexdigest()))
    # 32 is not a tuned performance quantity: it is the smallest fixed cohort
    # with one positive per target plus 21 independent hash-selected notices,
    # enough to expose new false positives without paying for an all-dev run.
    remainder = sorted((rid for rid in records if rid not in selected), key=lambda rid: hashlib.sha256(f"inc071:remainder:{rid}".encode()).hexdigest())
    selected.update(remainder[:32 - len(selected)])
    return sorted(selected)


def schema(target: tuple[str, ...]) -> dict[str, Any]:
    return {"type": "object", "additionalProperties": False, "required": list(target), "properties": {
        item: {"type": "object", "additionalProperties": False, "required": ["v", "e"], "properties": {"v": {"type": "integer", "enum": [0, 1]}, "e": {"type": ["string", "null"], "maxLength": 500}}}
        for item in target}}


def messages(record: dict[str, Any], cards: dict[str, Any], target: tuple[str, ...], arm: str) -> list[dict[str, str]]:
    system = [
        "당신은 공공입찰 공고의 법령 위반을 독립적으로 판단한다.",
        "메타와 제공된 모든 원문 문서를 읽는다. 키워드만으로 단정하지 말고 적용 전제, 실제 제한, 예외를 함께 확인한다.",
        "v=1이면 e는 원문 문서에 있는 변경 없는 연속 부분문자열(500자 이하)이다. v=0이면 e=null이다.",
        "부재탐지 항목은 v=1이어도 e=null이며, 적용 전제가 확실하지 않으면 0으로 둔다.",
        "JSON 객체 하나만 출력한다.",
    ]
    payload = ["[공고 ID]\n" + record["id"], "[메타]\n" + json.dumps(record["meta"], ensure_ascii=False, sort_keys=True)]
    if arm == "card":
        compact = {item: {"항목명": cards[item]["item_definition"]["항목명"], **cards[item]["card"]} for item in target}
        payload.append("[법령 판단 엑기스: 원문 증거가 아니며, 적용·예외를 확인하는 보조 기준]\n" + json.dumps(compact, ensure_ascii=False))
    payload.append("[전체 문서]\n" + context.full_context(record))
    return [{"role": "system", "content": "\n".join(system)}, {"role": "user", "content": "\n\n".join(payload)}]


def cfg() -> dict[str, Any]:
    return {"model": "google/gemma-4-26b-a4b-it", "api_url": "https://openrouter.ai/api/v1/chat/completions", "api_key_env": "OPENROUTER_API_KEY", "temperature": 0.0, "seed": 20260905, "max_tokens": 800, "timeout_seconds": 120, "request_retries": 1}


def validate(payload: dict[str, Any], record: dict[str, Any], target: tuple[str, ...]) -> tuple[dict[str, Any], list[str]]:
    source = "\n".join(doc["text"] for doc in record["docs"]); result = {}; warnings = []
    for item in target:
        cell = payload.get(item)
        if not isinstance(cell, dict) or cell.get("v") not in (0, 1):
            raise ValueError(f"invalid {item}")
        v, e = int(cell["v"]), cell.get("e")
        e = e.strip() if isinstance(e, str) else ""
        if item in ABSENCE: e = ""
        elif v and e not in source:
            warnings.append(f"{item}: invalid evidence; downgraded"); v, e = 0, ""
        elif not v: e = ""
        result[item] = {"v": v, "e": e}
    return result, warnings


def run_one(rid: str, arm: str, repeat: str, records: dict[str, Any], cards: dict[str, Any], target: tuple[str, ...]) -> None:
    path = OUT / "records" / f"{rid}_{arm}_{repeat}.json"
    if path.exists(): return
    response: Any = None
    try:
        response = common.completion(cfg(), messages(records[rid], cards, target, arm), schema(target))
        pred, warnings = validate(common.parse_json(response.content), records[rid], target)
        entry = {"id": rid, "arm": arm, "repeat": repeat, "success": True, "usage": response.usage, "raw_response": response.content, "prediction": pred, "warnings": warnings}
    except Exception as exc:
        entry = {"id": rid, "arm": arm, "repeat": repeat, "success": False, "error": f"{type(exc).__name__}: {exc}", "usage": {} if response is None else response.usage, "raw_response": "" if response is None else response.content}
    path.parent.mkdir(parents=True, exist_ok=True); common.write_json(path, entry)


def metrics(pred: dict[str, Any], labels: dict[str, Any], ids: list[str], target: tuple[str, ...]) -> dict[str, Any]:
    rows = []
    for item in target:
        tp = fp = fn = 0
        for rid in ids:
            gold, value = int(labels[rid][item]), int(pred[rid][item]["v"])
            tp += gold and value; fp += (not gold) and value; fn += gold and (not value)
        rows.append({"item": item, "tp": tp, "fp": fp, "fn": fn, "precision": tp / (tp + fp) if tp + fp else 0, "recall": tp / (tp + fn) if tp + fn else 0, "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0})
    return {"macro_f1": sum(x["f1"] for x in rows) / len(rows), "per_item": rows, "tp": sum(x["tp"] for x in rows), "fp": sum(x["fp"] for x in rows), "fn": sum(x["fn"] for x in rows)}


def preflight() -> None:
    records, labels, cards = load(); target = items(cards); ids = cohort(records, labels, target)
    manifest = [{"id": rid, "positive_targets": [i for i in target if labels[rid][i] == "1"], "control_sha256": common.sha256_text(json.dumps(messages(records[rid], cards, target, "control"), ensure_ascii=False, sort_keys=True)), "card_sha256": common.sha256_text(json.dumps(messages(records[rid], cards, target, "card"), ensure_ascii=False, sort_keys=True))} for rid in ids]
    OUT.mkdir(parents=True, exist_ok=True); common.write_jsonl(OUT / "cohort.jsonl", manifest); common.write_json(OUT / "config.json", {"target_items": target, "cohort_size": len(ids), "repeats": 2, "calls": len(ids) * 4, "max_cost_usd": 0.55, "success_gate": "both card-control Macro-F1 deltas > 0, aggregate newly-correct cells > newly-wrong cells, and no target loses all cohort true positives"})
    print(json.dumps({"status": "preflight_ok", "target": target, "cohort": len(ids), "calls": len(ids) * 4}, ensure_ascii=False, indent=2))


def run(workers: int) -> None:
    records, labels, cards = load(); target = items(cards); ids = cohort(records, labels, target)
    jobs = [(rid, arm, rep) for rid in ids for arm in ("control", "card") for rep in ("r1", "r2")]
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(run_one, rid, arm, rep, records, cards, target) for rid, arm, rep in jobs]
        for n, future in enumerate(as_completed(futures), 1): future.result(); print(f"completed={n}/{len(futures)}", flush=True)


def aggregate() -> None:
    records, labels, cards = load(); target = items(cards); ids = cohort(records, labels, target); report = {"experiment_id": "inc071_accepted_card_mechanism_pilot", "target_items": target, "cohort_size": len(ids), "arms": {}}
    for rep in ("r1", "r2"):
        by_arm = {}
        for arm in ("control", "card"):
            entries = [json.loads((OUT / "records" / f"{rid}_{arm}_{rep}.json").read_text(encoding="utf-8")) for rid in ids]
            failures = [e for e in entries if not e["success"]]
            by_arm[arm] = {"success": len(entries) - len(failures), "failures": len(failures), "cost_usd": sum(float(e.get("usage", {}).get("cost", 0) or 0) for e in entries)}
            if not failures: by_arm[arm].update(metrics({e["id"]: e["prediction"] for e in entries}, labels, ids, target))
        if not by_arm["control"]["failures"] and not by_arm["card"]["failures"]:
            by_arm["delta_card_minus_control"] = by_arm["card"]["macro_f1"] - by_arm["control"]["macro_f1"]
        report["arms"][rep] = by_arm
    common.write_json(OUT / "metrics.json", report); print(json.dumps(report, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--mode", required=True, choices=("preflight", "run", "aggregate")); parser.add_argument("--workers", type=int, default=16); args = parser.parse_args(); load_dotenv(ROOT / ".env"); OUT.mkdir(parents=True, exist_ok=True)
    if args.mode == "preflight": preflight()
    elif args.mode == "run": run(args.workers)
    else: aggregate()


if __name__ == "__main__": main()
