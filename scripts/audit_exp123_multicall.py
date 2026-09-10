#!/usr/bin/env python3
"""Offline semantic and topology audit for EXP123 multi-call candidates.

No model call or label is used.  The audit treats EXP123 as the incumbent and
measures only source/prompt ownership, document admission, and call topology.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_semantic_input_matrix import ledger_item_coverage, parse_contract
from src.data import load_decision_cards, load_item_table, load_records
from src.prompt import DOCUMENT_ORDER, build_messages, build_official_baseline_context, build_system_prompt
from src.schema import ITEMS

EXP123_RULE_SOURCE = ROOT / "incubator/submission_candidates/exp123_card_v6_frozen_rules/src/frozen_rules.py"
EXP123_CARD_PATH = ROOT / "data/derived/decision_cards_v6.json"
EXP123_CONTEXT_CHARS = 4000
EXP123_RUNTIME_MINUTES = 37 + 14 / 60
EXP135_TWO_CALL_MINUTES = 93 + 28 / 60

GROUPS: dict[str, tuple[str, ...]] = {
    "qualification": ("v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v21"),
    "product_and_absence": ("v10", "v11", "v12", "v13", "v14", "v15", "v16", "v17", "v18"),
    "document_procedure_consistency": ("v9", "v19", "v20", "v22", "v23", "v24"),
}


def validate_groups(groups: dict[str, tuple[str, ...]] = GROUPS) -> None:
    flattened = tuple(item for group in groups.values() for item in group)
    if len(flattened) != len(set(flattened)) or set(flattened) != set(ITEMS):
        raise ValueError("multi-call groups must partition v1..v24 exactly once")


def load_exp123_rule_items(source: Path = EXP123_RULE_SOURCE) -> tuple[str, ...]:
    """Read the isolated archive's actual override loop, not a remembered list."""
    text = source.read_text(encoding="utf-8")
    expected = '("v2", _v2(record)), ("v3", _v3(record)), ("v21", _v21(record))'
    if expected not in text or "for document in record[\"docs\"]" not in text:
        raise ValueError("EXP123 frozen-rule source no longer matches the audited archive contract")
    return ("v2", "v3", "v21")


def document_admission(records: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    counts = {document_type: Counter() for document_type in DOCUMENT_ORDER}
    for record in records:
        context = build_official_baseline_context(record, EXP123_CONTEXT_CHARS)
        for document_type in DOCUMENT_ORDER:
            source_present = any(document["type"] == document_type for document in record["docs"])
            rendered = f"[{document_type}:" in context
            if not source_present:
                counts[document_type]["absent_in_notice"] += 1
            elif rendered:
                counts[document_type]["rendered"] += 1
            else:
                counts[document_type]["present_but_omitted"] += 1
    return {document_type: dict(counts[document_type]) for document_type in DOCUMENT_ORDER}


def group_messages(
    record: dict[str, Any], item_table: dict[str, dict[str, Any]],
    cards: dict[str, dict[str, Any]], active_items: tuple[str, ...],
) -> list[dict[str, str]]:
    """Render a proposed group call without claiming it is runnable policy."""
    system = build_system_prompt(
        item_table,
        profile="official_baseline_subset_v1",
        decision_cards=cards,
        active_items=active_items,
        output_mode="labels_and_evidence",
        layout="plain",
    )
    return build_messages(
        record,
        system,
        EXP123_CONTEXT_CHARS,
        prompt_profile="official_baseline_subset_v1",
        metadata_style="official_lines",
        output_mode="labels_and_evidence",
    )


def render_messages(label: str, messages: list[dict[str, str]]) -> str:
    return (
        f"# {label}\n\n"
        "Offline prototype only. It was rendered through the shared prompt builder; no model call was made.\n\n"
        "## System\n\n```text\n" + messages[0]["content"]
        + "\n```\n\n## User\n\n```text\n" + messages[1]["content"] + "\n```\n"
    )


def summarize_group_prompt_lengths(
    records: list[dict[str, Any]], item_table: dict[str, dict[str, Any]],
    cards: dict[str, dict[str, Any]],
) -> dict[str, dict[str, float]]:
    summary: dict[str, dict[str, float]] = {}
    for name, items in GROUPS.items():
        lengths = [
            sum(len(message["content"]) for message in group_messages(record, item_table, cards, items))
            for record in records
        ]
        lengths.sort()
        summary[name] = {
            "calls_per_notice": 1,
            "items": len(items),
            "min_message_chars": lengths[0],
            "median_message_chars": lengths[len(lengths) // 2],
            "p95_message_chars": lengths[round((len(lengths) - 1) * 0.95)],
            "max_message_chars": lengths[-1],
        }
    return summary


def architecture_topology() -> dict[str, dict[str, Any]]:
    linear_two = EXP123_RUNTIME_MINUTES * 2
    return {
        "A_disjoint_three_groups": {
            "first_stage_calls": 3,
            "conditional_second_stage": False,
            "min_calls": 3,
            "max_calls": 3,
            "final_label_owner": "one disjoint group per item; concatenate; then EXP123 v2/v3/v21 override",
            "linear_runtime_minutes": round(EXP123_RUNTIME_MINUTES * 3, 2),
            "guarded_runtime_minutes": round(EXP135_TWO_CALL_MINUTES * 1.5, 2),
            "submission_status": "analysis_only until exact staged vLLM measurement",
        },
        "B_triage_then_strict": {
            "first_stage_calls": 1,
            "conditional_second_stage": True,
            "min_calls": 1,
            "max_calls": 2,
            "final_label_owner": "strict final pass; triage is never evidence or final label",
            "linear_runtime_minutes_if_all_routed": round(linear_two, 2),
            "guarded_runtime_minutes_if_all_routed": round(EXP135_TWO_CALL_MINUTES, 2),
            "submission_status": "needs triage schema, coverage gate, and fallback implementation",
        },
        "C_locator_then_final": {
            "first_stage_calls": 1,
            "conditional_second_stage": True,
            "min_calls": 1,
            "max_calls": 2,
            "final_label_owner": "strict final pass; locator text is a non-authoritative navigation aid",
            "linear_runtime_minutes_if_all_routed": round(linear_two, 2),
            "guarded_runtime_minutes_if_all_routed": round(EXP135_TWO_CALL_MINUTES, 2),
            "submission_status": "needs locator schema, absence routing, and fallback implementation",
        },
    }


def audit(output_dir: Path, review_ids: list[str]) -> dict[str, Any]:
    validate_groups()
    rules = load_exp123_rule_items()
    item_table = load_item_table(ROOT / "data/raw/open/data/항목표.json")
    cards = load_decision_cards(EXP123_CARD_PATH, item_table)
    records = load_records(ROOT / "data/raw/open/dev.jsonl.gz")
    contract = parse_contract(ROOT / "docs/semantic_input_contract_v1.md")
    ledger = ledger_item_coverage(ROOT / "data/derived/legal_condition_ledger_v1.json")
    sample_system = build_system_prompt(
        item_table, profile="official_baseline_v1", decision_cards=cards,
        output_mode="labels_and_evidence", layout="plain",
    )
    rows = []
    for item in ITEMS:
        card = cards[item]["prompt_text"]
        if card not in sample_system:
            raise ValueError(f"EXP123 card not rendered for {item}")
        rows.append({
            "item": item,
            "card_rendered": True,
            "card_text": card,
            "required_notice_scope": contract[item]["required_notice_scope"],
            "required_facts": contract[item]["required_facts"],
            "ledger_provenance_count": len(ledger[item]),
            "final_owner": "EXP123 frozen rule" if item in rules else "Gemma V/E",
            "full_source_python_predicate": item in rules,
            "requires_exact_product_lookup": "제공된 경쟁제품 조회" in card or "제공된 조회상" in card,
            "product_lookup_rendered": False,
            "requires_complete_notice": "All supplied documents" in contract[item]["required_notice_scope"],
        })
    output_dir.mkdir(parents=True, exist_ok=True)
    review_dir = output_dir / "group_prompt_review"
    review_dir.mkdir(exist_ok=True)
    records_by_id = {record["id"]: record for record in records}
    rendered = []
    for record_id in review_ids:
        record = records_by_id.get(record_id)
        if record is None:
            raise ValueError(f"review record not found: {record_id}")
        for name, items in GROUPS.items():
            destination = review_dir / f"{record_id.lower()}.{name}.messages.md"
            destination.write_text(
                render_messages(f"Prototype A group={name}, notice={record_id}", group_messages(record, item_table, cards, items)),
                encoding="utf-8",
            )
            rendered.append(str(destination))
    report = {
        "audit_version": 1,
        "labels_read": False,
        "incumbent": {
            "archive": "dist/pps_20260906_233304.zip",
            "public_macro_positive_f1": 0.260445711,
            "runtime_minutes": EXP123_RUNTIME_MINUTES,
            "document_context": "ordered 4000-character single context",
            "card_path": str(EXP123_CARD_PATH.relative_to(ROOT)),
            "frozen_rule_source": str(EXP123_RULE_SOURCE.relative_to(ROOT)),
            "frozen_rule_items": rules,
        },
        "item_matrix": rows,
        "document_admission_dev200": document_admission(records),
        "architecture_groups": {name: list(items) for name, items in GROUPS.items()},
        "group_prompt_length_dev200": summarize_group_prompt_lengths(records, item_table, cards),
        "architectures": architecture_topology(),
        "rendered_group_prompt_review": rendered,
        "limitations": [
            "Character counts and historic OpenRouter runtime are not exact vLLM tokenizer/throughput measurements.",
            "B and C have contracts only; their prompts and schemas are not implemented or runnable yet.",
            "No label, model response, score, or public-quality claim is included.",
        ],
    }
    (output_dir / "exp123_multicall_audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "exp123_multicall_audit.md").write_text(render_markdown(report), encoding="utf-8")
    return report


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# EXP123 multi-call offline audit",
        "",
        "No labels or model calls were used. This report is an admission/topology audit, not a quality result.",
        "",
        "## Incumbent", "",
        "- EXP123 public Macro positive-F1: `0.260445711`",
        "- EXP123 runtime: `37m 14s`",
        "- Frozen full-source override items: `v2`, `v3`, `v21`",
        "- All other items retain Gemma V/E ownership.",
        "",
        "## EXP123 item ownership", "",
        "| Item | card v6 rendered | final owner | full-source Python predicate | unresolved rendered-input gap |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in report["item_matrix"]:
        gaps = []
        if row["requires_exact_product_lookup"] and not row["product_lookup_rendered"]:
            gaps.append("card가 전제한 경쟁제품 조회 미주입")
        if row["requires_complete_notice"]:
            gaps.append("전체 문서 부재검토이나 4k single")
        lines.append(
            f"| {row['item']} | yes | {row['final_owner']} | "
            f"{'yes' if row['full_source_python_predicate'] else 'no'} | {'; '.join(gaps) or '없음'} |"
        )
    lines += ["", "## 4k document admission, dev-200", "",
              "| type | rendered | present but omitted | absent |",
              "| --- | ---: | ---: | ---: |"]
    for document_type, counts in report["document_admission_dev200"].items():
        lines.append(
            f"| {document_type} | {counts.get('rendered', 0)} | "
            f"{counts.get('present_but_omitted', 0)} | {counts.get('absent_in_notice', 0)} |"
        )
    lines += ["", "## Candidate topology", "",
              "| architecture | calls/notice | final owner | linear minutes | guarded minutes | status |",
              "| --- | --- | --- | ---: | ---: | --- |"]
    for name, value in report["architectures"].items():
        linear = value.get("linear_runtime_minutes", value.get("linear_runtime_minutes_if_all_routed"))
        guarded = value.get("guarded_runtime_minutes", value.get("guarded_runtime_minutes_if_all_routed"))
        lines.append(
            f"| {name} | {value['min_calls']}–{value['max_calls']} | {value['final_label_owner']} | "
            f"{linear} | {guarded} | {value['submission_status']} |"
        )
    lines += ["", "## A-group prototype prompt length, dev-200", "",
              "| group | items | median chars | p95 chars | max chars |",
              "| --- | ---: | ---: | ---: | ---: |"]
    for name, value in report["group_prompt_length_dev200"].items():
        lines.append(
            f"| {name} | {value['items']} | {value['median_message_chars']} | "
            f"{value['p95_message_chars']} | {value['max_message_chars']} |"
        )
    lines += ["", "## Required next work", "",
              "- Read the nine A-group fixture messages before any A paid run.",
              "- Implement B and C only as complete contracts: schema, routing, fallback, final-owner rule, mock, and evidence validation together.",
              "- Do not interpret the runtime columns as vLLM proof."]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="outputs/exp123-multicall-audit-v1")
    parser.add_argument("--review-record-id", action="append", dest="review_ids")
    args = parser.parse_args()
    report = audit(Path(args.output_dir), args.review_ids or ["PPS-DEV-062", "PPS-DEV-042", "PPS-DEV-01"])
    print(Path(args.output_dir) / "exp123_multicall_audit.md")
    print(f"audited {len(report['item_matrix'])} items without labels or model calls")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
