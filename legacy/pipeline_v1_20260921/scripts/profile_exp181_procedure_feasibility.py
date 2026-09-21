#!/usr/bin/env python3
"""Measure EXP181's worst-case token/call topology without provider calls."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_complete_fact_admission import make_token_counter, source_coverage_gaps
from scripts.inspect_prompt import build_pipeline_for_preview
from src.context_budget import pack_contexts_to_token_budget
from src.data import load_records
from src.prompt import append_fact_inventory, append_procedure_fact_navigation
from src.schema import FACT_INVENTORY_CATEGORIES, PROCEDURE_FACT_FIELDS


def _saved_inventory(path: Path) -> dict[str, dict[str, tuple[tuple[str, str], ...]]]:
    return {
        row["id"]: {
            category: tuple((str(doc_id), str(text)) for doc_id, text in row["staged_run"]["inventory"]["by_category"].get(category, []))
            for category in FACT_INVENTORY_CATEGORIES
        }
        for row in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line)
    }


def profile(config_path: Path, predictions_path: Path) -> dict:
    from src.config import load_config

    config = load_config(config_path)
    pipeline = build_pipeline_for_preview(config)
    count_tokens = make_token_counter(config.llm.tokenizer_source or config.llm.model)
    pipeline.count_tokens = count_tokens
    records = load_records(config.data.input_path)
    saved = _saved_inventory(predictions_path)
    budget = config.max_model_len - config.output_reserve_tokens
    scenarios = {
        "added_empty_procedure": (True, 0),
        "added_procedure_schema_upper": (True, 2),
        "replacement_empty_procedure": (False, 0),
        "replacement_procedure_schema_upper": (False, 2),
    }
    result = {
        "experiment_id": config.experiment_id,
        "method": "exact Gemma chat-template admission; no labels or provider calls",
        "record_count": len(records),
        "prompt_budget_tokens": budget,
        "scenarios": {},
    }
    for name, (include_generic, per_field) in scenarios.items():
        rows, omissions = [], []
        procedure = {
            field: tuple(("synthetic", "가" * 360) for _ in range(per_field))
            for field in PROCEDURE_FACT_FIELDS
        }
        for record in records:
            inventory = saved[record["id"]]

            def messages_for(context: str | None):
                base_messages = pipeline.messages_for_context(record, context)
                if include_generic:
                    base_messages = append_fact_inventory(base_messages, inventory)
                return append_procedure_fact_navigation(
                    base_messages,
                    procedure,
                )

            contexts = pack_contexts_to_token_budget(
                pipeline._visible_record(record), pipeline.system_prompt_for_record(record),
                count_tokens, budget, pipeline.notice_anchor_chars, message_builder=messages_for,
            )
            tokens = [count_tokens(messages_for(context)) for context in contexts]
            if any(value > budget for value in tokens):
                raise AssertionError(f"over-budget pack: {record['id']}")
            omissions.extend({"id": record["id"], **gap} for gap in source_coverage_gaps(pipeline._visible_record(record), contexts))
            rows.append({"id": record["id"], "final_passes": len(contexts), "tokens": tokens})
        stage_calls = sum(len(pipeline.contexts_for_record(record)) for record in records)
        final_calls = sum(row["final_passes"] for row in rows)
        result["scenarios"][name] = {
            "procedure_excerpts_per_field": per_field,
            "generic_stage_calls": stage_calls if include_generic else 0,
            "procedure_stage_calls": stage_calls,
            "final_calls": final_calls,
            "total_calls": stage_calls * (2 if include_generic else 1) + final_calls,
            "final_pass_distribution": dict(sorted(Counter(row["final_passes"] for row in rows).items())),
            "source_document_omission_count": len(omissions),
            "rows": rows,
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = profile(args.config, args.predictions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({**result, "scenarios": {name: {key: value for key, value in scenario.items() if key != "rows"} for name, scenario in result["scenarios"].items()}}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
