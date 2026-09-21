#!/usr/bin/env python3
"""Verify organizer product-row conditions reach exact final rendered inputs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.inspect_prompt import build_pipeline_for_preview
from scripts.profile_context_admission import _token_counter
from src.config import load_config
from src.data import (
    competition_product_fact,
    load_competition_product_index,
    load_record_id_panel,
    load_records,
    select_records_by_id,
)
from src.prompt import build_fact_inventory_system_prompt


def _non_source_prefix(user_message: str) -> str:
    """Return prompt-owned context while excluding unchanged notice source text."""
    boundaries = ("[공고 자료 원문]", "# 공고 자료")
    positions = [user_message.find(value) for value in boundaries]
    positions = [value for value in positions if value >= 0]
    return user_message[: min(positions)] if positions else user_message


def _coded_metadata_identifiers(record: dict) -> set[str]:
    meta = record.get("meta", {})
    product_codes = re.findall(r"\[\s*(\d{10})\s*\]", str(meta.get("세부품명번호목록") or ""))
    license_codes = re.findall(r"\(\s*(\d{4})\s*\)", str(meta.get("면허업종제한목록") or ""))
    return set(product_codes + license_codes)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--all-records", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    if config.competition_product_context_mode != "conditions_and_provenance_v2":
        raise ValueError("audit requires conditions_and_provenance_v2")
    if config.competition_products_path is None:
        raise ValueError("audit requires competition_products_path")

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        config.llm.tokenizer_source or config.llm.model
    )
    counter = _token_counter(tokenizer)
    pipeline = build_pipeline_for_preview(config, count_tokens=counter)
    products = load_competition_product_index(config.competition_products_path)
    records = load_records(config.data.input_path)
    if config.data.fast_panel_ids_path and not args.all_records:
        records = select_records_by_id(
            records, load_record_id_panel(config.data.fast_panel_ids_path)
        )

    rows = []
    failures: list[str] = []
    rendered_pass_count = 0
    stage_one_rendered_pass_count = 0
    metadata_identifier_record_count = 0
    metadata_identifier_leak_count = 0
    for record in records:
        fact = competition_product_fact(record, products)
        conditional = [
            product for product in fact["matched_products"]
            if str(product.get("특이사항", "")).strip()
        ]
        contexts = pipeline.contexts_for_record(record)
        messages = [pipeline.messages_for_context(record, context) for context in contexts]
        rendered_pass_count += len(messages)
        rendered_prefixes = [
            _non_source_prefix(pack[1]["content"])
            for pack in messages
        ]
        if config.staged_run and config.staged_run.mode == "fact_inventory_full_final_v1":
            inventory_system = build_fact_inventory_system_prompt()
            navigation_messages = [
                pipeline.navigation_messages_for_context(
                    record, context, inventory_system, source_only=False,
                )[1]
                for context in contexts
            ]
            stage_one_rendered_pass_count += len(navigation_messages)
            rendered_prefixes.extend(
                _non_source_prefix(pack[1]["content"])
                for pack in navigation_messages
            )
        metadata_identifiers = _coded_metadata_identifiers(record)
        if metadata_identifiers:
            metadata_identifier_record_count += 1
        leaked_metadata_identifiers = sorted({
            identifier
            for identifier in metadata_identifiers
            if any(identifier in prefix for prefix in rendered_prefixes)
        })
        if leaked_metadata_identifiers:
            metadata_identifier_leak_count += 1
            failures.append(
                f"{record['id']}: coded metadata identifiers leaked "
                f"{leaked_metadata_identifiers}"
            )
        if not conditional:
            continue
        missing_conditions = sorted({
            str(product["특이사항"])
            for product in conditional
            if any(str(product["특이사항"]) not in pack[1]["content"] for pack in messages)
        })
        leaked_codes = sorted({
            str(product["세부품명번호"])
            for product in conditional
            if any(
                str(product["세부품명번호"]) in prefix
                for prefix in rendered_prefixes
            )
        })
        leaked_doc_ids = sorted({
            str(source["doc_id"])
            for product in conditional
            for source in product.get("document_match_sources", [])
            if any(str(source["doc_id"]) in prefix for prefix in rendered_prefixes)
        })
        if missing_conditions:
            failures.append(f"{record['id']}: missing conditions {missing_conditions}")
        if leaked_codes or leaked_doc_ids:
            failures.append(
                f"{record['id']}: internal identifiers leaked "
                f"codes={leaked_codes}, doc_ids={leaked_doc_ids}"
            )
        rows.append({
            "id": record["id"],
            "pass_count": len(messages),
            "conditions": [str(product["특이사항"]) for product in conditional],
            "source_types": sorted({
                str(source["type"])
                for product in conditional
                for source in product.get("document_match_sources", [])
            }),
            "metadata_match": any(product.get("metadata_match") for product in conditional),
            "missing_conditions": missing_conditions,
            "leaked_codes": leaked_codes,
            "leaked_doc_ids": leaked_doc_ids,
        })

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "config": str(config.path.relative_to(ROOT)),
        "record_count": len(records),
        "conditional_match_record_count": len(rows),
        "conditional_match_pass_count": sum(row["pass_count"] for row in rows),
        "rendered_record_count": len(records),
        "rendered_pass_count": rendered_pass_count,
        "stage_one_rendered_pass_count": stage_one_rendered_pass_count,
        "coded_metadata_record_count": metadata_identifier_record_count,
        "coded_metadata_leak_record_count": metadata_identifier_leak_count,
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "records": rows,
    }
    output_dir.joinpath("product_condition_delivery_audit.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Product condition delivery audit", "",
        f"- Config: `{result['config']}`",
        f"- Records: {result['record_count']}",
        f"- Conditional matches: {result['conditional_match_record_count']}",
        f"- Final rendered passes checked: {result['conditional_match_pass_count']}",
        f"- All rendered records/passes checked: {result['rendered_record_count']} / {result['rendered_pass_count']}",
        f"- Source-first stage-one passes checked: {result['stage_one_rendered_pass_count']}",
        f"- Records with coded metadata: {result['coded_metadata_record_count']}",
        f"- Coded-metadata leak records: {result['coded_metadata_leak_record_count']}",
        f"- Status: **{result['status']}**", "",
    ]
    if failures:
        lines.extend(["## Failures", "", *[f"- {value}" for value in failures], ""])
    lines.extend(["## Records", ""])
    lines.extend(
        f"- `{row['id']}`: {row['pass_count']} pass(es); "
        f"conditions={row['conditions']}; sources={row['source_types']}"
        for row in rows
    )
    output_dir.joinpath("product_condition_delivery_audit.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
