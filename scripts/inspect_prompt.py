#!/usr/bin/env python3
"""Export the exact sanitized request body for one local experiment record."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.data import load_item_table, load_records
from src.prompt import build_messages, build_system_prompt
from src.schema import judgment_schema


def _request_preview(config: Any, messages: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "model": config.llm.model,
        "messages": messages,
        "temperature": config.llm.temperature,
        "max_tokens": config.llm.max_tokens,
        "seed": config.llm.seed,
        "stream": False,
        "provider": {
            "require_parameters": config.llm.require_parameters,
            "sort": config.llm.provider_sort,
        },
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "pps_compliance_judgment",
                "strict": True,
                "schema": judgment_schema(),
            },
        },
    }


def _markdown_preview(record_id: str, config: Any, messages: list[dict[str, str]]) -> str:
    system, user = messages
    return (
        f"# Actual LLM Input: {record_id}\n\n"
        "This file is generated without making an API call. It is the exact `messages` "
        "content constructed by the current experiment configuration. The companion "
        "JSON also includes the non-secret request settings and response schema.\n\n"
        "## Effective Configuration\n\n"
        f"- Model: `{config.llm.model}`\n"
        f"- `prompt.max_document_chars`: `{config.max_document_chars}`\n"
        f"- `max_tokens`: `{config.llm.max_tokens}`\n"
        f"- Temperature: `{config.llm.temperature}`\n"
        f"- Seed: `{config.llm.seed}`\n\n"
        "## System Message\n\n"
        f"```text\n{system['content']}\n```\n\n"
        "## User Message\n\n"
        f"```text\n{user['content']}\n```\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--record-id", default="PPS-DEV-01")
    parser.add_argument("--output-dir", default="outputs/prompt-inspection")
    args = parser.parse_args()

    config = load_config(args.config)
    record = next(
        (item for item in load_records(config.data.input_path) if item["id"] == args.record_id),
        None,
    )
    if record is None:
        raise ValueError(f"record not found: {args.record_id}")
    system_prompt = build_system_prompt(load_item_table(config.data.item_table_path))
    messages = build_messages(record, system_prompt, config.max_document_chars)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = args.record_id.lower()
    (output_dir / f"{stem}.request.json").write_text(
        json.dumps(_request_preview(config, messages), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / f"{stem}.messages.md").write_text(
        _markdown_preview(args.record_id, config, messages), encoding="utf-8"
    )
    print(output_dir / f"{stem}.messages.md")
    print(output_dir / f"{stem}.request.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
