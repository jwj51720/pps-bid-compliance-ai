#!/usr/bin/env python3
"""Synthetic Gemma-4 thinking-trigger versus flat JSON transport audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

import inc001_simple_joint24 as common


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "incubator/runs/inc067_gemma4_thinking_transport_audit"
EXPECTED = {f"v{index}": index % 2 for index in range(1, 25)}
ARMS = ("standard", "think_trigger")


def config() -> dict[str, Any]:
    return {"model": "google/gemma-4-26b-a4b-it", "api_url": "https://openrouter.ai/api/v1/chat/completions", "api_key_env": "OPENROUTER_API_KEY", "temperature": 0.0, "seed": 20260905, "max_tokens": 256, "timeout_seconds": 120, "request_retries": 1}


def schema() -> dict[str, Any]:
    return {"type": "object", "additionalProperties": False, "required": list(EXPECTED), "properties": {field: {"type": "integer", "enum": [0, 1]} for field in EXPECTED}}


def messages(arm: str) -> list[dict[str, str]]:
    instruction = "당신은 엄격한 JSON 전송 검증기다. JSON 객체 하나만 출력한다."
    if arm == "think_trigger":
        instruction = "<|think|>\n" + instruction
    task = "다음 값을 정확히 출력한다: " + ", ".join(f"{field}={value}" for field, value in EXPECTED.items())
    return [{"role": "system", "content": instruction}, {"role": "user", "content": task}]


def run_one(arm: str, repeat: int) -> None:
    path = OUT / "records" / f"{arm}_{repeat}.json"
    if path.exists():
        return
    response: Any = None
    try:
        prompt = messages(arm)
        response = common.completion(config(), prompt, schema())
        payload = common.parse_json(response.content)
        entry = {"arm": arm, "repeat": repeat, "success": payload == EXPECTED and int(response.usage.get("completion_tokens", 0) or 0) <= 256, "value_valid": payload == EXPECTED, "completion_within_cap": int(response.usage.get("completion_tokens", 0) or 0) <= 256, "usage": response.usage, "content": response.content, "prompt_sha256": common.sha256_text(json.dumps(prompt, ensure_ascii=False, sort_keys=True)), "visible_thought_marker": "<|channel>thought" in response.content}
    except Exception as exc:
        entry = {"arm": arm, "repeat": repeat, "success": False, "value_valid": False, "completion_within_cap": False, "error": f"{type(exc).__name__}: {exc}", "usage": {} if response is None else response.usage, "content": "" if response is None else response.content, "visible_thought_marker": False}
    path.parent.mkdir(parents=True, exist_ok=True)
    common.write_json(path, entry)


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--mode", choices=("preflight", "run", "aggregate"), required=True)
    args = parser.parse_args(); load_dotenv(ROOT / ".env"); OUT.mkdir(parents=True, exist_ok=True)
    if args.mode == "preflight":
        common.write_json(OUT / "config.json", {"protocol": "incubator/docs/inc067_gemma4_thinking_transport_protocol.md", "arms": ARMS, "repeats": 6, "model": config(), "max_cost_usd": 0.05, "expected": EXPECTED})
        print(json.dumps({"status": "preflight_ok", "calls": 12, "max_cost_usd": 0.05}, ensure_ascii=False)); return
    if args.mode == "run":
        for repeat in range(1, 7):
            for arm in ARMS:
                run_one(arm, repeat)
                print(f"{arm}/{repeat}", flush=True)
        return
    rows = [json.loads((OUT / "records" / f"{arm}_{repeat}.json").read_text(encoding="utf-8")) for arm in ARMS for repeat in range(1, 7)]
    cost = sum(float(row.get("usage", {}).get("cost", 0) or 0) for row in rows)
    if cost > .05:
        raise RuntimeError(f"reported cost ceiling exceeded: {cost:.6f}")
    report = {"experiment_id": "inc067_gemma4_thinking_transport_audit", "reported_cost_usd": cost, "arms": {arm: {"calls": len([row for row in rows if row["arm"] == arm]), "valid": sum(row["success"] for row in rows if row["arm"] == arm), "visible_thought_markers": sum(row["visible_thought_marker"] for row in rows if row["arm"] == arm), "completion_tokens": [int(row.get("usage", {}).get("completion_tokens", 0) or 0) for row in rows if row["arm"] == arm], "reasoning_tokens": [int(row.get("usage", {}).get("completion_tokens_details", {}).get("reasoning_tokens", 0) or 0) for row in rows if row["arm"] == arm]} for arm in ARMS}}
    common.write_json(OUT / "report.json", report); print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
