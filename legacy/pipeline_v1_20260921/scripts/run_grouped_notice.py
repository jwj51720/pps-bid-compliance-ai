#!/usr/bin/env python3
"""Diagnose one notice with v-item groups and their minimal official-law bundles.

This is deliberately a one-notice structural probe.  It is not a submission
entrypoint and does not claim a benchmark score; it persists every exact group
input and raw pass result so that grouping quality can be inspected before an
efficient multi-notice orchestrator is introduced.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_experiment import _make_client, _make_token_counter, _write_input_examples_markdown
from src.config import load_config
from src.data import load_competition_product_index, load_decision_cards, load_item_table, load_records
from src.law_bundles import MetadataLawBundleRouter
from src.legal_groups import LEGAL_ITEM_GROUPS, validate_groups
from src.pipeline import BaselinePipeline, PredictionError, judgment_to_row, zero_judgment
from src.submission import write_submission


def _prediction_json(group_id: str, prediction: Any) -> dict[str, Any]:
    return {
        "group": group_id, "judgment": prediction.judgment,
        "raw_response": prediction.raw_response, "model": prediction.model,
        "latency_seconds": prediction.latency_seconds, "usage": prediction.usage,
        "pass_judgments": list(prediction.pass_judgments),
        "parse_errors": list(prediction.parse_errors),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/config.exp019-routed-law-navigation-first20.yaml")
    parser.add_argument("--record-index", type=int, default=0)
    parser.add_argument("--output-dir", default="outputs/exp-021-grouped-one-notice")
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--prompt-layout", choices=("plain", "markdown", "markdown_v2"), default="plain")
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()
    if args.record_index < 0:
        parser.error("--record-index must be non-negative")

    load_dotenv(ROOT / ".env")
    config = load_config(args.config)
    if not config.reference_bundle_dir:
        raise ValueError("the base config must provide generated legal_reference_bundles_v1")
    validate_groups()
    records = load_records(config.data.input_path)
    if args.record_index >= len(records):
        raise ValueError(f"record-index out of range: {args.record_index}")
    record = records[args.record_index]
    route = MetadataLawBundleRouter(config.reference_bundle_dir).route(record)
    navigation_by_item = {
        line.split(":", 1)[0].removeprefix("- ").strip(): line
        for line in MetadataLawBundleRouter(config.reference_bundle_dir).navigation_text(record).splitlines()
        if line.startswith("- v")
    }
    output_dir = ROOT / args.output_dir
    if output_dir.exists() and not args.fresh:
        raise RuntimeError(f"{output_dir} exists; use --fresh only for this disposable probe")
    if output_dir.exists():
        # The target is the explicit disposable probe directory; remove only its
        # files so a fresh run cannot mix outputs from two different notices.
        import shutil as _shutil
        _shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    shutil.copy2(config.path, output_dir / "base_config.yaml")
    item_table = load_item_table(config.data.item_table_path)
    decision_cards = load_decision_cards(config.decision_cards_path, item_table) if config.decision_cards_path else None
    products = load_competition_product_index(config.competition_products_path) if config.competition_products_path else None
    client = _make_client(config, args.mock)
    token_counter = _make_token_counter(config, args.mock)
    merged = zero_judgment()
    audit: dict[str, Any] = {
        "experiment": "exp-021-grouped-one-notice", "id": record["id"], "record_index": args.record_index,
        "profile": route.profile, "base_config": str(config.path), "prompt_layout": args.prompt_layout, "groups": [],
    }
    input_entries: list[dict[str, Any]] = []
    result_path = output_dir / "group_predictions.json"
    with result_path.open("w", encoding="utf-8") as result_handle:
        for group in LEGAL_ITEM_GROUPS:
            bundle_path = config.reference_bundle_dir / "groups" / f"{route.profile}__{group.group_id}.txt"
            reference_text = bundle_path.read_text(encoding="utf-8")
            reference_navigation = "\n".join(
                [
                    "## 이 호출의 v별 법령 참고 위치",
                    "아래 목록은 각 v가 판정 기준으로 먼저 확인할 이번 호출의 공식 참고자료다.",
                    "법령은 evidence가 아니며, evidence는 대상 공고문서에서만 복사한다.",
                    *(navigation_by_item[item] for item in group.items),
                ]
            )
            pipeline = BaselinePipeline(
                item_table=item_table, client=client, max_document_chars=config.max_document_chars,
                prompt_mode=config.prompt_mode, include_normalized_facts=config.include_normalized_facts,
                context_strategy=config.context_strategy, notice_anchor_chars=config.notice_anchor_chars,
                overflow_split_enabled=config.overflow_split_enabled, strict_document_evidence=config.strict_document_evidence,
                absence_detection_strategy=config.absence_detection_strategy, decision_cards=decision_cards,
                competition_products=products, count_tokens=token_counter,
                prompt_budget_tokens=config.max_model_len - config.output_reserve_tokens,
                reference_text=reference_text or None, active_items=group.items,
                prompt_layout=args.prompt_layout,
                reference_navigation=reference_navigation,
            )
            contexts = pipeline.contexts_for_record(record)
            group_inputs = []
            for pass_index, context in enumerate(contexts, 1):
                messages = pipeline.messages_for_context(record, context)
                entry = {"id": record["id"], "group": group.group_id, "items": list(group.items),
                         "pass_index": pass_index, "token_count": token_counter(messages) if token_counter else None,
                         "messages": messages}
                input_entries.append(entry)
                group_inputs.append({key: entry[key] for key in ("pass_index", "token_count")})
            prediction = pipeline.predict(record)
            for item in group.items:
                merged[item] = prediction.judgment[item]
            value = _prediction_json(group.group_id, prediction)
            result_handle.write(json.dumps(value, ensure_ascii=False) + "\n")
            result_handle.flush()
            audit["groups"].append({"group": group.group_id, "items": list(group.items),
                                    "bundle_path": str(bundle_path.relative_to(ROOT)), "bundle_characters": len(reference_text),
                                    "inputs": group_inputs, "latency_seconds": prediction.latency_seconds,
                                    "usage": prediction.usage, "parse_errors": list(prediction.parse_errors)})
            print(f"{group.group_id}: {group.items}, passes={len(contexts)}, {prediction.latency_seconds:.1f}s")
    (output_dir / "grouping_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_input_examples_markdown(output_dir / "input_examples.md", input_entries)
    (output_dir / "merged_prediction.json").write_text(json.dumps({"id": record["id"], "judgment": merged}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_submission([judgment_to_row(record["id"], merged)], output_dir / "submission.csv")
    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
