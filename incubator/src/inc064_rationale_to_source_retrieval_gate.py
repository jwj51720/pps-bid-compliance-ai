#!/usr/bin/env python3
"""Audit whether a full-notice legal memo improves source-line retrieval."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

import inc001_simple_joint24 as common
import inc018_global_context_architecture as context
import inc049_criterion_to_source_line_retrieval_audit as retrieval
from inc048_source_fragment_ontology_audit import fragments


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "incubator/runs/inc064_rationale_to_source_retrieval_gate"
ITEMS = ("v4", "v7")
RANKS = (1, 3, 5, 10, 20)


def config() -> dict[str, Any]:
    return {
        "model": "google/gemma-4-26b-a4b-it",
        "api_url": "https://openrouter.ai/api/v1/chat/completions",
        "api_key_env": "OPENROUTER_API_KEY",
        "temperature": 0.0,
        "seed": 20260905,
        "max_tokens": 256,
        "timeout_seconds": 120,
        "request_retries": 1,
    }


def embedding_config() -> dict[str, Any]:
    return {
        "model": "baai/bge-m3",
        "api_url": "https://openrouter.ai/api/v1/embeddings",
        "api_key_env": "OPENROUTER_API_KEY",
        "timeout_seconds": 120,
        "request_retries": 1,
    }


def load() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, str]], dict[str, Any], dict[str, str]]:
    data = ROOT / "data/raw/open"
    records = {row["id"]: row for row in common.read_jsonl_gz(data / "dev.jsonl.gz")}
    labels = {row["id"]: row for row in common.read_csv(data / "dev_labels.csv")}
    table = json.loads((data / "data/항목표.json").read_text(encoding="utf-8"))["항목"]
    laws = {path.name: path.read_text(encoding="utf-8") for path in (data / "data/법령패키지/법령").glob("*.txt")}
    return records, labels, table, laws


def law_text(item: str, definition: dict[str, Any], laws: dict[str, str]) -> str:
    """Use only organizer-provided law references; retain complete matched units."""
    references = "\n".join(str(definition.get(key, "")) for key in ("국가계약법", "지방계약법", "비고"))
    national_rules = laws["국가를 당사자로 하는 계약에 관한 법률 시행규칙.txt"]
    local_rules = laws["지방자치단체를 당사자로 하는 계약에 관한 법률 시행규칙.txt"]
    national_25 = national_rules[national_rules.index("제25조(제한경쟁입찰의 제한기준)"):national_rules.index("제26조(", national_rules.index("제25조(제한경쟁입찰의 제한기준)"))]
    local_25 = local_rules[local_rules.index("제25조(제한입찰의 제한기준)"):local_rules.index("제26조(", local_rules.index("제25조(제한입찰의 제한기준)"))]
    if item == "v4":
        source = laws["(계약예규) 정부 입찰·계약 집행기준.txt"]
        start = source.index("제5조(제한기준)")
        end = source.index("제5조의2", start)
        return "\n\n".join([references, "[국가계약 집행기준 제5조]\n" + source[start:end], "[국가계약 시행규칙 제25조]\n" + national_25, "[지방계약 시행규칙 제25조]\n" + local_25])
    if item == "v7":
        local_guideline = laws["지방자치단체 입찰 및 계약 집행기준.txt"]
        start = local_guideline.index("제3절 수의계약 대상과 운영요령")
        end = local_guideline.index("4) 지역사업자는", start)
        return "\n\n".join([references, "[국가계약 시행규칙 제25조]\n" + national_25, "[지방계약 시행규칙 제25조]\n" + local_25, "[지방 수의계약 운영요령]\n" + local_guideline[start:end]])
    raise ValueError(item)


def jobs(records: dict[str, dict[str, Any]], labels: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    return [
        {"id": record_id, "item": item, "evidence": labels[record_id][f"e{item[1:]}"]}
        for record_id in sorted(records)
        for item in ITEMS
        if labels[record_id][item] == "1" and labels[record_id][f"e{item[1:]}"]
    ]


def messages(record: dict[str, Any], item: str, definition: dict[str, Any], legal_text: str) -> list[dict[str, str]]:
    system = (
        "당신은 공공입찰 법령 검토를 위한 원문 탐색 메모를 작성한다. "
        "아래 한 항목의 법률상 쟁점을 공고 원문에서 다시 찾을 수 있도록 사실과 적용 조건만 간결히 적는다. "
        "위반 여부(0/1), 인용문, 줄 번호, 문서 ID를 출력하지 말고, 원문에 없는 사실을 단정하지 말라. "
        "JSON 객체 하나만 출력한다."
    )
    user = "\n\n".join(
        [
            f"[검사항목]\n{item}: {definition['항목명']}",
            f"[관련 법령 및 항목 설명]\n{legal_text}",
            "[메타]\n" + json.dumps(record["meta"], ensure_ascii=False, sort_keys=True),
            "[전체 원문]\n" + context.full_context(record),
            "[출력]\n원문에서 확인해야 할 법률상 사실과 관계를 memo 문자열 하나에 적는다.",
        ]
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["memo"],
        "properties": {"memo": {"type": "string", "minLength": 1}},
    }


def lines(record: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"key": f"{record['id']}:{row['doc_id']}:{row['line_id']}", "text": row["text"]}
        for row in fragments(record)
        if row["kind"] == "line"
    ]


def rank(lines_: list[dict[str, Any]], scores: list[float], evidence: str) -> int | None:
    return retrieval.rank_of_evidence(lines_, scores, evidence)


def run_one(job: dict[str, Any], records: dict[str, dict[str, Any]], table: dict[str, Any], laws: dict[str, str]) -> None:
    checkpoint = OUT / "records" / f"{job['id']}_{job['item']}.json"
    if checkpoint.exists():
        return
    response: Any = None
    try:
        legal = law_text(job["item"], table[job["item"]], laws)
        prompt = messages(records[job["id"]], job["item"], table[job["item"]], legal)
        response = common.completion(config(), prompt, schema())
        payload = common.parse_json(response.content)
        memo = payload.get("memo")
        if not isinstance(memo, str) or not memo.strip():
            raise ValueError("empty memo")
        entry = {**job, "success": True, "memo": memo, "usage": response.usage, "raw_response": response.content,
                 "prompt_sha256": common.sha256_text(json.dumps(prompt, ensure_ascii=False, sort_keys=True))}
    except Exception as exc:
        entry = {**job, "success": False, "error": f"{type(exc).__name__}: {exc}", "memo": "",
                 "usage": {} if response is None else response.usage,
                 "raw_response": "" if response is None else response.content}
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    common.write_json(checkpoint, entry)


def aggregate(jobs_: list[dict[str, Any]], records: dict[str, dict[str, Any]], table: dict[str, Any], laws: dict[str, str]) -> None:
    entries = [json.loads((OUT / "records" / f"{job['id']}_{job['item']}.json").read_text(encoding="utf-8")) for job in jobs_]
    failures = [entry for entry in entries if not entry["success"]]
    if failures:
        common.write_json(OUT / "report.json", {"experiment_id": "inc064_rationale_to_source_retrieval_gate", "failures": failures})
        raise RuntimeError(f"memo failures: {len(failures)}")
    rows = []
    total_cost = sum(float(entry.get("usage", {}).get("cost", 0) or 0) for entry in entries)
    for entry in entries:
        record = records[entry["id"]]
        source = lines(record)
        legal = law_text(entry["item"], table[entry["item"]], laws)
        criterion = retrieval.criterion_query(entry["item"], table[entry["item"]], record["meta"]) + "\n[법령]\n" + legal
        query_rows = [{"key": "criterion", "text": criterion}, {"key": "memo", "text": criterion + "\n[탐색 메모]\n" + entry["memo"]}]
        source_usage: list[dict[str, Any]] = []
        query_usage: list[dict[str, Any]] = []
        source_vectors = retrieval.recursively_embed(embedding_config(), source, "search_document", source_usage)
        query_vectors = retrieval.recursively_embed(embedding_config(), query_rows, "search_query", query_usage)
        total_cost += sum(float(x.get("usage", {}).get("cost", 0) or 0) for x in source_usage + query_usage)
        by_query = {row["key"]: vector for row, vector in zip(query_rows, query_vectors)}
        for representation in ("criterion", "memo"):
            scores = [retrieval.cosine(by_query[representation], vector) for vector in source_vectors]
            rows.append({"id": entry["id"], "item": entry["item"], "representation": representation,
                         "rank": rank(source, scores, entry["evidence"]), "line_count": len(source),
                         "memo_sha256": common.sha256_text(entry["memo"])})
    if total_cost > 0.15:
        raise RuntimeError(f"reported cost ceiling exceeded: {total_cost:.6f}")
    summary: dict[str, Any] = {}
    for representation in ("criterion", "memo"):
        current = [row for row in rows if row["representation"] == representation]
        ranks = [row["rank"] for row in current]
        summary[representation] = {
            "eligible": len(current), "found": sum(value is not None for value in ranks),
            "mrr": sum(1 / value for value in ranks if value is not None) / len(current),
            **{f"recall_at_{limit}": sum(value is not None and value <= limit for value in ranks) / len(current) for limit in RANKS},
        }
    paired = []
    for job in jobs_:
        control = next(row for row in rows if row["id"] == job["id"] and row["item"] == job["item"] and row["representation"] == "criterion")["rank"]
        memo = next(row for row in rows if row["id"] == job["id"] and row["item"] == job["item"] and row["representation"] == "memo")["rank"]
        paired.append({"id": job["id"], "item": job["item"], "criterion_rank": control, "memo_rank": memo,
                       "improved": memo is not None and (control is None or memo < control),
                       "worsened": control is not None and (memo is None or memo > control)})
    report = {"experiment_id": "inc064_rationale_to_source_retrieval_gate", "jobs": len(jobs_), "memo_transport_success": len(entries),
              "reported_cost_usd": total_cost, "summaries": summary, "paired": paired,
              "advance_gate": {"no_memo_evidence_loss": not any(row["memo_rank"] is None for row in paired),
                               "no_paired_rank_regression": not any(row["worsened"] for row in paired),
                               "at_least_one_strict_improvement": any(row["improved"] for row in paired)}}
    report["advance_gate"]["pass"] = all(report["advance_gate"].values())
    common.write_jsonl(OUT / "rank_rows.jsonl", rows)
    common.write_json(OUT / "report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "run", "aggregate"), required=True)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    records, labels, table, laws = load()
    jobs_ = jobs(records, labels)
    OUT.mkdir(parents=True, exist_ok=True)
    if args.mode == "preflight":
        manifest = []
        for job in jobs_:
            legal = law_text(job["item"], table[job["item"]], laws)
            prompt = messages(records[job["id"]], job["item"], table[job["item"]], legal)
            manifest.append({**job, "prompt_sha256": common.sha256_text(json.dumps(prompt, ensure_ascii=False, sort_keys=True)),
                             "message_characters": sum(len(row["content"]) for row in prompt)})
        common.write_jsonl(OUT / "manifest.jsonl", manifest)
        common.write_json(OUT / "config.json", {"protocol": "incubator/docs/inc064_rationale_to_source_retrieval_protocol.md", "jobs": len(jobs_), "model": config(), "embedding_model": embedding_config(), "max_cost_usd": 0.15})
        print(json.dumps({"status": "preflight_ok", "jobs": len(jobs_), "max_message_characters": max(row["message_characters"] for row in manifest), "max_cost_usd": 0.15}, ensure_ascii=False, indent=2))
        return
    if args.mode == "run":
        for position, job in enumerate(jobs_, 1):
            run_one(job, records, table, laws)
            print(f"completed={position}/{len(jobs_)}", flush=True)
        return
    aggregate(jobs_, records, table, laws)


if __name__ == "__main__":
    main()
