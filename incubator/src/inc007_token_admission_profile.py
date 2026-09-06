#!/usr/bin/env python3
"""No-API exact-Gemma-tokenizer profile for complete-document packing."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from transformers import AutoTokenizer

import inc001_simple_joint24 as common


def count_messages(tokenizer: Any, messages: list[dict[str, str]]) -> int:
    encoded = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True)
    ids = encoded["input_ids"] if hasattr(encoded, "keys") else encoded
    return len(ids)


def render_messages(record: dict[str, Any], system: str, document_context: str) -> list[dict[str, str]]:
    unavailable = record.get("dropped_doc_counts") or {}
    user = "\n\n".join([
        f"[공고 ID]\n{record['id']}",
        "[나라장터 입력 메타]\n" + json.dumps(record["meta"], ensure_ascii=False, sort_keys=True),
        "[미수록 문서]\n" + json.dumps(unavailable, ensure_ascii=False, sort_keys=True),
        "[문서]\n" + document_context,
    ])
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def pack_complete_documents(record: dict[str, Any], system: str, tokenizer: Any, budget: int, anchor_chars: int) -> tuple[list[dict[str, Any]], int]:
    """Exact-token packs: whole ordered docs first, then exact-token fragments."""
    order = common.DOCUMENT_ORDER
    documents = sorted(record["docs"], key=lambda doc: (order[doc["type"]], doc["doc_id"]))
    announcement = next((doc for doc in documents if doc["type"] == "공고문"), None)
    anchor = announcement["text"][:anchor_chars] if announcement else ""
    anchor_header = f"[공고문 앵커:{announcement['doc_id']}]\n" if announcement else ""

    def render(parts: list[str], include_anchor: bool) -> str:
        prefix = anchor_header + anchor if include_anchor and anchor else ""
        return "\n\n".join(value for value in (prefix, *parts) if value)

    def fits(parts: list[str], include_anchor: bool) -> bool:
        return count_messages(tokenizer, render_messages(record, system, render(parts, include_anchor))) <= budget

    if not fits([], False):
        raise ValueError(f"fixed prompt exceeds budget: {record['id']}")
    packs: list[dict[str, Any]] = []
    current: list[str] = []
    current_docs: list[str] = []
    current_anchor = False

    def flush() -> None:
        nonlocal current, current_docs, current_anchor
        if current:
            context = render(current, current_anchor)
            packs.append({"document_context": context, "document_ids": current_docs, "token_count": count_messages(tokenizer, render_messages(record, system, context))})
            current, current_docs, current_anchor = [], [], False

    for document in documents:
        include_anchor = bool(announcement and document["doc_id"] != announcement["doc_id"])
        header = f"[{document['type']}:{document['doc_id']}]\n"
        text, offset = document["text"], 0
        while offset < len(text) or (not text and offset == 0):
            suffix = "" if offset == 0 else f" [계속 {offset}]"
            fragment_header = header.rstrip("\n") + suffix + "\n"
            remaining = text[offset:]
            candidate = current + [fragment_header + remaining]
            candidate_anchor = current_anchor or include_anchor
            if fits(candidate, candidate_anchor):
                current, current_docs, current_anchor = candidate, current_docs + [document["doc_id"]], candidate_anchor
                offset = len(text) if text else 1
                continue
            if current:
                flush()
                continue
            low, high, best = 1, len(remaining), 0
            while low <= high:
                middle = (low + high) // 2
                if fits([fragment_header + remaining[:middle]], include_anchor):
                    best, low = middle, middle + 1
                else:
                    high = middle - 1
            if best == 0:
                raise ValueError(f"cannot admit document fragment: {record['id']} {document['doc_id']}")
            current = [fragment_header + remaining[:best]]
            current_docs = [document["doc_id"]]
            current_anchor = include_anchor
            offset += best
            flush()
    flush()
    return packs, len(documents)


def percentile(values: list[int], q: float) -> int:
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * q)] if ordered else 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="incubator/configs/inc007_token_admission_profile.json")
    args = parser.parse_args()
    root = common.repo_root()
    config = json.loads((root / args.config).read_text(encoding="utf-8"))
    output = root / "incubator/runs" / config["experiment_id"]
    output.mkdir(parents=True, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(config["model_tokenizer"])
    records = common.read_jsonl_gz(root / config["data_root"] / "dev.jsonl.gz")
    item_table = json.loads((root / config["data_root"] / "data/항목표.json").read_text(encoding="utf-8"))["항목"]
    system = common.build_system_prompt(item_table)
    budget = config["max_model_len"] - config["output_reserve_tokens"]
    rows: list[dict[str, Any]] = []
    for record in records:
        full_context, _ = common.render_documents(record, 10**9)
        full_tokens = count_messages(tokenizer, render_messages(record, system, full_context))
        packs, document_count = pack_complete_documents(record, system, tokenizer, budget, config["notice_anchor_chars"])
        rows.append({"id": record["id"], "full_prompt_tokens": full_tokens, "fits_one_pass": full_tokens <= budget, "overflow_tokens": max(0, full_tokens - budget), "source_document_count": document_count, "adaptive_pass_count": len(packs), "adaptive_pass_tokens": [pack["token_count"] for pack in packs], "adaptive_pack_document_ids": [pack["document_ids"] for pack in packs]})
    pass_counts = [row["adaptive_pass_count"] for row in rows]
    full_tokens = [row["full_prompt_tokens"] for row in rows]
    report = {"experiment_id": config["experiment_id"], "method": "GemmaTokenizer.apply_chat_template with generation prompt; no provider calls", "tokenizer": config["model_tokenizer"], "max_model_len": config["max_model_len"], "output_reserve_tokens": config["output_reserve_tokens"], "prompt_budget_tokens": budget, "record_count": len(rows), "one_pass_fit_count": sum(row["fits_one_pass"] for row in rows), "overflow_count": sum(not row["fits_one_pass"] for row in rows), "full_prompt_tokens": {"p50": percentile(full_tokens, .5), "p90": percentile(full_tokens, .9), "p95": percentile(full_tokens, .95), "max": max(full_tokens)}, "adaptive_pass_count": {"mean": sum(pass_counts) / len(pass_counts), "p50": percentile(pass_counts, .5), "p95": percentile(pass_counts, .95), "max": max(pass_counts), "distribution": dict(sorted(Counter(pass_counts).items()))}, "test_1853_projection": {"estimated_calls_from_dev_mean": round(1853 * sum(pass_counts) / len(pass_counts), 1), "estimated_calls_from_dev_p95": 1853 * percentile(pass_counts, .95)}, "source_sha256": {"dev": common.sha256_file(root / config["data_root"] / "dev.jsonl.gz"), "item_table": common.sha256_file(root / config["data_root"] / "data/항목표.json")}, "rows": rows}
    common.write_json(output / "config.json", config)
    common.write_json(output / "report.json", report)
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
