#!/usr/bin/env python3
"""Audit a candidate's exact rendered final input against the v-item contract.

This is an offline admission gate.  It deliberately does not read labels or
predictions and never calls a provider.  A ``fail`` is not a model-quality
claim: it means the configured architecture does not yet supply what it says
it will use for that active item.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_semantic_input_matrix import (  # noqa: E402
    DOCUMENT_ORDER,
    ledger_item_coverage,
    parse_contract,
    required_meta_fields,
)
from scripts.inspect_prompt import build_pipeline_for_preview  # noqa: E402
from scripts.inspect_grouped_prompt import build_grouped_previews  # noqa: E402
from src.config import load_config  # noqa: E402
from src.data import load_decision_cards, load_item_table, load_records  # noqa: E402
from src.prompt import (  # noqa: E402
    _render_card_text,
    append_fact_inventory,
    append_locator_navigation,
    build_fact_inventory_system_prompt,
    build_messages,
    build_official_baseline_context,
)
from src.schema import (  # noqa: E402
    ABSENCE_ITEMS,
    FACT_INVENTORY_CATEGORIES,
    FACT_INVENTORY_CATEGORIES_V2,
    ITEMS,
)


def document_types_from_scope(scope: str) -> tuple[set[str], str | None]:
    """Apply the contract's explicit full-document admission invariant.

    The organizer only guarantees that violations may occur in attachments; it
    does not authorize us to narrow a v item to one source type.  The table's
    scope cell remains useful common-location guidance, but cannot lower the
    required source coverage for an active final judgment.
    """
    del scope
    return set(DOCUMENT_ORDER), None


def rendered_document_types(message: str) -> set[str]:
    return {
        document_type
        for document_type in DOCUMENT_ORDER
        if re.search(r"\[" + re.escape(document_type) + r":[^\]\n]+\]", message)
    }


def final_messages_for_record(pipeline: Any, record: dict[str, Any], staged_mode: str | None) -> list[dict[str, str]]:
    """Build the final-stage messages without pretending a first-stage result exists."""
    pipeline, _ = pipeline.effective_pipeline_for_record(record)
    contexts = pipeline.contexts_for_record(record)
    if len(contexts) != 1:
        raise ValueError(
            f"candidate semantic audit requires one final context; {record['id']} yielded {len(contexts)}"
        )
    messages = pipeline.messages_for_context(record, contexts[0])
    if staged_mode == "locator_then_final_v1":
        locator_items = tuple(item for item in pipeline.active_items if item not in ABSENCE_ITEMS)
        # Missing locator text is deliberately non-authoritative.  This is the
        # safest exact preview of the final-stage prompt independent of model output.
        messages = append_locator_navigation(
            messages, {item: "" for item in locator_items}, locator_items
        )
    return messages


def _span(text: str, needle: str) -> dict[str, int] | None:
    index = text.find(needle)
    if index < 0:
        return None
    return {"start": index, "end": index + len(needle)}


def metadata_field_span(text: str, field: str, metadata_style: str) -> dict[str, int] | None:
    """Locate a fact in the configured human-readable or JSON rendering."""
    if metadata_style == "official_lines":
        return _span(text, f"- {field}:")
    return _span(text, f'"{field}"')


def audit(config_path: Path, contract_path: Path, ledger_path: Path, output_dir: Path,
          review_ids: list[str]) -> dict[str, Any]:
    config = load_config(config_path)
    contract = parse_contract(contract_path)
    ledger = ledger_item_coverage(ledger_path)
    records = load_records(config.data.input_path)
    by_id = {record["id"]: record for record in records}
    grouped = bool(config.raw.get("grouped_run"))
    pipeline = None if grouped else build_pipeline_for_preview(config)
    active_items = tuple(config.active_items or ITEMS)
    staged_mode = config.staged_run.mode if config.staged_run else None
    policy_failures: list[str] = []
    if config.metadata_style == "full_json":
        policy_failures.append(
            "metadata_style=full_json exposes raw metadata JSON rather than the required human-readable item facts"
        )

    if not review_ids:
        attachment = next((record["id"] for record in records if len(record["docs"]) > 1), None)
        longest = max(records, key=lambda record: sum(len(doc["text"]) for doc in record["docs"]))["id"]
        review_ids = [records[0]["id"], attachment or records[0]["id"], longest]
    missing_ids = [record_id for record_id in review_ids if record_id not in by_id]
    if missing_ids:
        raise ValueError(f"review records not found: {', '.join(missing_ids)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    rendered_dir = output_dir / "rendered_inputs"
    rendered_dir.mkdir(exist_ok=True)
    sample_messages: dict[str, list[dict[str, str]]] = {}
    sample_active_items: dict[str, tuple[str, ...]] = {}
    sample_gated_items: dict[str, dict[str, str]] = {}
    source_stage_messages: dict[str, list[list[dict[str, str]]]] = {}
    sample_previews: dict[str, list[dict[str, Any]]] = {}
    for record_id in review_ids:
        if grouped:
            previews = build_grouped_previews(config, by_id[record_id])
            sample_previews[record_id] = previews
            lines = [
                f"# Exact rendered grouped final input: {record_id}", "",
                "Offline admission preview; no provider call.", "",
            ]
            for preview in previews:
                lines += [
                    f"## {preview['group']} — {', '.join(preview['items'])} — pack {preview['pass_index']}",
                    "", "### System", "", "```text", preview["messages"][0]["content"], "```",
                    "", "### User", "", "```text", preview["messages"][1]["content"], "```", "",
                ]
            rendered_dir.joinpath(f"{record_id.lower()}.grouped.messages.md").write_text(
                "\n".join(lines), encoding="utf-8"
            )
        else:
            assert pipeline is not None
            effective_pipeline, inactive = pipeline.effective_pipeline_for_record(by_id[record_id])
            sample_active_items[record_id] = effective_pipeline.active_items
            sample_gated_items[record_id] = inactive
            if staged_mode in {
                "fact_inventory_then_final_v1",
                "fact_inventory_full_final_v1",
                "fact_inventory_full_final_v2",
                "fact_inventory_full_final_v3",
                "fact_inventory_full_final_v4",
            }:
                visible = pipeline._visible_record(by_id[record_id])
                source_stage_messages[record_id] = [
                    build_messages(
                        visible,
                        build_fact_inventory_system_prompt(
                            4 if staged_mode == "fact_inventory_full_final_v2" else 3,
                            categories=(
                                FACT_INVENTORY_CATEGORIES_V2
                                if staged_mode == "fact_inventory_full_final_v4"
                                else FACT_INVENTORY_CATEGORIES
                            ),
                        ),
                        pipeline.max_document_chars,
                        document_context=(context.text if hasattr(context, "text") else context),
                        prompt_profile=pipeline.prompt_profile,
                        metadata_style=pipeline.metadata_style,
                        output_mode="labels_only",
                    )
                    for context in pipeline.contexts_for_record(by_id[record_id])
                ]
                final_context = (
                    None if staged_mode in {"fact_inventory_full_final_v1", "fact_inventory_full_final_v2", "fact_inventory_full_final_v3", "fact_inventory_full_final_v4"}
                    else build_official_baseline_context(visible, 4000)
                )
                messages = append_fact_inventory(
                    pipeline.messages_for_context(by_id[record_id], final_context),
                    {
                        category: ()
                        for category in (
                            FACT_INVENTORY_CATEGORIES_V2
                            if staged_mode == "fact_inventory_full_final_v4"
                            else FACT_INVENTORY_CATEGORIES
                        )
                    },
                    position=(
                        "before_source"
                        if staged_mode == "fact_inventory_full_final_v3"
                        else "after_source"
                    ),
                    categories=(
                        FACT_INVENTORY_CATEGORIES_V2
                        if staged_mode == "fact_inventory_full_final_v4"
                        else FACT_INVENTORY_CATEGORIES
                    ),
                )
            else:
                messages = final_messages_for_record(pipeline, by_id[record_id], staged_mode)
            sample_messages[record_id] = messages
            rendered = (
                "# Exact rendered final input: " + record_id + "\n\n"
                "Offline admission preview; no provider call.\n\n"
                "## System\n\n```text\n" + messages[0]["content"] + "\n```\n\n"
                "## User\n\n```text\n" + messages[1]["content"] + "\n```\n"
                + ("\n## Navigation message\n\n```text\n" + messages[2]["content"] + "\n```\n"
                   if len(messages) > 2 else "")
            )
            if staged_mode in {
                "fact_inventory_then_final_v1",
                "fact_inventory_full_final_v1",
                "fact_inventory_full_final_v2",
                "fact_inventory_full_final_v3",
                "fact_inventory_full_final_v4",
            }:
                rendered += "\n## Source fact-collection messages\n"
                for index, source_messages in enumerate(source_stage_messages[record_id], 1):
                    rendered += (
                        f"\n### Source pack {index}\n\n```text\n{source_messages[0]['content']}\n```\n\n"
                        f"```text\n{source_messages[1]['content']}\n```\n"
                    )
            rendered_dir.joinpath(f"{record_id.lower()}.final.messages.md").write_text(rendered, encoding="utf-8")

    item_table = load_item_table(config.data.item_table_path)
    cards = load_decision_cards(config.decision_cards_path, item_table) if config.decision_cards_path else {}

    def grouped_for_item(record_id: str, item: str) -> list[dict[str, Any]]:
        matches = [preview for preview in sample_previews[record_id] if item in preview["items"]]
        if not matches:
            raise ValueError(f"grouped final input has no owner for {item} in {record_id}")
        groups = {preview["group"] for preview in matches}
        if len(groups) != 1:
            raise ValueError(f"grouped final input has overlapping owners for {item}: {sorted(groups)}")
        return matches

    rows: list[dict[str, Any]] = []
    for item in active_items:
        definition = contract[item]
        card_text = str(cards.get(item, {}).get("prompt_text", ""))
        rendered_card_text = (
            _render_card_text(card_text, indent="  ", output_mode=config.output_mode)
            if config.prompt_layout == "markdown_v2" else card_text
        )
        if grouped:
            reference_previews = grouped_for_item(review_ids[0], item)
            system_message = reference_previews[0]["messages"][0]["content"]
            user_messages = "\n".join(
                preview["messages"][1]["content"] for preview in reference_previews
            )
        else:
            active_review_ids = [
                record_id for record_id in review_ids
                if item in sample_active_items[record_id]
            ]
            reference_messages = sample_messages[active_review_ids[0]] if active_review_ids else []
            if not active_review_ids:
                rows.append({
                    "item": item,
                    "card_span": None,
                    "metadata_spans": {},
                    "requires_csv_fact": "CSV" in definition["required_facts"],
                    "csv_fact_supplied": None,
                    "required_notice_scope": definition["required_notice_scope"],
                    "scope_fixture_checks": {
                        record_id: {"gated": True, "reason": sample_gated_items[record_id][item]}
                        for record_id in review_ids
                    },
                    "ledger_provenance": ledger[item],
                    "status": "gated_in_all_review_fixtures",
                    "failures": [],
                })
                continue
            system_message = reference_messages[0]["content"]
            user_messages = "\n".join(message["content"] for message in reference_messages[1:])
        card_span = _span(system_message, rendered_card_text) if rendered_card_text else None
        fields = required_meta_fields(definition["required_facts"])
        field_spans = {
            field: metadata_field_span(user_messages, field, config.metadata_style)
            for field in fields
        }
        csv_required = "CSV" in definition["required_facts"]
        csv_supplied = bool(config.competition_products_path) and any(
            heading in user_messages
            for heading in ("[대회 제공 경쟁제품 고시 확인]", "# 대회 제공 경쟁제품 고시 확인")
        )
        exact_types, scope_error = document_types_from_scope(definition["required_notice_scope"])
        fixture_scope: dict[str, Any] = {}
        for record_id in review_ids:
            if not grouped and item not in sample_active_items[record_id]:
                fixture_scope[record_id] = {
                    "gated": True, "reason": sample_gated_items[record_id][item],
                }
                continue
            source_types = {doc["type"] for doc in by_id[record_id]["docs"]}
            if grouped:
                messages_for_item = grouped_for_item(record_id, item)
                rendered_text = "\n".join(
                    preview["messages"][1]["content"] for preview in messages_for_item
                )
            else:
                messages_for_item = sample_messages[record_id]
                rendered_text = "\n".join(message["content"] for message in messages_for_item[1:])
                if staged_mode in {
                    "fact_inventory_then_final_v1",
                    "fact_inventory_full_final_v1",
                    "fact_inventory_full_final_v2",
                    "fact_inventory_full_final_v3",
                    "fact_inventory_full_final_v4",
                }:
                    rendered_text = "\n".join(
                        message[1]["content"] for message in source_stage_messages[record_id]
                    )
            seen = rendered_document_types(rendered_text)
            required_present = sorted(exact_types & source_types)
            fixture_scope[record_id] = {
                "source_types": sorted(source_types),
                "rendered_types": sorted(seen),
                "required_present_but_omitted": sorted(set(required_present) - seen),
            }
        failures: list[str] = []
        if not card_span:
            failures.append("exact decision-card prompt_text is absent from final system message")
        if any(span is None for span in field_spans.values()):
            failures.append("required organizer metadata field is absent from final user message")
        if csv_required and not csv_supplied:
            failures.append("required organizer CSV fact is not supplied")
        if scope_error:
            failures.append(scope_error)
        if any(
            value.get("required_present_but_omitted", []) for value in fixture_scope.values()
        ):
            failures.append("required source document is present but omitted in a reviewed fixture")
        rows.append({
            "item": item,
            "card_span": card_span,
            "metadata_spans": field_spans,
            "requires_csv_fact": csv_required,
            "csv_fact_supplied": csv_supplied,
            "required_notice_scope": definition["required_notice_scope"],
            "scope_fixture_checks": fixture_scope,
            "ledger_provenance": ledger[item],
            "status": "pass" if not failures else "fail",
            "failures": failures,
        })

    report = {
        "audit_version": 1,
        "config": str(config_path),
        "execution": "grouped final" if grouped else "single final",
        "staged_mode": staged_mode,
        "active_items": list(active_items),
        "active_items_by_fixture": {
            record_id: list(items) for record_id, items in sample_active_items.items()
        },
        "review_ids": review_ids,
        "labels_or_predictions_read": False,
        "provider_called": False,
        "policy_failures": policy_failures,
        "passed": not policy_failures and not any(row["status"] == "fail" for row in rows),
        "items": rows,
    }
    output_dir.joinpath("semantic_contract_audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Candidate semantic-input admission audit",
        "",
        f"- Config: `{config_path}`",
        f"- Staged mode: `{staged_mode or 'single final'}`",
        f"- Reviewed records: {', '.join(review_ids)}",
        "- Labels/predictions read: no; provider called: no.",
        f"- Verdict: **{'PASS' if report['passed'] else 'FAIL — do not run paid experiment'}**",
        "",
        "## Policy-level checks",
        "",
    ]
    lines += ([f"- FAIL: {failure}" for failure in policy_failures] or ["- PASS"])
    lines += [
        "",
        "## Per-item checks",
        "",
        "| Item | Card | Metadata | CSV | Document scope | Verdict |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        metadata = "ok" if all(value is not None for value in row["metadata_spans"].values()) else "missing"
        csv = "n/a" if not row["requires_csv_fact"] else ("ok" if row["csv_fact_supplied"] else "missing")
        scope = "gated" if row["status"] == "gated_in_all_review_fixtures" else ("ok" if not any("scope" in failure or "source document" in failure for failure in row["failures"]) else "fail")
        lines.append(
            f"| {row['item']} | {'ok' if row['card_span'] else 'missing'} | {metadata} | {csv} | {scope} | {row['status']} |"
        )
    lines += ["", "## Failure details", ""]
    for row in rows:
        if row["failures"]:
            lines.append(f"### {row['item']}")
            lines += [f"- {failure}" for failure in row["failures"]]
            lines.append("")
    output_dir.joinpath("semantic_contract_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--contract", default="docs/semantic_input_contract_v1.md")
    parser.add_argument("--ledger", default="data/derived/legal_condition_ledger_v1.json")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--review-id", action="append", default=[])
    args = parser.parse_args()
    report = audit(
        Path(args.config), Path(args.contract), Path(args.ledger), Path(args.output_dir), args.review_id
    )
    print(json.dumps({"passed": report["passed"], "items": len(report["items"])}, ensure_ascii=False))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
