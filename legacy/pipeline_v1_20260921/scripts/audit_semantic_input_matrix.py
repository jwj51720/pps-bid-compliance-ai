#!/usr/bin/env python3
"""Audit what the configured prompt actually supplies to every v item.

This is an offline admission gate.  It deliberately does not call an LLM, edit
cards, or infer labels.  Its inputs are the versioned semantic contract, the
organizer item table/records, the legal-condition ledger, and the exact shared
prompt builder selected by a config.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.inspect_prompt import build_pipeline_for_preview
from src.config import load_config
from src.data import load_item_table, load_records
from src.prompt import DOCUMENT_ORDER, OFFICIAL_BASELINE_META_FIELDS
from src.schema import ITEMS

CONTRACT_HEADER = (
    "| Item | Applicability and 1-condition | Material 0-condition / exception | "
    "Required notice scope | Required metadata / organizer fact | Ledger source family |"
)
META_FIELD_NAMES = tuple(OFFICIAL_BASELINE_META_FIELDS)


def parse_contract(path: Path) -> dict[str, dict[str, str]]:
    """Read the canonical human-reviewed contract table without inventing facts."""
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index(CONTRACT_HEADER) + 2
    except ValueError as error:
        raise ValueError(f"semantic-contract table header not found: {path}") from error

    entries: dict[str, dict[str, str]] = {}
    for line in lines[start:]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 6 or not re.fullmatch(r"v(?:[1-9]|1[0-9]|2[0-4])", cells[0]):
            raise ValueError(f"malformed semantic-contract row: {line}")
        item, condition, zero_condition, scope, facts, source_family = cells
        if not all((condition, zero_condition, scope, facts, source_family)):
            raise ValueError(f"empty semantic-contract cell for {item}")
        unresolved = ("same as v", "regional fields", "업종 fields")
        if any(token in facts.lower() for token in unresolved):
            raise ValueError(
                f"semantic-contract facts must name actual organizer fields, not aliases: {item}"
            )
        if item in entries:
            raise ValueError(f"duplicate semantic-contract item: {item}")
        entries[item] = {
            "condition": condition,
            "zero_condition": zero_condition,
            "required_notice_scope": scope,
            "required_facts": facts,
            "ledger_source_family": source_family,
        }
    if tuple(entries) != ITEMS:
        raise ValueError(
            "semantic contract must contain v1..v24 exactly once in order; "
            f"got {list(entries)}"
        )
    return entries


def ledger_item_coverage(path: Path) -> dict[str, list[dict[str, str]]]:
    """Return retained official-source provenance for each item."""
    ledger = json.loads(path.read_text(encoding="utf-8"))
    coverage: dict[str, list[dict[str, str]]] = {item: [] for item in ITEMS}
    for entry_key, entry in ledger["entries"].items():
        for item_entry in entry["items"]:
            item = item_entry["item"]
            if item not in coverage:
                raise ValueError(f"unknown ledger item {item} in {entry_key}")
            coverage[item].append(
                {
                    "entry": entry_key,
                    "profile": str(entry["profile"]),
                    "group": str(entry["group"]),
                    "source_chunk_keys": ", ".join(item_entry["source_chunk_keys"]),
                }
            )
    missing = [item for item, sources in coverage.items() if not sources]
    if missing:
        raise ValueError(f"ledger has no source provenance for: {', '.join(missing)}")
    return coverage


def required_meta_fields(required_facts: str) -> list[str]:
    return [field for field in META_FIELD_NAMES if field in required_facts]


def _rendered_document_types(context: str) -> set[str]:
    return {
        document_type
        for document_type in DOCUMENT_ORDER
        if re.search(r"\[" + re.escape(document_type) + r":[^\]\n]+\]", context)
    }


def document_coverage(records: list[dict[str, Any]], pipeline: Any) -> dict[str, dict[str, int]]:
    """Measure document presence versus actual single-context admission."""
    counts = {document_type: Counter() for document_type in DOCUMENT_ORDER}
    for record in records:
        contexts = pipeline.contexts_for_record(record)
        if len(contexts) != 1:
            raise ValueError(
                "semantic matrix is only valid for one-context policies; "
                f"{record['id']} yielded {len(contexts)} contexts"
            )
        messages = pipeline.messages_for_context(record, contexts[0])
        rendered_types = _rendered_document_types(messages[1]["content"])
        source_types = {document["type"] for document in record["docs"]}
        for document_type in DOCUMENT_ORDER:
            if document_type not in source_types:
                counts[document_type]["absent_in_notice"] += 1
            elif document_type in rendered_types:
                counts[document_type]["rendered"] += 1
            else:
                counts[document_type]["present_but_omitted"] += 1
    return {
        document_type: {
            "absent_in_notice": counts[document_type]["absent_in_notice"],
            "rendered": counts[document_type]["rendered"],
            "present_but_omitted": counts[document_type]["present_but_omitted"],
        }
        for document_type in DOCUMENT_ORDER
    }


def metadata_coverage(records: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for field in META_FIELD_NAMES:
        present = sum(1 for record in records if field in record["meta"])
        non_null = sum(1 for record in records if record["meta"].get(field) is not None)
        result[field] = {
            "rendered_when_key_present": present,
            "non_null_value": non_null,
            "absent_key": len(records) - present,
        }
    return result


def render_message_markdown(record_id: str, messages: list[dict[str, str]]) -> str:
    return (
        f"# Exact rendered baseline input: {record_id}\n\n"
        "Generated offline through `BaselinePipeline`; no API call was made.\n\n"
        "## System message\n\n```text\n"
        + messages[0]["content"]
        + "\n```\n\n## User message\n\n```text\n"
        + messages[1]["content"]
        + "\n```\n"
    )


def audit(config_path: Path, contract_path: Path, ledger_path: Path, output_dir: Path,
          review_ids: list[str]) -> dict[str, Any]:
    config = load_config(config_path)
    if config.prompt_profile != "official_baseline_v1":
        raise ValueError("this baseline semantic audit requires prompt.profile=official_baseline_v1")
    if config.context_strategy != "single" or config.max_document_chars != 4000:
        raise ValueError("this baseline semantic audit requires single 4,000-character context")
    if config.decision_cards_path or config.competition_products_path or config.reference_path:
        raise ValueError("baseline semantic audit requires no cards, product facts, or references")

    contract = parse_contract(contract_path)
    ledger = ledger_item_coverage(ledger_path)
    records = load_records(config.data.input_path)
    item_table = load_item_table(config.data.item_table_path)
    pipeline = build_pipeline_for_preview(config)
    first_record = records[0]
    first_context = pipeline.contexts_for_record(first_record)
    if len(first_context) != 1:
        raise AssertionError("baseline policy unexpectedly generated multiple contexts")
    system_message = pipeline.messages_for_context(first_record, first_context[0])[0]["content"]

    output_dir.mkdir(parents=True, exist_ok=True)
    review_dir = output_dir / "rendered_inputs"
    review_dir.mkdir(exist_ok=True)
    record_by_id = {record["id"]: record for record in records}
    rendered_reviews: list[str] = []
    for record_id in review_ids:
        record = record_by_id.get(record_id)
        if record is None:
            raise ValueError(f"review record not found: {record_id}")
        contexts = pipeline.contexts_for_record(record)
        if len(contexts) != 1:
            raise ValueError(f"review record {record_id} is not single-context")
        messages = pipeline.messages_for_context(record, contexts[0])
        destination = review_dir / f"{record_id.lower()}.messages.md"
        destination.write_text(render_message_markdown(record_id, messages), encoding="utf-8")
        rendered_reviews.append(str(destination))

    doc_coverage = document_coverage(records, pipeline)
    meta_coverage = metadata_coverage(records)
    rows: list[dict[str, Any]] = []
    for item in ITEMS:
        definition = item_table[item]
        raw_line = f"- {item}: {definition['항목명']}"
        if definition.get("비고"):
            raw_line += f" ({definition['비고']})"
        if definition.get("부재탐지"):
            raw_line += "  [근거 없음 — null]"
        if raw_line not in system_message:
            raise ValueError(f"exact baseline item line missing from system message: {item}")
        fields = required_meta_fields(contract[item]["required_facts"])
        rows.append(
            {
                "item": item,
                "item_name": definition["항목명"],
                "absence_item": bool(definition.get("부재탐지")),
                "baseline_system_item_line": raw_line,
                "baseline_has_item_specific_condition": False,
                "baseline_has_material_exception": False,
                "baseline_has_csv_applicability_fact": False,
                "required_condition": contract[item]["condition"],
                "required_zero_condition": contract[item]["zero_condition"],
                "required_notice_scope": contract[item]["required_notice_scope"],
                "required_metadata_fields": fields,
                "requires_csv_fact": "CSV" in contract[item]["required_facts"],
                "ledger_provenance": ledger[item],
            }
        )

    report = {
        "audit_version": 1,
        "config": str(config_path),
        "contract": str(contract_path),
        "ledger": str(ledger_path),
        "record_count": len(records),
        "policy": {
            "prompt_profile": config.prompt_profile,
            "context_strategy": config.context_strategy,
            "max_document_chars": config.max_document_chars,
            "decision_cards": False,
            "competition_products": False,
            "law_reference": False,
        },
        "baseline_system_contains_item_specific_conditions": False,
        "baseline_system_contains_item_specific_exceptions": False,
        "baseline_user_contains_competition_product_csv_facts": False,
        "metadata_field_coverage": meta_coverage,
        "document_type_coverage": doc_coverage,
        "reviewed_rendered_inputs": rendered_reviews,
        "items": rows,
    }
    (output_dir / "semantic_input_matrix.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "semantic_input_matrix.md").write_text(render_markdown(report), encoding="utf-8")
    return report


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Semantic Input Matrix — exact organizer baseline",
        "",
        "This is an offline rendered-input audit, not a score experiment. `없음` means "
        "the required fact is not in this canonical prompt; it does not mean the fact is false.",
        "",
        "## Policy verified",
        "",
        f"- Records audited: {report['record_count']}",
        "- One 4,000-character ordered context; no card, competition-product CSV fact, or law reference.",
        "- Every v line is present, but item-specific applicability/exception conditions are absent.",
        "",
        "## Per-item matrix",
        "",
        "| v | Exact baseline system line | Condition / material exception | Required prompt-visible facts | Notice scope risk | Ledger provenance |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["items"]:
        required = ", ".join(row["required_metadata_fields"]) or "없음"
        if row["requires_csv_fact"]:
            required += "; CSV 필요(미주입)"
        provenance = "; ".join(
            f"{entry['profile']}/{entry['group']}" for entry in row["ledger_provenance"]
        )
        lines.append(
            f"| {row['item']} | `{row['baseline_system_item_line']}` | "
            f"미주입 / 미주입 | {required} | {row['required_notice_scope']} | {provenance} |"
        )
    lines += ["", "## Actual document admission across dev-200", "",
              "| Document type | Rendered | Present but omitted | Absent in notice |",
              "| --- | ---: | ---: | ---: |"]
    for document_type, counts in report["document_type_coverage"].items():
        lines.append(
            f"| {document_type} | {counts['rendered']} | {counts['present_but_omitted']} | {counts['absent_in_notice']} |"
        )
    lines += ["", "## Required interpretation", "",
              "- This baseline can test the organizer's minimal prompt, not the legal-condition hypothesis in the semantic contract.",
              "- An item requiring omitted document types or exact competition-product CSV facts is structurally under-informed in this policy.",
              "- Do not turn this report into cards, Python rules, RAG, grouping, or a paid experiment without a separately declared hypothesis and rendered-input review.",
              "", "## Human-review files", ""]
    lines += [f"- `{path}`" for path in report["reviewed_rendered_inputs"]]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--contract", default="docs/semantic_input_contract_v1.md")
    parser.add_argument("--ledger", default="data/derived/legal_condition_ledger_v1.json")
    parser.add_argument("--output-dir", default="outputs/semantic-input-matrix-v1")
    parser.add_argument("--review-record-id", action="append", dest="review_ids")
    args = parser.parse_args()
    review_ids = args.review_ids or ["PPS-DEV-062", "PPS-DEV-042", "PPS-DEV-01"]
    report = audit(Path(args.config), Path(args.contract), Path(args.ledger), Path(args.output_dir), review_ids)
    print(Path(args.output_dir) / "semantic_input_matrix.md")
    print(f"audited {report['record_count']} records and {len(report['items'])} items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
