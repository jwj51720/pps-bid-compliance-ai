#!/usr/bin/env python3
"""Exact-token, label-blind capacity profile for EXP180 timeline navigation."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_complete_fact_admission import make_token_counter, source_coverage_gaps
from scripts.inspect_prompt import build_pipeline_for_preview
from src.context_budget import pack_contexts_to_token_budget
from src.data import load_records
from src.prompt import append_fact_inventory, append_timeline_fact_navigation
from src.schema import FACT_INVENTORY_CATEGORIES, TIMELINE_FACT_ROLES


def _eligible(record: dict[str, Any]) -> bool:
    meta = record.get("meta", {})
    return (
        str(meta.get("적용계약법", "")) == "지방계약법"
        and str(meta.get("낙찰방법", "")) == "협상에의한계약"
    )


def _saved_inventory(path: Path) -> dict[str, dict[str, tuple[tuple[str, str], ...]]]:
    rows = (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line)
    return {
        row["id"]: {
            category: tuple((str(doc_id), str(excerpt)) for doc_id, excerpt in row[
                "staged_run"]["inventory"]["by_category"].get(category, []))
            for category in FACT_INVENTORY_CATEGORIES
        }
        for row in rows
    }


def _timeline(maximum: bool) -> dict[str, tuple[tuple[str, str], ...]]:
    text = "가" * 360
    return {
        role: (("synthetic", text), ("synthetic", text)) if maximum else ()
        for role in TIMELINE_FACT_ROLES
    }


def profile(config_path: Path, predictions_path: Path) -> dict[str, Any]:
    from src.config import load_config

    config = load_config(config_path)
    pipeline = build_pipeline_for_preview(config)
    count_tokens = make_token_counter(config.llm.tokenizer_source or config.llm.model)
    pipeline.count_tokens = count_tokens
    records = load_records(config.data.input_path)
    saved = _saved_inventory(predictions_path)
    budget = config.max_model_len - config.output_reserve_tokens
    report: dict[str, Any] = {
        "experiment_id": config.experiment_id,
        "method": "exact Gemma chat-template token admission; no labels or provider calls",
        "generic_inventory_source": str(predictions_path),
        "record_count": len(records),
        "eligible_record_count": sum(_eligible(record) for record in records),
        "prompt_budget_tokens": budget,
        "scenarios": {},
    }
    for name, maximum in (("empty_timeline", False), ("timeline_schema_upper", True)):
        rows: list[dict[str, Any]] = []
        omissions: list[dict[str, Any]] = []
        for record in records:
            inventory = saved.get(record["id"])
            if inventory is None:
                raise ValueError(f"saved EXP171 inventory missing {record['id']}")
            timeline = _timeline(maximum) if _eligible(record) else None

            def messages_for(context: str | None) -> list[dict[str, str]]:
                messages = append_fact_inventory(pipeline.messages_for_context(record, context), inventory)
                return append_timeline_fact_navigation(messages, timeline) if timeline is not None else messages

            contexts = pack_contexts_to_token_budget(
                pipeline._visible_record(record), pipeline.system_prompt_for_record(record),
                count_tokens, budget, pipeline.notice_anchor_chars, message_builder=messages_for,
            )
            tokens = [count_tokens(messages_for(context)) for context in contexts]
            if any(value > budget for value in tokens):
                raise AssertionError(f"over-budget final pack: {record['id']}")
            omissions.extend(
                {"id": record["id"], **gap}
                for gap in source_coverage_gaps(pipeline._visible_record(record), contexts)
            )
            rows.append({"id": record["id"], "final_passes": len(contexts), "pack_tokens": tokens})
        final_calls = sum(row["final_passes"] for row in rows)
        timeline_calls = sum(
            len(pipeline.contexts_for_record(record)) for record in records if _eligible(record)
        )
        report["scenarios"][name] = {
            "timeline_navigation": "empty" if not maximum else "5 roles × 2 synthetic 360-char excerpts",
            "generic_stage_calls": sum(len(pipeline.contexts_for_record(record)) for record in records),
            "timeline_stage_calls": timeline_calls,
            "final_calls": final_calls,
            "total_calls": sum(len(pipeline.contexts_for_record(record)) for record in records) + timeline_calls + final_calls,
            "final_pass_distribution": dict(sorted(Counter(row["final_passes"] for row in rows).items())),
            "source_document_omission_count": len(omissions),
            "rows": rows,
        }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = profile(args.config, args.predictions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        **result,
        "scenarios": {key: {k: v for k, v in value.items() if k != "rows"}
                      for key, value in result["scenarios"].items()},
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
