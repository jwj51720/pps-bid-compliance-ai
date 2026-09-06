#!/usr/bin/env python3
"""Isolate JSON transport behavior; contains no competition material."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

import inc001_simple_joint24 as common


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "incubator/runs/inc051_structured_output_transport_audit"
EXPECTED = {"v10": 0, "v11": 1, "v12": 0, "v13": 1}
ARMS = ("nested_schema", "flat_schema", "json_object")


def nested_schema() -> dict[str, Any]:
    return {"type": "object", "additionalProperties": False, "required": list(EXPECTED), "properties": {key: {"type": "object", "additionalProperties": False, "required": ["value"], "properties": {"value": {"type": "integer", "enum": [0, 1]}}} for key in EXPECTED}}


def flat_schema() -> dict[str, Any]:
    return {"type": "object", "additionalProperties": False, "required": list(EXPECTED), "properties": {key: {"type": "integer", "enum": [0, 1]} for key in EXPECTED}}


def payload(arm: str) -> dict[str, Any]:
    message = "JSON 하나만 출력하라. 정확히 v10=0, v11=1, v12=0, v13=1을 출력하라. 설명이나 공백 채우기를 하지 마라."
    value: dict[str, Any] = {"model": "google/gemma-4-26b-a4b-it", "messages": [{"role": "system", "content": "당신은 JSON 전송 검증기다."}, {"role": "user", "content": message}], "temperature": 0.0, "seed": 20260905, "max_tokens": 64, "stream": False, "provider": {"require_parameters": True, "sort": "throughput"}}
    if arm == "nested_schema":
        value["response_format"] = {"type": "json_schema", "json_schema": {"name": "nested", "strict": True, "schema": nested_schema()}}
    elif arm == "flat_schema":
        value["response_format"] = {"type": "json_schema", "json_schema": {"name": "flat", "strict": True, "schema": flat_schema()}}
    else:
        value["response_format"] = {"type": "json_object"}
    return value


def valid(arm: str, content: str) -> bool:
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        return False
    if arm == "nested_schema":
        value = {key: row.get("value") if isinstance(row, dict) else None for key, row in value.items()} if isinstance(value, dict) else value
    return value == EXPECTED


def run_one(arm: str, repetition: int) -> dict[str, Any]:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise RuntimeError("missing OPENROUTER_API_KEY")
    started = time.monotonic()
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json=payload(arm), timeout=120)
        if not response.ok:
            return {"arm": arm, "repetition": repetition, "success": False, "error": f"HTTP {response.status_code}: {response.text[:240]}", "usage": {}, "content": "", "seconds": round(time.monotonic() - started, 3)}
        body = response.json(); content = body["choices"][0]["message"]["content"]
        usage = body.get("usage", {})
        completion = int(usage.get("completion_tokens", 0) or 0)
        return {"arm": arm, "repetition": repetition, "success": valid(arm, content) and completion <= 64, "parse_and_value_valid": valid(arm, content), "completion_within_cap": completion <= 64, "completion_tokens": completion, "usage": usage, "content": content, "seconds": round(time.monotonic() - started, 3)}
    except Exception as exc:
        return {"arm": arm, "repetition": repetition, "success": False, "error": f"{type(exc).__name__}: {exc}", "usage": {}, "content": "", "seconds": round(time.monotonic() - started, 3)}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--mode", choices=("preflight", "run"), default="preflight")
    args = parser.parse_args(); load_dotenv(ROOT / ".env"); OUTPUT.mkdir(parents=True, exist_ok=True)
    if args.mode == "preflight":
        common.write_json(OUTPUT / "config.json", {"arms": ARMS, "repetitions": 10, "requested_max_tokens": 64, "max_cost_usd": 0.12})
        print(json.dumps({"status": "preflight_ok", "calls": 30, "arms": ARMS, "requested_max_tokens": 64, "max_cost_usd": 0.12}, ensure_ascii=False, indent=2)); return
    path = OUTPUT / "responses.jsonl"; existing = {(row["arm"], row["repetition"]): row for row in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())} if path.exists() else {}
    rows = list(existing.values())
    spend = sum(float(row.get("usage", {}).get("cost", 0) or 0) for row in rows)
    rejected_arms = {row["arm"] for row in rows if not row.get("completion_within_cap", True)}
    for repetition in range(1, 11):
        for arm in ARMS:
            if arm in rejected_arms:
                continue
            if (arm, repetition) in existing:
                continue
            if spend >= .12:
                raise RuntimeError(f"cost ceiling reached before {arm}/{repetition}: {spend:.6f}")
            row = run_one(arm, repetition); rows.append(row); spend += float(row.get("usage", {}).get("cost", 0) or 0)
            common.write_jsonl(path, rows)
            print(f"{arm}/{repetition} success={row['success']}", flush=True)
    summary = {}
    for arm in ARMS:
        subset = [row for row in rows if row["arm"] == arm]
        summary[arm] = {"calls": len(subset), "valid": sum(row["success"] for row in subset), "cap_breaches": sum(not row.get("completion_within_cap", False) for row in subset), "reported_cost_usd": sum(float(row.get("usage", {}).get("cost", 0) or 0) for row in subset)}
    common.write_json(OUTPUT / "report.json", {"experiment_id": "inc051_structured_output_transport_audit", "reported_cost_usd": spend, "arms": summary})
    print(json.dumps({"reported_cost_usd": spend, "arms": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
