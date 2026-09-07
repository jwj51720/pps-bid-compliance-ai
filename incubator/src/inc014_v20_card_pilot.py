#!/usr/bin/env python3
"""Paired, v20-only Gemma pilot: source-only control versus law fact card."""

from __future__ import annotations

import argparse
import fcntl
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from transformers import AutoTokenizer

import inc001_simple_joint24 as common
from inc007_token_admission_profile import count_messages


V20_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["v20"],
    "properties": {"v20": {"type": "integer", "enum": [0, 1]}},
}
SYSTEM = """당신은 공공 입찰의 v20만 점검한다. 내부적으로 원문과 제공 사실을 검토한 뒤 JSON만 출력한다.\n
v20=1은 해당 소프트웨어사업에 대해 입찰공고문 또는 제안요청서에 대기업 참여제한 하한제도의 적용 여부와 적용 근거를 명시해야 하나, 원문 전체를 검토해 그 명시가 없다고 판단한 경우다.\n
소프트웨어사업 여부, 사업금액, 분리ㆍ분담이행, 공공기관 또는 예외 사실을 실제 원문과 제공 사실로 검토한다. 키워드 하나, 메타의 미입력, 금액 하나만으로 v20=1을 결정하지 않는다. 판단이 불명확하면 0이다.\n
출력 형식: {\"v20\": 0 또는 1}"""


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()


def full_documents(record: dict[str, Any]) -> str:
    documents = sorted(record["docs"], key=lambda doc: (common.DOCUMENT_ORDER[doc["type"]], doc["doc_id"]))
    return "\n\n".join(f"[{doc['type']}:{doc['doc_id']}]\n{doc['text']}" for doc in documents)


def card_for_prompt(card: dict[str, Any]) -> str:
    facts = card["legal_facts_verbatim"]
    keep = {
        "threshold_rule": facts["threshold_rule"],
        "non_software_split_exception": facts["non_software_split_exception"],
        "amount_and_long_contract_rules": facts["amount_and_long_contract_rules"],
        "notice_or_rfp_disclosure_duty": facts["notice_or_rfp_disclosure_duty"],
        "appendix_1_thresholds": facts["appendix_1_thresholds"],
        "exception_request_context": facts["exception_request_context"],
        "review_contract": card["review_contract"],
    }
    return "[Organizer law fact card; not notice evidence]\n" + json.dumps(keep, ensure_ascii=False)


def build_messages(record: dict[str, Any], card_context: str | None) -> list[dict[str, str]]:
    body = [
        f"[공고 ID]\n{record['id']}",
        "[나라장터 입력 메타]\n" + json.dumps(record["meta"], ensure_ascii=False, sort_keys=True),
    ]
    if card_context:
        body.append(card_context)
    body.append("[전체 문서 원문]\n" + full_documents(record))
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": "\n\n".join(body)}]


def select_cohort(
    records: dict[str, dict[str, Any]], labels: dict[str, dict[str, str]], manifest: list[dict[str, Any]], negative_count: int
) -> tuple[list[str], dict[str, Any]]:
    facts = {row["id"]: row for row in manifest}
    positives = sorted(record_id for record_id, label in labels.items() if label["v20"] == "1")
    eligible = [
        record_id for record_id, label in labels.items()
        if label["v20"] == "0"
        and facts[record_id]["metadata_applicability_status"] == "unknown"
        and facts[record_id]["cue_counts"].get("sw_applicability", 0) > 0
    ]
    # Deterministic nearest-neighbour matching on raw estimated-price scale,
    # without using any negative-document content or model outputs.
    available = set(eligible)
    selected: list[str] = []
    for positive_id in positives:
        target = int(records[positive_id]["meta"].get("입찰추정가격") or 0)
        candidate = min(available, key=lambda record_id: (abs(int(records[record_id]["meta"].get("입찰추정가격") or 0) - target), record_id))
        selected.append(candidate)
        available.remove(candidate)
        if len(selected) == negative_count:
            break
    for candidate in sorted(available, key=lambda record_id: (int(records[record_id]["meta"].get("입찰추정가격") or 0), record_id)):
        if len(selected) == negative_count:
            break
        selected.append(candidate)
    ids = sorted([*positives, *selected])
    return ids, {"positive_ids": positives, "matched_negative_ids": sorted(selected), "eligible_negative_count": len(eligible)}


def parse_v20(content: str) -> int:
    value = common.parse_json(content).get("v20")
    if value not in (0, 1):
        raise ValueError("missing or invalid v20")
    return int(value)


def score(entries: list[dict[str, Any]], labels: dict[str, dict[str, str]]) -> dict[str, Any]:
    tp = sum(entry["prediction"] == 1 and labels[entry["id"]]["v20"] == "1" for entry in entries)
    fp = sum(entry["prediction"] == 1 and labels[entry["id"]]["v20"] == "0" for entry in entries)
    fn = sum(entry["prediction"] == 0 and labels[entry["id"]]["v20"] == "1" for entry in entries)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="incubator/configs/inc014_v20_card_pilot.json")
    parser.add_argument("--mode", choices=("preflight", "run"), default="preflight")
    args = parser.parse_args()
    root = common.repo_root()
    config = json.loads((root / args.config).read_text(encoding="utf-8"))
    load_dotenv(root / ".env")
    output = root / "incubator/runs" / config["experiment_id"]
    output.mkdir(parents=True, exist_ok=True)
    lock = (output / ".run.lock").open("w", encoding="utf-8")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    data_root = root / config["data_root"]
    records = {row["id"]: row for row in common.read_jsonl_gz(data_root / "dev.jsonl.gz")}
    labels = {row["id"]: row for row in common.read_csv(data_root / "dev_labels.csv")}
    manifest = read_jsonl(root / config["audit_manifest_path"])
    card = json.loads((root / config["card_path"]).read_text(encoding="utf-8"))
    ids, cohort = select_cohort(records, labels, manifest, config["negative_count"])
    card_context = card_for_prompt(card)
    tokenizer = AutoTokenizer.from_pretrained(config["model_tokenizer"])
    requests: list[dict[str, Any]] = []
    budget = config["max_model_len"] - config["output_reserve_tokens"]
    for record_id in ids:
        for policy, context in (("control", None), ("law_card", card_context)):
            messages = build_messages(records[record_id], context)
            tokens = count_messages(tokenizer, messages)
            if tokens > budget:
                raise RuntimeError(f"prompt exceeds exact budget: {record_id} {policy} {tokens}>{budget}")
            requests.append({"id": record_id, "policy": policy, "messages": messages, "prompt_tokens": tokens, "prompt_sha256": common.sha256_text(json.dumps(messages, ensure_ascii=False, sort_keys=True))})
    plan = {
        "experiment_id": config["experiment_id"], "hypothesis": "a source-grounded v20 law card improves v20 F1 without a material false-positive increase",
        "changed_variable": "fixed legal fact card only", "cohort": cohort, "cohort_count": len(ids), "request_count": len(requests),
        "full_notice_context": True, "prompt_token_budget": budget, "prompt_token_max": max(row["prompt_tokens"] for row in requests),
        "success_gate": "law_card TP >= 3 of 5; law_card F1 > control F1; law_card FP <= control FP + 1", "max_cost_usd": config["max_cost_usd"],
        "source_sha256": {"dev": common.sha256_file(data_root / "dev.jsonl.gz"), "labels": common.sha256_file(data_root / "dev_labels.csv"), "card": common.sha256_file(root / config["card_path"])},
    }
    common.write_json(output / "config.json", config)
    common.write_json(output / "plan.json", plan)
    common.write_jsonl(output / "inputs.jsonl", requests)
    if args.mode == "preflight":
        print(json.dumps({"status": "preflight_ok", **plan}, ensure_ascii=False, indent=2))
        return
    if len(requests) > config["max_requests"]:
        raise RuntimeError("request ceiling exceeded")
    checkpoint = output / "checkpoint.jsonl"
    done = {(row["id"], row["policy"]): row for row in read_jsonl(checkpoint)} if checkpoint.exists() else {}
    remaining = [row for row in requests if (row["id"], row["policy"]) not in done]

    def run(request: dict[str, Any]) -> dict[str, Any]:
        response: dict[str, Any] = {"raw_response": "", "model": config["model"], "usage": {}, "latency_seconds": 0.0, "finish_reason": None, "success": False}
        try:
            completion = common.completion(config, request["messages"], V20_SCHEMA)
            response.update({"raw_response": completion.content, "model": completion.model, "usage": completion.usage, "latency_seconds": completion.latency_seconds, "finish_reason": completion.finish_reason})
            prediction = parse_v20(completion.content)
            response["success"] = True
            warning = None
        except Exception as exc:  # checkpoint failure as a zero, never hide it
            prediction, warning = 0, f"failure:{type(exc).__name__}:{str(exc)[:240]}"
        return {"id": request["id"], "policy": request["policy"], "prediction": prediction, "response": response, "warning": warning}

    with ThreadPoolExecutor(max_workers=config["concurrency"]) as executor:
        futures = [executor.submit(run, request) for request in remaining]
        for index, future in enumerate(as_completed(futures), 1):
            row = future.result()
            done[(row["id"], row["policy"])] = row
            append_jsonl(checkpoint, row)
            print(f"[{index}/{len(remaining)}] {row['policy']} {row['id']}", flush=True)
    entries = list(done.values())
    by_policy = {policy: sorted([row for row in entries if row["policy"] == policy], key=lambda row: row["id"]) for policy in ("control", "law_card")}
    metrics = {"experiment_id": config["experiment_id"], "request_count": len(entries), "successful_request_count": sum(row["response"]["success"] for row in entries), "reported_cost_usd": sum(float(row["response"]["usage"].get("cost", 0) or 0) for row in entries), "policies": {policy: score(rows, labels) for policy, rows in by_policy.items()}}
    control, treatment = metrics["policies"]["control"], metrics["policies"]["law_card"]
    metrics["delta_law_card_minus_control"] = {key: treatment[key] - control[key] for key in ("tp", "fp", "fn", "precision", "recall", "f1")}
    metrics["success_gate_pass"] = treatment["tp"] >= 3 and treatment["f1"] > control["f1"] and treatment["fp"] <= control["fp"] + 1
    common.write_jsonl(output / "responses.jsonl", [{"id": row["id"], "policy": row["policy"], **row["response"], "warning": row["warning"]} for row in entries])
    common.write_jsonl(output / "predictions.jsonl", [{"id": row["id"], "policy": row["policy"], "v20": row["prediction"]} for row in entries])
    common.write_json(output / "metrics.json", metrics)
    print(json.dumps({"status": "complete", "metrics": metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
