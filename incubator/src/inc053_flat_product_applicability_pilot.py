#!/usr/bin/env python3
"""INC-050 frozen product pilot with INC-052 flat response transport only."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

import inc001_simple_joint24 as common
import inc050_competition_product_applicability_pilot as base


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "incubator/runs/inc053_flat_product_applicability_pilot"


def schema(record: dict[str, Any]) -> dict[str, Any]:
    count = len(base.source_candidates(record))
    properties = {item: {"type": "integer", "enum": [0, 1]} for item in base.ITEMS}
    properties.update({item: {"type": "integer", "enum": [-1, *range(count)]} for item in ("e12", "e13")})
    return {"type": "object", "additionalProperties": False, "required": [*base.ITEMS, "e12", "e13"], "properties": properties}


def messages(record: dict[str, Any], table: dict[str, Any], facts: dict[str, dict[str, Any]], arm: str) -> list[dict[str, str]]:
    values = base.messages(record, table, facts, arm)
    values[0] = values[0].copy()
    values[0]["content"] = values[0]["content"].replace(
        "v10과 v11은 부재탐지 항목이며 근거를 출력하지 않는다. v12와 v13이 1이면 선택 가능한 변경 없는 원문 줄 하나의 evidence_id를 고르고, 0이면 NONE을 고른다.",
        "v10~v13은 각각 0 또는 1로 출력한다. v10/v11은 부재탐지 항목이다. v12/v13이 1이면 e12/e13에 아래 후보 목록의 0부터 시작하는 줄 번호를 출력하고, 0이면 -1을 출력한다.",
    ).replace("JSON 객체 하나만 출력한다.", "v10,v11,v12,v13,e12,e13의 flat JSON 객체 하나만 출력한다.")
    return values


def valid(payload: dict[str, Any], record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    candidates = base.source_candidates(record)
    result = {}
    for item in base.ITEMS:
        label = payload.get(item)
        if label not in (0, 1):
            raise ValueError(f"invalid {item}")
        if item in base.ABSENCE:
            result[item] = {"위반여부": int(label), "근거문구": ""}
            continue
        index = payload.get(f"e{item[1:]}")
        if label and isinstance(index, int) and 0 <= index < len(candidates):
            result[item] = {"위반여부": 1, "근거문구": candidates[index]["source_line"], "evidence_index": index}
        elif not label and index == -1:
            result[item] = {"위반여부": 0, "근거문구": "", "evidence_index": -1}
        else:
            result[item] = {"위반여부": 0, "근거문구": "", "evidence_index": -1, "downgraded": True}
    return result


def preflight() -> None:
    records, labels, table, facts = base.load_inputs(); ids = base.cohort(records, labels, facts)
    coverage = []
    for item in ("v12", "v13"):
        evidence = f"e{item[1:]}"
        for record_id, record in records.items():
            if labels[record_id][item] == "1" and labels[record_id][evidence]:
                coverage.append({"id": record_id, "item": item, "covered": any(labels[record_id][evidence] in row["source_line"] for row in base.source_candidates(record))})
    missing = [row for row in coverage if not row["covered"]]
    manifest = []
    for record_id in ids:
        for arm in base.ARMS:
            request = messages(records[record_id], table, facts, arm)
            manifest.append({"id": record_id, "arm": arm, "prompt_sha256": common.sha256_text(json.dumps(request, ensure_ascii=False, sort_keys=True)), "candidate_count": len(base.source_candidates(records[record_id])), "message_characters": sum(len(row["content"]) for row in request)})
    OUTPUT.mkdir(parents=True, exist_ok=True)
    common.write_json(OUTPUT / "config.json", {"experiment_id": "inc053_flat_product_applicability_pilot", "predecessor": "inc050", "only_changed_variable": "flat binary and evidence-index response transport", "items": base.ITEMS, "arms": base.ARMS, "model": base.request_config(), "max_calls": len(manifest), "max_cost_usd": .40})
    common.write_json(OUTPUT / "candidate_coverage.json", {"eligible": len(coverage), "covered": len(coverage) - len(missing), "missing": missing})
    common.write_jsonl(OUTPUT / "cohort.jsonl", manifest)
    if missing: raise RuntimeError(f"candidate coverage gate failed: {len(missing)}")
    print(json.dumps({"status": "preflight_ok", "cohort_size": len(ids), "calls": len(manifest), "candidate_coverage": len(coverage), "max_message_characters": max(row["message_characters"] for row in manifest)}, ensure_ascii=False, indent=2))


def run_one(record_id: str, arm: str) -> None:
    records, _, table, facts = base.load_inputs(); path = OUTPUT / "records" / f"{record_id}_{arm}.json"
    if path.exists(): return
    response: Any = None
    try:
        response = common.completion(base.request_config(), messages(records[record_id], table, facts, arm), schema(records[record_id]))
        entry = {"id": record_id, "arm": arm, "success": True, "usage": response.usage, "raw_response": response.content, "judgment": valid(common.parse_json(response.content), records[record_id])}
    except Exception as exc:
        entry = {"id": record_id, "arm": arm, "success": False, "error": f"{type(exc).__name__}: {exc}", "usage": {} if response is None else response.usage, "raw_response": "" if response is None else response.content}
    path.parent.mkdir(parents=True, exist_ok=True); common.write_json(path, entry)


def run_all(workers: int) -> None:
    records, labels, _, facts = base.load_inputs(); jobs = [(record_id, arm) for record_id in base.cohort(records, labels, facts) for arm in base.ARMS]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_one, record_id, arm) for record_id, arm in jobs]
        for count, future in enumerate(as_completed(futures), 1): future.result(); print(f"completed={count}/{len(futures)}", flush=True)


def aggregate() -> None:
    records, labels, _, facts = base.load_inputs(); ids = base.cohort(records, labels, facts); report: dict[str, Any] = {"experiment_id": "inc053_flat_product_applicability_pilot", "cohort_size": len(ids), "requested_calls": len(ids) * len(base.ARMS), "arms": {}}
    for arm in base.ARMS:
        entries = [json.loads(path.read_text(encoding="utf-8")) for record_id in ids if (path := OUTPUT / "records" / f"{record_id}_{arm}.json").exists()]
        failures = [row for row in entries if not row["success"]]; current = {"successful_calls": len(entries) - len(failures), "failure_count": len(failures), "reported_cost_usd": sum(float(row.get("usage", {}).get("cost", 0) or 0) for row in entries)}
        if not failures and len(entries) == len(ids):
            per_item = []
            for item in base.ITEMS:
                tp = fp = fn = 0
                for row in entries:
                    gold, pred = int(labels[row["id"]][item]), row["judgment"][item]["위반여부"]
                    tp += gold and pred; fp += not gold and pred; fn += gold and not pred
                per_item.append({"item": item, "tp": tp, "fp": fp, "fn": fn, "f1": base.f1(tp, fp, fn)})
            current["target_macro_f1"] = sum(row["f1"] for row in per_item) / len(per_item); current["per_item"] = per_item
        report["arms"][arm] = current
    report["facts_minus_control"] = {repeat: report["arms"][f"facts_{repeat}"]["target_macro_f1"] - report["arms"][f"control_{repeat}"]["target_macro_f1"] for repeat in ("r1", "r2") if "target_macro_f1" in report["arms"][f"facts_{repeat}"] and "target_macro_f1" in report["arms"][f"control_{repeat}"]}
    common.write_json(OUTPUT / "metrics.json", report); print(json.dumps(report, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--mode", required=True, choices=("preflight", "run-all", "aggregate")); parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args(); load_dotenv(ROOT / ".env"); OUTPUT.mkdir(parents=True, exist_ok=True)
    if args.mode == "preflight": preflight()
    elif args.mode == "run-all": run_all(args.workers)
    else: aggregate()


if __name__ == "__main__": main()
