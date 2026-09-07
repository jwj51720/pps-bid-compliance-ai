#!/usr/bin/env python3
"""INC-066: optional source-line attention before a full-notice judgment."""

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
import inc060_line_id_joint24_pilot as line_base


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "incubator/runs/inc066_attention_proposal_topology_pilot"


def config(max_tokens: int) -> dict[str, Any]:
    return {
        "model": "google/gemma-4-26b-a4b-it",
        "api_url": "https://openrouter.ai/api/v1/chat/completions",
        "api_key_env": "OPENROUTER_API_KEY",
        "temperature": 0.0,
        "seed": 20260905,
        "max_tokens": max_tokens,
        "timeout_seconds": 120,
        "request_retries": 1,
    }


def load() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, str]], dict[str, Any]]:
    data = ROOT / "data/raw/open"
    records = {row["id"]: row for row in common.read_jsonl_gz(data / "dev.jsonl.gz")}
    labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}
    table = json.loads((data / "data/항목표.json").read_text(encoding="utf-8"))["항목"]
    return records, labels, table


def seed_cohort(records: dict[str, dict[str, Any]], labels: dict[str, dict[str, str]]) -> list[str]:
    """Exact positive-cover seed selection inherited from INC-054."""
    selected = set()
    for item in common.ITEMS:
        positives = [record_id for record_id in records if labels[record_id][item] == "1"]
        selected.add(min(positives, key=lambda record_id: hashlib.sha256(f"inc054:{item}:{record_id}".encode()).hexdigest()))
    if not all(any(labels[record_id][item] == "1" for record_id in selected) for item in common.ITEMS):
        raise RuntimeError("positive-cover cohort lost an item")
    return sorted(selected)


def label_schema() -> dict[str, Any]:
    return {"type": "object", "additionalProperties": False, "required": list(common.ITEMS), "properties": {item: {"type": "integer", "enum": [0, 1]} for item in common.ITEMS}}


def locator_schema(record: dict[str, Any]) -> dict[str, Any]:
    ids = [-1, *range(len(line_base.lines(record)))]
    fields = [f"a{item[1:]}" for item in common.ITEMS]
    return {"type": "object", "additionalProperties": False, "required": fields, "properties": {field: {"type": "integer", "enum": ids} for field in fields}}


def final_messages(record: dict[str, Any], table: dict[str, Any], attention: dict[str, int] | None = None) -> list[dict[str, str]]:
    system = "\n".join([
        "당신은 공공입찰 공고의 법령 위반을 독립적으로 판정한다. 메타와 모든 원문 문서를 읽어 각 항목을 0 또는 1로 판단한다.",
        "키워드, 안내 힌트, 또는 단일 문구만으로 단정하지 말고 법률상 적용 조건과 예외를 함께 검토한다. 불확실하면 0으로 둔다. JSON 객체 하나만 출력한다.",
        *[f"- {item}: {table[item]['항목명']}" for item in common.ITEMS],
    ])
    parts = [
        "[공고 ID]\n" + record["id"],
        "[메타]\n" + json.dumps(record["meta"], ensure_ascii=False, sort_keys=True),
        "[전체 문서]\n" + context.full_context(record),
    ]
    if attention is not None:
        source_lines = line_base.lines(record)
        hints = []
        for item in common.ITEMS:
            index = attention[item]
            hint = "관련 원문 줄을 찾지 못함" if index == -1 else source_lines[index]
            hints.append(f"[{item}] {hint}")
        parts.append("[독립 탐색기의 주의용 원문 줄]\n이 목록은 오류가 있을 수 있는 탐색 보조일 뿐, 증거도 라벨 조건도 아니다. 반드시 전체 원문과 메타를 우선해 독립적으로 판단한다.\n" + "\n".join(hints))
    return [{"role": "system", "content": system}, {"role": "user", "content": "\n\n".join(parts)}]


def locator_messages(record: dict[str, Any], table: dict[str, Any]) -> list[dict[str, str]]:
    source_lines = line_base.lines(record)
    system = "\n".join([
        "당신은 판정을 하지 않는 원문 탐색기다. 각 항목에 대해 법률상 적용 조건, 예외 또는 위반 여부를 검토할 때 가장 중요한 원문 줄 하나를 고른다.",
        "위반 여부, 인용문, 해설을 출력하지 말며, 관련된 원문 줄을 찾을 수 없을 때만 -1을 쓴다. JSON 객체 하나만 출력한다.",
        *[f"- a{item[1:]}: {item} ({table[item]['항목명']})" for item in common.ITEMS],
    ])
    user = "\n\n".join([
        "[메타]\n" + json.dumps(record["meta"], ensure_ascii=False, sort_keys=True),
        "[번호가 부여된 전체 원문 줄]\n" + "\n".join(f"[L{index}] {line}" for index, line in enumerate(source_lines)),
    ])
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def parse_labels(payload: dict[str, Any]) -> dict[str, int]:
    if set(payload) != set(common.ITEMS) or any(payload[item] not in (0, 1) for item in common.ITEMS):
        raise ValueError("invalid flat label object")
    return {item: int(payload[item]) for item in common.ITEMS}


def run_control(record_id: str, repeat: str, records: dict[str, dict[str, Any]], table: dict[str, Any]) -> None:
    path = OUT / "control" / f"{record_id}_{repeat}.json"
    if path.exists():
        return
    response: Any = None
    try:
        messages = final_messages(records[record_id], table)
        response = common.completion(config(128), messages, label_schema())
        entry = {"id": record_id, "repeat": repeat, "success": True, "prediction": parse_labels(common.parse_json(response.content)), "usage": response.usage, "raw_response": response.content, "prompt_sha256": common.sha256_text(json.dumps(messages, ensure_ascii=False, sort_keys=True))}
    except Exception as exc:
        entry = {"id": record_id, "repeat": repeat, "success": False, "error": f"{type(exc).__name__}: {exc}", "usage": {} if response is None else response.usage, "raw_response": "" if response is None else response.content}
    path.parent.mkdir(parents=True, exist_ok=True)
    common.write_json(path, entry)


def run_treatment(record_id: str, repeat: str, records: dict[str, dict[str, Any]], table: dict[str, Any]) -> None:
    path = OUT / "treatment" / f"{record_id}_{repeat}.json"
    if path.exists():
        return
    locator_response: Any = None
    final_response: Any = None
    try:
        record = records[record_id]
        locator_prompt = locator_messages(record, table)
        locator_response = common.completion(config(512), locator_prompt, locator_schema(record))
        locator_payload = common.parse_json(locator_response.content)
        expected = {f"a{item[1:]}" for item in common.ITEMS}
        if set(locator_payload) != expected:
            raise ValueError("invalid locator fields")
        count = len(line_base.lines(record))
        attention = {item: locator_payload[f"a{item[1:]}"] for item in common.ITEMS}
        if any(not isinstance(index, int) or index < -1 or index >= count for index in attention.values()):
            raise ValueError("invalid locator ID")
        final_prompt = final_messages(record, table, attention)
        final_response = common.completion(config(128), final_prompt, label_schema())
        entry = {"id": record_id, "repeat": repeat, "success": True, "attention": attention, "prediction": parse_labels(common.parse_json(final_response.content)), "locator_usage": locator_response.usage, "final_usage": final_response.usage, "locator_raw_response": locator_response.content, "final_raw_response": final_response.content, "locator_prompt_sha256": common.sha256_text(json.dumps(locator_prompt, ensure_ascii=False, sort_keys=True)), "final_prompt_sha256": common.sha256_text(json.dumps(final_prompt, ensure_ascii=False, sort_keys=True))}
    except Exception as exc:
        entry = {"id": record_id, "repeat": repeat, "success": False, "error": f"{type(exc).__name__}: {exc}", "locator_usage": {} if locator_response is None else locator_response.usage, "final_usage": {} if final_response is None else final_response.usage, "locator_raw_response": "" if locator_response is None else locator_response.content, "final_raw_response": "" if final_response is None else final_response.content}
    path.parent.mkdir(parents=True, exist_ok=True)
    common.write_json(path, entry)


def score(predictions: dict[str, dict[str, int]], labels: dict[str, dict[str, str]], cohort: list[str]) -> tuple[float, list[dict[str, Any]], int, int, int]:
    per_item = []
    totals = [0, 0, 0]
    for item in common.ITEMS:
        tp = fp = fn = 0
        for record_id in cohort:
            gold, prediction = int(labels[record_id][item]), predictions[record_id][item]
            tp += gold == prediction == 1
            fp += gold == 0 and prediction == 1
            fn += gold == 1 and prediction == 0
        totals[0] += tp
        totals[1] += fp
        totals[2] += fn
        per_item.append({"item": item, "tp": tp, "fp": fp, "fn": fn, "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0})
    return sum(row["f1"] for row in per_item) / len(per_item), per_item, *totals


def aggregate(records: dict[str, dict[str, Any]], labels: dict[str, dict[str, str]]) -> None:
    cohort = seed_cohort(records, labels)
    report: dict[str, Any] = {"experiment_id": "inc066_attention_proposal_topology_pilot", "cohort_size": len(cohort), "repeats": {}}
    all_cost = 0.0
    for repeat in ("r1", "r2"):
        control = [json.loads((OUT / "control" / f"{record_id}_{repeat}.json").read_text(encoding="utf-8")) for record_id in cohort]
        treatment = [json.loads((OUT / "treatment" / f"{record_id}_{repeat}.json").read_text(encoding="utf-8")) for record_id in cohort]
        control_failures = [row for row in control if not row["success"]]
        treatment_failures = [row for row in treatment if not row["success"]]
        all_cost += sum(float(row.get("usage", {}).get("cost", 0) or 0) for row in control)
        all_cost += sum(float(row.get("locator_usage", {}).get("cost", 0) or 0) + float(row.get("final_usage", {}).get("cost", 0) or 0) for row in treatment)
        row: dict[str, Any] = {"control_success": len(control) - len(control_failures), "treatment_success": len(treatment) - len(treatment_failures), "control_failures": control_failures, "treatment_failures": treatment_failures}
        if not control_failures and not treatment_failures:
            control_score, control_items, control_tp, control_fp, control_fn = score({entry["id"]: entry["prediction"] for entry in control}, labels, cohort)
            treatment_score, treatment_items, treatment_tp, treatment_fp, treatment_fn = score({entry["id"]: entry["prediction"] for entry in treatment}, labels, cohort)
            changed = []
            for record_id in cohort:
                for item in common.ITEMS:
                    before = next(entry for entry in control if entry["id"] == record_id)["prediction"][item]
                    after = next(entry for entry in treatment if entry["id"] == record_id)["prediction"][item]
                    if before != after:
                        gold = int(labels[record_id][item])
                        changed.append({"id": record_id, "item": item, "gold": gold, "control": before, "treatment": after, "correction": after == gold and before != gold})
            row.update({"control_macro_f1": control_score, "treatment_macro_f1": treatment_score, "delta": treatment_score - control_score, "control": {"tp": control_tp, "fp": control_fp, "fn": control_fn, "per_item": control_items}, "treatment": {"tp": treatment_tp, "fp": treatment_fp, "fn": treatment_fn, "per_item": treatment_items}, "changed_cells": changed, "corrected_cells": sum(cell["correction"] for cell in changed), "new_errors": sum(not cell["correction"] for cell in changed)})
        report["repeats"][repeat] = row
    if all_cost > 0.50:
        raise RuntimeError(f"reported cost ceiling exceeded: {all_cost:.6f}")
    report["reported_cost_usd"] = all_cost
    report["advance_gate"] = {"both_scored": all("delta" in row for row in report["repeats"].values()), "both_positive": all(row.get("delta", 0) > 0 for row in report["repeats"].values()), "no_repeat_net_error_increase": all(row.get("corrected_cells", 0) > row.get("new_errors", 0) for row in report["repeats"].values())}
    report["advance_gate"]["pass"] = all(report["advance_gate"].values())
    common.write_json(OUT / "report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("preflight", "run", "aggregate"))
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    records, labels, table = load()
    cohort = seed_cohort(records, labels)
    OUT.mkdir(parents=True, exist_ok=True)
    if args.mode == "preflight":
        manifest = []
        for record_id in cohort:
            locator = locator_messages(records[record_id], table)
            control = final_messages(records[record_id], table)
            manifest.append({"id": record_id, "locator_characters": sum(len(row["content"]) for row in locator), "control_characters": sum(len(row["content"]) for row in control), "line_count": len(line_base.lines(records[record_id])), "locator_prompt_sha256": common.sha256_text(json.dumps(locator, ensure_ascii=False, sort_keys=True)), "control_prompt_sha256": common.sha256_text(json.dumps(control, ensure_ascii=False, sort_keys=True))})
        common.write_jsonl(OUT / "manifest.jsonl", manifest)
        common.write_json(OUT / "config.json", {"protocol": "incubator/docs/inc066_attention_proposal_topology_protocol.md", "cohort": cohort, "cohort_size": len(cohort), "repeats": 2, "max_calls": len(cohort) * 2 * 3, "max_cost_usd": 0.50, "control": config(128), "locator": config(512), "source_sha256": {"dev": common.sha256_file(ROOT / "data/raw/open/dev.jsonl.gz"), "labels": common.sha256_file(ROOT / "data/raw/open/dev_labels.csv"), "item_table": common.sha256_file(ROOT / "data/raw/open/data/항목표.json")}})
        print(json.dumps({"status": "preflight_ok", "cohort_size": len(cohort), "calls": len(cohort) * 2 * 3, "max_locator_characters": max(row["locator_characters"] for row in manifest), "max_control_characters": max(row["control_characters"] for row in manifest), "max_lines": max(row["line_count"] for row in manifest)}, ensure_ascii=False, indent=2))
        return
    if args.mode == "run":
        jobs = []
        for repeat in ("r1", "r2"):
            jobs.extend(("control", record_id, repeat) for record_id in cohort)
            jobs.extend(("treatment", record_id, repeat) for record_id in cohort)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(run_control if arm == "control" else run_treatment, record_id, repeat, records, table): (arm, record_id, repeat) for arm, record_id, repeat in jobs}
            for completed, future in enumerate(as_completed(futures), 1):
                future.result()
                print(f"completed={completed}/{len(futures)}", flush=True)
        return
    aggregate(records, labels)


if __name__ == "__main__":
    main()
