#!/usr/bin/env python3
"""Test flat binary plus candidate-index JSON transport without source data."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

import inc001_simple_joint24 as common


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "incubator/runs/inc052_flat_candidate_transport_audit"
EXPECTED = {"v10": 0, "v11": 1, "v12": 0, "v13": 1, "e12": -1, "e13": 3}


def schema() -> dict[str, Any]:
    properties = {key: {"type": "integer", "enum": [0, 1]} for key in ("v10", "v11", "v12", "v13")}
    properties.update({key: {"type": "integer", "enum": [-1, 0, 1, 2, 3, 4]} for key in ("e12", "e13")})
    return {"type": "object", "additionalProperties": False, "required": list(EXPECTED), "properties": properties}


def one(repetition: int) -> dict[str, Any]:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise RuntimeError("missing OPENROUTER_API_KEY")
    payload = {"model": "google/gemma-4-26b-a4b-it", "messages": [{"role": "system", "content": "당신은 JSON 전송 검증기다."}, {"role": "user", "content": "JSON 하나만 출력하라. 정확히 v10=0,v11=1,v12=0,v13=1,e12=-1,e13=3을 출력하라."}], "temperature": 0.0, "seed": 20260905, "max_tokens": 64, "stream": False, "provider": {"require_parameters": True, "sort": "throughput"}, "response_format": {"type": "json_schema", "json_schema": {"name": "flat_candidate", "strict": True, "schema": schema()}}}
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json=payload, timeout=120)
        if not response.ok:
            return {"repetition": repetition, "success": False, "error": f"HTTP {response.status_code}: {response.text[:240]}", "usage": {}, "content": ""}
        body = response.json(); content = body["choices"][0]["message"]["content"]; usage = body.get("usage", {})
        try: valid = json.loads(content) == EXPECTED
        except json.JSONDecodeError: valid = False
        completion = int(usage.get("completion_tokens", 0) or 0)
        return {"repetition": repetition, "success": valid and completion <= 64, "parse_and_value_valid": valid, "completion_within_cap": completion <= 64, "completion_tokens": completion, "usage": usage, "content": content}
    except Exception as exc:
        return {"repetition": repetition, "success": False, "error": f"{type(exc).__name__}: {exc}", "usage": {}, "content": ""}


def main() -> None:
    load_dotenv(ROOT / ".env"); OUTPUT.mkdir(parents=True, exist_ok=True); path = OUTPUT / "responses.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []
    existing = {row["repetition"] for row in rows}; spend = sum(float(row.get("usage", {}).get("cost", 0) or 0) for row in rows)
    for repetition in range(1, 11):
        if repetition in existing: continue
        if spend >= .04: raise RuntimeError(f"cost ceiling reached: {spend:.6f}")
        row = one(repetition); rows.append(row); spend += float(row.get("usage", {}).get("cost", 0) or 0); common.write_jsonl(path, rows); print(f"{repetition}/10 success={row['success']}", flush=True)
    report = {"experiment_id": "inc052_flat_candidate_transport_audit", "calls": len(rows), "valid": sum(row["success"] for row in rows), "cap_breaches": sum(not row.get("completion_within_cap", False) for row in rows), "reported_cost_usd": spend, "advance": len(rows) == 10 and all(row["success"] for row in rows)}
    common.write_json(OUTPUT / "report.json", report); print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
