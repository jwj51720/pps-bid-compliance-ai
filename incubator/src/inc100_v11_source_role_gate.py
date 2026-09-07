#!/usr/bin/env python3
"""Bounded diagnostic of v11 applicability and source-role reasoning."""
from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import json
import os
import re
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/open"
CARDS = ROOT / "incubator/reference/dev_history/decision_cards_v6.json"
PRODUCTS = ROOT / "incubator/data/derived/historical_exp014/competition_products_v1.json"
IDS = ROOT / "incubator/data/derived/inc100_v11_role_audit_ids.json"
OUT = ROOT / "incubator/runs/inc100_v11_source_role_gate"


def schema() -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "required": ["applicability", "source_role", "restriction_status", "source_quote", "v11"],
        "properties": {
            "applicability": {"type": "string", "enum": ["competitive", "noncompetitive", "unknown"]},
            "source_role": {"type": "string", "enum": ["bidder_eligibility", "incidental_or_post_award", "no_relevant_source", "mixed_or_uncertain"]},
            "restriction_status": {"type": "string", "enum": ["required_competition_restriction_present", "absent", "uncertain"]},
            "source_quote": {"type": "string"},
            "v11": {"type": "integer", "enum": [0, 1]},
        },
    }


def exact_status(meta: dict[str, Any], products: dict[str, Any]) -> str:
    codes = re.findall(r"\d{10}", str(meta.get("세부품명번호목록") or ""))
    if not codes:
        return "unknown_no_exact_code"
    return "matched" if any(code in products for code in codes) else "not_matched"


def message(record: dict[str, Any], card: dict[str, Any], products: dict[str, Any]) -> list[dict[str, str]]:
    status = exact_status(record["meta"], products)
    docs = "\n\n".join(f"[{doc['type']}|{doc['doc_id']}]\n{doc['text']}" for doc in record["docs"])
    system = """당신은 v11만 감사하는 공공입찰 법령 검토자다. 최종 JSON 필드 각각을 독립적으로 판정한다.
정확 제품코드 상태가 not_matched이면 경쟁제품 적용대상은 noncompetitive이고 v11은 반드시 0이다.
unknown_no_exact_code는 적용성의 부정 근거가 아니다. 원문에서 중소기업 관련 언급을 발견해도,
입찰참가자격·입찰조건에 실제로 작동하는 제한일 때만 bidder_eligibility 또는 필요한 제한으로 본다.
낙찰 후 의무, 하도급, 금융·홍보 안내, 일반 법령 언급은 incidental_or_post_award다.
v11은 경쟁제품 적용대상이고 필요한 중소기업자간 경쟁 제한이 공고 전체에 없을 때만 1이다.
source_quote는 판단에 쓴 원문 그대로 최대 500자로 쓰며, 원문 근거가 없으면 빈 문자열이다."""
    user = "\n\n".join([
        "[v11 카드]\n" + card["prompt_text"],
        "[정확 제품코드 적용성 사실]\n" + status,
        "[metadata]\n" + json.dumps(record["meta"], ensure_ascii=False, sort_keys=True),
        "[공고 원문 전체]\n" + docs,
    ])
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def output_text(body: dict[str, Any]) -> str:
    direct = body.get("output_text")
    if isinstance(direct, str) and direct:
        return direct
    return "".join(
        str(block.get("text", ""))
        for message in body.get("output", []) if message.get("type") == "message"
        for block in message.get("content", []) if block.get("type") == "output_text"
    )


def call(key: str, record: dict[str, Any], card: dict[str, Any], products: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "model": "gpt-5.6-luna", "input": message(record, card, products), "store": False,
        "max_output_tokens": 2048, "reasoning": {"effort": "medium"},
        "text": {"format": {"type": "json_schema", "name": "v11_source_role", "strict": True, "schema": schema()}},
    }
    try:
        response = requests.post("https://api.openai.com/v1/responses", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json=payload, timeout=300)
        body = response.json()
        text = output_text(body)
        if response.ok and text:
            value = json.loads(text)
            return {"id": record["id"], "success": True, "result": value, "usage": body.get("usage", {})}
        return {"id": record["id"], "success": False, "error": f"{response.status_code}:{str(body)[:400]}", "response_body": body}
    except Exception as exc:
        return {"id": record["id"], "success": False, "error": f"{type(exc).__name__}:{exc}"}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--run", action="store_true"); parser.add_argument("--probe-id"); args = parser.parse_args()
    if not args.run:
        raise SystemExit("Pass --run after reading the fixed protocol.")
    ids = [args.probe_id] if args.probe_id else json.loads(IDS.read_text(encoding="utf-8"))["ids"]
    with gzip.open(RAW / "dev.jsonl.gz", "rt", encoding="utf-8") as handle:
        notices = {row["id"]: row for row in (json.loads(line) for line in handle if line)}
    card = json.loads(CARDS.read_text(encoding="utf-8"))["cards"]["v11"]
    products = json.loads(PRODUCTS.read_text(encoding="utf-8"))["products"]
    load_dotenv(ROOT / ".env"); key = os.environ["OPENAI_API_KEY"]
    OUT.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(call, key, notices[notice_id], card, products) for notice_id in ids]
        rows = [future.result() for future in futures]
    name = "transport_probe.jsonl" if args.probe_id else "responses.jsonl"
    (OUT / name).write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    print(json.dumps({"requests": len(rows), "success": sum(row["success"] for row in rows), "failed": [row["id"] for row in rows if not row["success"]]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
