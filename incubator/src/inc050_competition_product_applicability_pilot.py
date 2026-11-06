#!/usr/bin/env python3
"""Repeated, full-notice v10--v13 applicability fact-sheet pilot."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

import inc001_simple_joint24 as common
from inc048_source_fragment_ontology_audit import fragments


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "incubator/runs/inc050_competition_product_applicability_pilot"
ITEMS = ("v10", "v11", "v12", "v13")
ABSENCE = frozenset(("v10", "v11"))
ARMS = ("control_r1", "facts_r1", "control_r2", "facts_r2")
RESTRICTION = ("직접생산", "직생", "소기업", "소상공인", "중소기업", "경쟁제품", "판로지원", "예외")


def load_inputs() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, str]], dict[str, Any], dict[str, dict[str, Any]]]:
    data = ROOT / "data/raw/open"
    records = {row["id"]: row for row in common.read_jsonl_gz(data / "dev.jsonl.gz")}
    labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}
    table = json.loads((data / "data/항목표.json").read_text(encoding="utf-8"))["항목"]
    facts = {row["id"]: row for row in json.loads((ROOT / "incubator/data/derived/product_family_facts_v1.json").read_text(encoding="utf-8"))["records"]}
    return records, labels, table, facts


def source_candidates(record: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in fragments(record):
        if row["kind"] != "line" or not row["selectable"] or not any(cue in row["text"] for cue in RESTRICTION):
            continue
        rows.append({"candidate_id": f"{row['doc_id']}_{row['line_id']}", "doc_id": row["doc_id"], "doc_type": row["doc_type"], "source_line": row["text"]})
    return rows


def source_fact_sheet(record: dict[str, Any], fact: dict[str, Any]) -> str:
    product = fact["product_index_fact"]
    if product["status"] == "matched":
        lookup = "공식 경쟁제품 목록과 정확히 일치 확인된 세부품명: " + ", ".join(product["matched_product_names"])
    elif product["status"] == "not_matched":
        lookup = "관찰된 세부품명 코드는 있으나 공식 경쟁제품 목록의 정확 일치는 확인되지 않음"
    else:
        lookup = "정확한 세부품명 코드를 관찰하지 못하여 공식 목록 일치 여부를 확인할 수 없음"
    meta = record["meta"]
    return "\n".join([
        "[적용성 사실표 — 판정이나 예외 판단이 아님]",
        f"적용계약법(메타 원문): {meta.get('적용계약법', '')}",
        f"입찰추정가격(메타 원문): {meta.get('입찰추정가격', '')}",
        f"배정예산금액(메타 원문): {meta.get('배정예산금액', '')}",
        lookup,
        "이 사실표는 법적 결론이 아니다. 원문과 항목 정의를 함께 읽어 판단한다.",
    ])


def schema(record: dict[str, Any]) -> dict[str, Any]:
    ids = ["NONE", *[row["candidate_id"] for row in source_candidates(record)]]
    properties: dict[str, Any] = {}
    for item in ITEMS:
        if item in ABSENCE:
            properties[item] = {"type": "object", "additionalProperties": False, "required": ["위반여부"], "properties": {"위반여부": {"type": "integer", "enum": [0, 1]}}}
        else:
            properties[item] = {"type": "object", "additionalProperties": False, "required": ["위반여부", "evidence_id"], "properties": {"위반여부": {"type": "integer", "enum": [0, 1]}, "evidence_id": {"type": "string", "enum": ids}}}
    return {"type": "object", "additionalProperties": False, "required": list(ITEMS), "properties": properties}


def render_docs(record: dict[str, Any]) -> str:
    docs = sorted(record["docs"], key=lambda doc: (common.DOCUMENT_ORDER[doc["type"]], doc["doc_id"]))
    return "\n\n".join(f"[{doc['type']}:{doc['doc_id']}]\n{doc['text']}" for doc in docs)


def messages(record: dict[str, Any], table: dict[str, Any], facts: dict[str, dict[str, Any]], arm: str) -> list[dict[str, str]]:
    candidates = source_candidates(record)
    candidate_text = "\n".join(f"- {row['candidate_id']}: [{row['doc_type']}] {row['source_line']}" for row in candidates) or "- 선택 가능한 원문 제한표현 줄 없음"
    system = "\n".join([
        "당신은 공공입찰 공고의 법령 위반을 독립적으로 판정한다.",
        "메타데이터, 제공된 항목 정의, 그리고 모든 원문 문서를 함께 읽어 v10~v13을 각각 판단한다.",
        *[f"- {item}: {table[item]['항목명']}" for item in ITEMS],
        "일반적인 중소기업·소기업 문구만으로 위반을 단정하지 말고, 적용 제품·금액·계약법·원문 제한의 관계를 확인한다.",
        "v10과 v11은 부재탐지 항목이며 근거를 출력하지 않는다. v12와 v13이 1이면 선택 가능한 변경 없는 원문 줄 하나의 evidence_id를 고르고, 0이면 NONE을 고른다.",
        "후보가 없다는 사실은 0의 근거가 아니며, 전체 원문은 항상 최종 판단 근거다. JSON 객체 하나만 출력한다.",
    ])
    content = "[메타]\n" + json.dumps(record["meta"], ensure_ascii=False, sort_keys=True)
    if arm.startswith("facts_"):
        content += "\n\n" + source_fact_sheet(record, facts[record["id"]])
    content += "\n\n[전체 원문 문서]\n" + render_docs(record)
    content += "\n\n[v12/v13 선택 가능한 원문 제한표현 줄]\n" + candidate_text
    return [{"role": "system", "content": system}, {"role": "user", "content": content}]


def request_config() -> dict[str, Any]:
    return {"model": "google/gemma-4-26b-a4b-it", "api_url": "https://openrouter.ai/api/v1/chat/completions", "api_key_env": "OPENROUTER_API_KEY", "temperature": 0.0, "seed": 20260905, "max_tokens": 500, "timeout_seconds": 120, "request_retries": 1}


def cohort(records: dict[str, dict[str, Any]], labels: dict[str, dict[str, str]], facts: dict[str, dict[str, Any]]) -> list[str]:
    positives = {record_id for record_id in records if any(labels[record_id][item] == "1" for item in ITEMS)}
    strata: dict[tuple[str, int], list[str]] = {}
    for record_id, fact in facts.items():
        if record_id in positives:
            continue
        burden = min(2, sum(fact["cue_counts"].values()))
        strata.setdefault((fact["product_index_fact"]["status"], burden), []).append(record_id)
    selected = set(positives)
    for key in sorted(strata):
        selected.add(min(strata[key], key=lambda record_id: hashlib.sha256(f"inc050:{record_id}".encode()).hexdigest()))
    remainder = sorted((record_id for record_id in records if record_id not in selected), key=lambda record_id: hashlib.sha256(f"inc050:{record_id}".encode()).hexdigest())
    selected.update(remainder[:max(0, 36 - len(selected))])
    return sorted(selected)


def valid(payload: dict[str, Any], record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    candidate_map = {row["candidate_id"]: row for row in source_candidates(record)}
    output = {}
    for item in ITEMS:
        cell = payload.get(item)
        if not isinstance(cell, dict) or cell.get("위반여부") not in (0, 1):
            raise ValueError(f"invalid {item}")
        label = int(cell["위반여부"])
        if item in ABSENCE:
            output[item] = {"위반여부": label, "근거문구": ""}
            continue
        evidence_id = cell.get("evidence_id")
        if label and evidence_id in candidate_map:
            output[item] = {"위반여부": label, "근거문구": candidate_map[evidence_id]["source_line"], "evidence_id": evidence_id}
        elif not label and evidence_id == "NONE":
            output[item] = {"위반여부": 0, "근거문구": "", "evidence_id": "NONE"}
        else:
            output[item] = {"위반여부": 0, "근거문구": "", "evidence_id": "NONE", "downgraded": True}
    return output


def f1(tp: int, fp: int, fn: int) -> float:
    return 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0


def preflight() -> None:
    records, labels, table, facts = load_inputs()
    coverage = []
    for item in ("v12", "v13"):
        evidence = f"e{item[1:]}"
        for record_id, record in records.items():
            if labels[record_id][item] == "1" and labels[record_id][evidence]:
                covered = any(labels[record_id][evidence] in row["source_line"] for row in source_candidates(record))
                coverage.append({"id": record_id, "item": item, "covered": covered})
    missing = [row for row in coverage if not row["covered"]]
    ids = cohort(records, labels, facts)
    manifest = []
    for record_id in ids:
        for arm in ARMS:
            request = messages(records[record_id], table, facts, arm)
            manifest.append({"id": record_id, "arm": arm, "prompt_sha256": common.sha256_text(json.dumps(request, ensure_ascii=False, sort_keys=True)), "candidate_ids": [row["candidate_id"] for row in source_candidates(records[record_id])], "message_characters": sum(len(row["content"]) for row in request)})
    output = OUTPUT; output.mkdir(parents=True, exist_ok=True)
    common.write_json(output / "config.json", {"items": ITEMS, "arms": ARMS, "model": request_config(), "cohort_size": len(ids), "max_calls": len(manifest), "max_cost_usd": 0.40})
    common.write_json(output / "candidate_coverage.json", {"eligible": len(coverage), "covered": len(coverage) - len(missing), "missing": missing})
    common.write_jsonl(output / "cohort.jsonl", manifest)
    if missing:
        raise RuntimeError(f"candidate coverage gate failed: {len(missing)}")
    print(json.dumps({"status": "preflight_ok", "cohort_size": len(ids), "calls": len(manifest), "max_message_characters": max(row["message_characters"] for row in manifest), "candidate_coverage": len(coverage)}, ensure_ascii=False, indent=2))


def run_one(record_id: str, arm: str) -> None:
    records, _, table, facts = load_inputs(); path = OUTPUT / "records" / f"{record_id}_{arm}.json"; prior: dict[str, Any] | None = None
    if path.exists():
        prior = json.loads(path.read_text(encoding="utf-8"))
        if prior.get("success") or prior.get("recovery_attempted"):
            return
    response: Any = None
    try:
        response = common.completion(request_config(), messages(records[record_id], table, facts, arm), schema(records[record_id]))
        entry = {"id": record_id, "arm": arm, "success": True, "usage": response.usage, "raw_response": response.content, "judgment": valid(common.parse_json(response.content), records[record_id])}
    except Exception as exc:
        entry = {"id": record_id, "arm": arm, "success": False, "error": f"{type(exc).__name__}: {exc}", "usage": {} if response is None else response.usage, "raw_response": "" if response is None else response.content}
    if prior is not None:
        entry["recovery_attempted"] = True
        entry["initial_attempt"] = {key: prior.get(key) for key in ("success", "error", "usage", "raw_response")}
    path.parent.mkdir(parents=True, exist_ok=True); common.write_json(path, entry)


def run_all(workers: int) -> None:
    records, labels, _, facts = load_inputs(); jobs = [(record_id, arm) for record_id in cohort(records, labels, facts) for arm in ARMS]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_one, record_id, arm) for record_id, arm in jobs]
        for count, future in enumerate(as_completed(futures), 1):
            future.result(); print(f"completed={count}/{len(futures)}", flush=True)


def aggregate() -> None:
    records, labels, _, facts = load_inputs(); ids = cohort(records, labels, facts)
    report: dict[str, Any] = {"experiment_id": "inc050_competition_product_applicability_pilot", "cohort_size": len(ids), "requested_calls": len(ids) * len(ARMS), "arms": {}}
    for arm in ARMS:
        entries = [json.loads(path.read_text(encoding="utf-8")) for record_id in ids if (path := OUTPUT / "records" / f"{record_id}_{arm}.json").exists()]
        failures = [row for row in entries if not row["success"]]
        def incurred_cost(row: dict[str, Any]) -> float:
            current = float(row.get("usage", {}).get("cost", 0) or 0)
            initial = float(row.get("initial_attempt", {}).get("usage", {}).get("cost", 0) or 0)
            return current + initial
        arm_report = {"successful_calls": len(entries) - len(failures), "failure_count": len(failures), "reported_cost_usd": sum(incurred_cost(row) for row in entries)}
        if not failures and len(entries) == len(ids):
            per_item = []
            for item in ITEMS:
                tp = fp = fn = 0
                for row in entries:
                    gold, pred = int(labels[row["id"]][item]), row["judgment"][item]["위반여부"]
                    tp += gold and pred; fp += not gold and pred; fn += gold and not pred
                per_item.append({"item": item, "tp": tp, "fp": fp, "fn": fn, "f1": f1(tp, fp, fn)})
            arm_report["target_macro_f1"] = sum(row["f1"] for row in per_item) / len(per_item); arm_report["per_item"] = per_item
        report["arms"][arm] = arm_report
    deltas = {}
    for repeat in ("r1", "r2"):
        control, facts_arm = report["arms"][f"control_{repeat}"], report["arms"][f"facts_{repeat}"]
        if "target_macro_f1" in control and "target_macro_f1" in facts_arm:
            deltas[repeat] = facts_arm["target_macro_f1"] - control["target_macro_f1"]
    report["facts_minus_control"] = deltas
    common.write_json(OUTPUT / "metrics.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--mode", required=True, choices=("preflight", "run-all", "aggregate")); parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args(); load_dotenv(ROOT / ".env"); OUTPUT.mkdir(parents=True, exist_ok=True)
    if args.mode == "preflight": preflight()
    elif args.mode == "run-all": run_all(args.workers)
    else: aggregate()


if __name__ == "__main__":
    main()
