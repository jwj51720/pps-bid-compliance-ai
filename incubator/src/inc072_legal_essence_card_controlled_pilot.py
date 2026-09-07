#!/usr/bin/env python3
"""INC-072: repaired paired test; only audited legal cards vary by arm."""
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
OUT = ROOT / "incubator/runs/inc072_legal_essence_card_controlled_pilot"


def load() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    data = ROOT / "data/raw/open"
    records = {x["id"]: x for x in common.read_jsonl_gz(data / "dev.jsonl.gz")}
    labels = {x["id"]: x for x in common.read_csv(data / "dev_labels.csv")}
    cards = json.loads((ROOT / "incubator/data/derived/legal_essence_cards_v1.json").read_text(encoding="utf-8"))["cards"]
    return records, labels, cards


def target(cards: dict[str, Any]) -> tuple[str, ...]:
    return tuple(x for x in common.ITEMS if x in cards)


def cohort(records: dict[str, Any], labels: dict[str, Any], items: tuple[str, ...]) -> list[str]:
    chosen = set()
    for item in items:
        positives = [rid for rid in records if labels[rid][item] == "1"]
        chosen.add(min(positives, key=lambda rid: hashlib.sha256(f"inc072:{item}:{rid}".encode()).hexdigest()))
    # Fixed coverage design: each target has a positive anchor, then 13
    # independent hash-selected comparison notices.  24 is the first round;
    # a pass, not a local optimum, licenses a broader confirmation.
    remaining = sorted((rid for rid in records if rid not in chosen), key=lambda rid: hashlib.sha256(f"inc072:remaining:{rid}".encode()).hexdigest())
    chosen.update(remaining[:24 - len(chosen)])
    return sorted(chosen)


def schema(items: tuple[str, ...]) -> dict[str, Any]:
    return {"type": "object", "additionalProperties": False, "required": list(items), "properties": {
        x: {"type": "object", "additionalProperties": False, "required": ["v", "e"], "properties": {"v": {"type": "integer", "enum": [0, 1]}, "e": {"type": ["string", "null"], "maxLength": 500}}}
        for x in items}}


def common_contract(cards: dict[str, Any], items: tuple[str, ...]) -> str:
    definitions = []
    for item in items:
        absent = " 부재탐지 항목이며 e는 항상 null." if item in common.ABSENCE_ITEMS else ""
        definitions.append(f"- {item}: {cards[item]['item_definition']['항목명']}.{absent}")
    return "\n".join([
        "당신은 공공입찰 공고의 법령 위반을 독립적으로 판단한다.",
        "메타와 제공된 모든 원문 문서를 읽고, 각 항목의 적용 전제·실제 제한·예외를 함께 확인한다. 키워드만으로 단정하지 않는다.",
        "v=1인 non-absence 항목의 e는 원문 문서의 변경 없는 연속 부분문자열(500자 이하)이어야 한다. v=0이면 e=null이다.",
        "부재탐지 항목은 e=null이며, 적용 전제가 확실하지 않으면 0으로 둔다.",
        "판정 항목:", *definitions, "JSON 객체 하나만 출력한다.",
    ])


def messages(record: dict[str, Any], cards: dict[str, Any], items: tuple[str, ...], arm: str) -> list[dict[str, str]]:
    blocks = ["[공고 ID]\n" + record["id"], "[메타]\n" + json.dumps(record["meta"], ensure_ascii=False, sort_keys=True)]
    if arm == "card":
        essence = {x: cards[x]["card"] for x in items}
        blocks.append("[법령 판단 엑기스: 원문 증거가 아닌 보조 기준. 각 항목의 적용 전제·위반 조건·예외를 원문과 함께 검토한다.]\n" + json.dumps(essence, ensure_ascii=False))
    blocks.append("[전체 문서]\n" + context.full_context(record))
    return [{"role": "system", "content": common_contract(cards, items)}, {"role": "user", "content": "\n\n".join(blocks)}]


def cfg() -> dict[str, Any]:
    return {"model": "google/gemma-4-26b-a4b-it", "api_url": "https://openrouter.ai/api/v1/chat/completions", "api_key_env": "OPENROUTER_API_KEY", "temperature": 0.0, "seed": 20260905, "max_tokens": 800, "timeout_seconds": 120, "request_retries": 1}


def validate(payload: dict[str, Any], record: dict[str, Any], items: tuple[str, ...]) -> tuple[dict[str, Any], list[str]]:
    source = "\n".join(doc["text"] for doc in record["docs"]); output, warnings = {}, []
    for item in items:
        cell = payload.get(item)
        if not isinstance(cell, dict) or cell.get("v") not in (0, 1): raise ValueError(f"invalid {item}")
        value, evidence = int(cell["v"]), cell.get("e"); evidence = evidence.strip() if isinstance(evidence, str) else ""
        if item in common.ABSENCE_ITEMS: evidence = ""
        elif value and evidence not in source: warnings.append(f"{item}: invalid evidence; downgraded"); value, evidence = 0, ""
        elif not value: evidence = ""
        output[item] = {"v": value, "e": evidence}
    return output, warnings


def run_one(rid: str, arm: str, repeat: str, records: dict[str, Any], cards: dict[str, Any], items: tuple[str, ...]) -> None:
    path = OUT / "records" / f"{rid}_{arm}_{repeat}.json"
    if path.exists(): return
    response: Any = None
    try:
        response = common.completion(cfg(), messages(records[rid], cards, items, arm), schema(items))
        prediction, warnings = validate(common.parse_json(response.content), records[rid], items)
        row = {"id": rid, "arm": arm, "repeat": repeat, "success": True, "usage": response.usage, "raw_response": response.content, "prediction": prediction, "warnings": warnings}
    except Exception as exc:
        row = {"id": rid, "arm": arm, "repeat": repeat, "success": False, "error": f"{type(exc).__name__}: {exc}", "usage": {} if response is None else response.usage, "raw_response": "" if response is None else response.content}
    path.parent.mkdir(parents=True, exist_ok=True); common.write_json(path, row)


def score(pred: dict[str, Any], labels: dict[str, Any], ids: list[str], items: tuple[str, ...]) -> dict[str, Any]:
    rows = []
    for item in items:
        tp = fp = fn = 0
        for rid in ids:
            g, p = int(labels[rid][item]), int(pred[rid][item]["v"]); tp += g and p; fp += not g and p; fn += g and not p
        rows.append({"item": item, "tp": tp, "fp": fp, "fn": fn, "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0})
    return {"macro_f1": sum(x["f1"] for x in rows) / len(rows), "tp": sum(x["tp"] for x in rows), "fp": sum(x["fp"] for x in rows), "fn": sum(x["fn"] for x in rows), "per_item": rows}


def preflight() -> None:
    records, labels, cards = load(); items = target(cards); ids = cohort(records, labels, items)
    man = []
    for rid in ids:
        control, card = messages(records[rid], cards, items, "control"), messages(records[rid], cards, items, "card")
        # The common system prompt is an explicit invariant, rather than an
        # informal claim in the protocol.
        assert control[0] == card[0]
        man.append({"id": rid, "positive_targets": [x for x in items if labels[rid][x] == "1"], "system_sha256": common.sha256_text(control[0]["content"]), "control_user_sha256": common.sha256_text(control[1]["content"]), "card_user_sha256": common.sha256_text(card[1]["content"])})
    OUT.mkdir(parents=True, exist_ok=True); common.write_jsonl(OUT / "cohort.jsonl", man); common.write_json(OUT / "config.json", {"items": items, "cohort_size": len(ids), "repeats": 2, "calls": len(ids) * 4, "max_cost_usd": .40, "sole_treatment_variable": "legal essence block in user message", "success_gate": "both deltas > 0; total corrected cells > new errors; no target loses all TP"}); print(json.dumps({"status": "preflight_ok", "cohort": len(ids), "calls": len(ids)*4, "items": items}, ensure_ascii=False, indent=2))


def run(workers: int) -> None:
    records, labels, cards = load(); items = target(cards); ids = cohort(records, labels, items); jobs = [(rid, arm, rep) for rid in ids for arm in ("control", "card") for rep in ("r1", "r2")]
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(run_one, *job, records, cards, items) for job in jobs]
        for number, future in enumerate(as_completed(futures), 1): future.result(); print(f"completed={number}/{len(futures)}", flush=True)


def aggregate() -> None:
    records, labels, cards = load(); items = target(cards); ids = cohort(records, labels, items); report = {"experiment_id": "inc072_legal_essence_card_controlled_pilot", "items": items, "cohort_size": len(ids), "repeats": {}}
    for rep in ("r1", "r2"):
        arms = {}
        for arm in ("control", "card"):
            rows = [json.loads((OUT / "records" / f"{rid}_{arm}_{rep}.json").read_text()) for rid in ids]; bad = [x for x in rows if not x["success"]]
            arms[arm] = {"success": len(rows)-len(bad), "failures": len(bad), "cost_usd": sum(float(x.get("usage",{}).get("cost",0) or 0) for x in rows)}
            if not bad: arms[arm].update(score({x["id"]: x["prediction"] for x in rows}, labels, ids, items))
        if not arms["control"]["failures"] and not arms["card"]["failures"]: arms["delta_card_minus_control"] = arms["card"]["macro_f1"] - arms["control"]["macro_f1"]
        report["repeats"][rep] = arms
    common.write_json(OUT / "metrics.json", report); print(json.dumps(report, ensure_ascii=False, indent=2))


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--mode", required=True, choices=("preflight","run","aggregate")); parser.add_argument("--workers",type=int,default=16); args=parser.parse_args(); load_dotenv(ROOT/".env"); OUT.mkdir(parents=True,exist_ok=True)
    if args.mode == "preflight": preflight()
    elif args.mode == "run": run(args.workers)
    else: aggregate()

if __name__ == "__main__": main()
