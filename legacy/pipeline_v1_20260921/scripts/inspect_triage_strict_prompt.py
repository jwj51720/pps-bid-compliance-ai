#!/usr/bin/env python3
"""Render B-stage triage inputs without an API call.

The strict-final input is intentionally not claimed to be exact here: it
depends on an actual triage payload and must be exported again by the runner
before any paid B experiment.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.data import load_decision_cards, load_item_table, load_records
from src.prompt import build_messages, build_triage_system_prompt
from src.schema import ITEMS, triage_schema


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/config.exp147-input-truthful-card-fast-panel.yaml")
    parser.add_argument("--record-id", default="PPS-DEV-01")
    parser.add_argument("--output-dir", default="outputs/triage-strict-prompt-review-v1")
    args = parser.parse_args()
    config = load_config(args.config)
    if config.context_strategy != "single" or config.overflow_split_enabled:
        raise ValueError("triage preview currently requires one fixed single notice context")
    if config.decision_cards_path is None:
        raise ValueError("triage preview requires the candidate's decision cards")
    item_table = load_item_table(config.data.item_table_path)
    cards = load_decision_cards(config.decision_cards_path, item_table)
    record = next(
        (value for value in load_records(config.data.input_path) if value["id"] == args.record_id),
        None,
    )
    if record is None:
        raise ValueError(f"record not found: {args.record_id}")
    system = build_triage_system_prompt(item_table, cards, ITEMS)
    messages = build_messages(
        record, system, config.max_document_chars,
        prompt_profile=config.prompt_profile,
        metadata_style=config.metadata_style,
        output_mode=config.output_mode,
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = args.record_id.lower()
    (output_dir / f"{stem}.triage.messages.md").write_text(
        f"# Exact B triage input: {args.record_id}\n\n"
        f"- config: `{config.path.relative_to(ROOT)}`\n"
        "- Generated through the shared prompt builder. No API call was made.\n\n"
        "## System message\n\n```text\n" + messages[0]["content"]
        + "\n```\n\n## User message\n\n```text\n" + messages[1]["content"] + "\n```\n",
        encoding="utf-8",
    )
    (output_dir / f"{stem}.triage.request.json").write_text(
        json.dumps({"messages": messages, "response_schema": triage_schema(ITEMS)}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(output_dir / f"{stem}.triage.messages.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
