#!/usr/bin/env python3
"""Run a resumable grouped-v legal-reference experiment and evaluate it."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_experiment import _make_client, _make_token_counter, _write_input_examples_markdown
from src.config import load_config
from src.data import (
    load_competition_product_index,
    load_decision_cards,
    load_item_table,
    load_record_id_panel,
    load_records,
    select_records_by_id,
)
from src.evaluate import evaluate_submission, write_rows
from src.law_bundles import FourProfileGroupLawBundleRouter, MetadataLawBundleRouter
from src.legal_groups import groups_for_scheme
from src.pipeline import BaselinePipeline, judgment_to_row, zero_judgment
from src.submission import validate_submission, write_submission


_GROUP_CONTEXT_OVERRIDE_KEYS = {
    "max_document_chars", "context_strategy", "overflow_split_enabled",
    "absence_detection_strategy",
}


def _group_context_policy(config: Any, grouped_run: dict[str, Any], group_id: str) -> dict[str, Any]:
    """Return the explicitly declared context policy for one execution group."""
    overrides = grouped_run.get("group_context_overrides", {})
    if not isinstance(overrides, dict):
        raise ValueError("grouped_run.group_context_overrides must be a mapping")
    override = overrides.get(group_id, {})
    if not isinstance(override, dict) or set(override) - _GROUP_CONTEXT_OVERRIDE_KEYS:
        raise ValueError(f"invalid group context override for {group_id}")
    policy = {
        "max_document_chars": config.max_document_chars,
        "context_strategy": config.context_strategy,
        "overflow_split_enabled": config.overflow_split_enabled,
        "absence_detection_strategy": config.absence_detection_strategy,
    }
    policy.update(override)
    if policy["context_strategy"] not in {"single", "single_no_split", "split", "full_split_merge"}:
        raise ValueError(f"invalid context_strategy for {group_id}")
    if policy["max_document_chars"] is not None and int(policy["max_document_chars"]) < 1:
        raise ValueError(f"max_document_chars must be positive for {group_id}")
    if policy["absence_detection_strategy"] not in {"per_pass_or", "per_pass_and"}:
        raise ValueError(f"invalid absence_detection_strategy for {group_id}")
    if policy["absence_detection_strategy"] == "per_pass_and" and group_id != "G02_absence_items":
        raise ValueError("per_pass_and is only valid for the dedicated absence group")
    return policy


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--ids-file", help="JSON list, or object with ids, selecting input records")
    parser.add_argument("--output-dir")
    parser.add_argument("--prompt-layout", choices=("plain", "markdown", "markdown_v2"))
    parser.add_argument("--reference-mode", choices=("group_bundle", "none"))
    parser.add_argument("--reference-navigation", choices=("none", "per_item"))
    parser.add_argument("--grouping", choices=("law_overlap_12", "four_way", "three_way", "absence_presence_v1", "absence_presence_consistency_v1"))
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")

    load_dotenv(ROOT / ".env")
    config = load_config(args.config)
    grouped_run = config.raw.get("grouped_run", {})
    if not isinstance(grouped_run, dict):
        raise ValueError("grouped_run must be a mapping when provided")
    grouping = args.grouping or str(grouped_run.get("grouping", "law_overlap_12"))
    reference_mode = args.reference_mode or str(grouped_run.get("reference_mode", "group_bundle"))
    reference_navigation = args.reference_navigation or str(grouped_run.get("reference_navigation", "per_item"))
    prompt_layout = args.prompt_layout or config.prompt_layout
    if grouping not in {"law_overlap_12", "four_way", "three_way", "absence_presence_v1", "absence_presence_consistency_v1"}:
        raise ValueError("invalid grouped_run.grouping")
    if reference_mode not in {"group_bundle", "none"}:
        raise ValueError("grouped_run.reference_mode must be group_bundle or none")
    if reference_navigation not in {"none", "per_item"}:
        raise ValueError("grouped_run.reference_navigation must be none or per_item")
    reuse_spec = grouped_run.get("reuse_groups")
    if reuse_spec is not None and not isinstance(reuse_spec, dict):
        raise ValueError("grouped_run.reuse_groups must be a mapping")
    if reference_mode == "group_bundle" and not config.reference_bundle_dir:
        raise ValueError("the base config must provide generated legal-reference bundles")
    item_groups = groups_for_scheme(grouping)
    group_context_policies = {
        group.group_id: _group_context_policy(config, grouped_run, group.group_id)
        for group in item_groups
    }
    selected_ids = (
        load_record_id_panel(args.ids_file)
        if args.ids_file
        else (
            load_record_id_panel(config.data.fast_panel_ids_path)
            if config.data.fast_panel_ids_path
            else None
        )
    )
    effective_limit = args.limit if args.limit is not None else config.local_limit
    if selected_ids is not None and effective_limit is not None:
        source = "--limit" if args.limit is not None else "run.local_limit"
        raise ValueError(f"record ID panel and {source} are mutually exclusive")
    records = load_records(config.data.input_path)
    if selected_ids is not None:
        records = select_records_by_id(records, selected_ids)
    elif effective_limit is not None:
        records = records[:effective_limit]
    output_dir = Path(args.output_dir).resolve() if args.output_dir else config.output_dir
    # A mock response is a structural smoke test, never a resumable remote
    # result.  Keep it in a dedicated subtree so its checkpoint cannot
    # suppress paid calls for the configured experiment ID.
    if args.mock:
        output_dir = output_dir / "_mock"
    checkpoint_path = output_dir / "predictions.jsonl"
    if args.fresh and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(config.path, output_dir / "base_config.yaml")
    (output_dir / "experiment_spec.json").write_text(
        json.dumps(
            {
                "experiment_id": config.experiment_id, "prompt_layout": prompt_layout,
                "grouping": grouping, "group_count": len(item_groups), "records": [record["id"] for record in records],
                "base_config": str(config.path), "reference_mode": reference_mode,
                "reference_navigation": reference_navigation, "reuse_groups": reuse_spec,
                "group_context_policies": group_context_policies,
            }, ensure_ascii=False, indent=2
        ) + "\n", encoding="utf-8"
    )
    checkpoint = {}
    if checkpoint_path.exists():
        checkpoint = {
            value["id"]: value for value in
            (json.loads(line) for line in checkpoint_path.read_text(encoding="utf-8").splitlines() if line.strip())
        }

    reused_groups_by_id: dict[str, dict[str, dict[str, Any]]] = {}
    reused_group_ids: set[str] = set()
    if reuse_spec is not None:
        source_path = ROOT / str(reuse_spec["output_dir"]) / "predictions.jsonl"
        reused_group_ids = {str(value) for value in reuse_spec["group_ids"]}
        if not source_path.is_file() or not reused_group_ids:
            raise ValueError("reuse_groups requires an existing predictions.jsonl and group_ids")
        for line in source_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            value = json.loads(line)
            groups = {group["group"]: group for group in value.get("groups", [])}
            missing = reused_group_ids - set(groups)
            if missing:
                raise ValueError(f"reuse source {value.get('id')} lacks groups: {sorted(missing)}")
            reused_groups_by_id[str(value["id"])] = groups
        missing_records = {record["id"] for record in records} - set(reused_groups_by_id)
        if missing_records:
            raise ValueError(f"reuse source lacks selected records: {sorted(missing_records)}")

    item_table = load_item_table(config.data.item_table_path)
    cards = load_decision_cards(config.decision_cards_path, item_table) if config.decision_cards_path else None
    products = load_competition_product_index(config.competition_products_path) if config.competition_products_path else None
    if config.decision_cards_path:
        shutil.copy2(config.decision_cards_path, output_dir / "decision_cards.json")
    if config.competition_products_path:
        shutil.copy2(config.competition_products_path, output_dir / "competition_products.json")
    client = _make_client(config, args.mock)
    exact_counter_required = any(
        policy["max_document_chars"] is None
        and policy["context_strategy"] in {"single", "single_no_split", "full_split_merge"}
        for policy in group_context_policies.values()
    )
    token_counter = _make_token_counter(config, args.mock, force=exact_counter_required)
    if reference_mode == "group_bundle":
        router = (
            FourProfileGroupLawBundleRouter(config.reference_bundle_dir)
            if config.reference_routing == "metadata_profile_group_v2"
            else MetadataLawBundleRouter(config.reference_bundle_dir)
        )
        shutil.copytree(config.reference_bundle_dir, output_dir / "law_bundles", dirs_exist_ok=True)
    else:
        router = None

    def predict_record(record: dict[str, Any]) -> dict[str, Any]:
        route = router.route(record) if router else None
        merged = zero_judgment()
        group_results: list[dict[str, Any]] = []
        examples: list[dict[str, Any]] = []
        for group in item_groups:
            context_policy = group_context_policies[group.group_id]
            if group.group_id in reused_group_ids:
                source_group = reused_groups_by_id[record["id"]][group.group_id]
                if not set(group.items).issubset(source_group["items"]):
                    raise ValueError(f"reused group item mismatch: {group.group_id}")
                for item in group.items:
                    merged[item] = source_group["judgment"][item]
                group_results.append({
                    **source_group,
                    "items": list(group.items),
                    "judgment": {item: source_group["judgment"][item] for item in group.items},
                    "reused_from": str(reuse_spec["output_dir"]),
                })
                continue
            bundle_path = None
            reference_text = None
            navigation = None
            if router:
                group_bundle = router.group_bundle(record, group.group_id)
                bundle_path = group_bundle.reference_path
                reference_text = group_bundle.reference_text
                # The chosen profile, group, chunk keys, and file paths are
                # retained in the run artifact.  They are routing metadata,
                # not instructions for the model, so no navigation block is
                # injected into this prompt.
            pipeline = BaselinePipeline(
                item_table=item_table, client=client, max_document_chars=context_policy["max_document_chars"],
                prompt_mode=config.prompt_mode, include_normalized_facts=config.include_normalized_facts,
                context_strategy=context_policy["context_strategy"], notice_anchor_chars=config.notice_anchor_chars,
                overflow_split_enabled=context_policy["overflow_split_enabled"], strict_document_evidence=config.strict_document_evidence,
                absence_detection_strategy=context_policy["absence_detection_strategy"], decision_cards=cards,
                competition_products=products, count_tokens=token_counter,
                prompt_budget_tokens=config.max_model_len - config.output_reserve_tokens,
                reference_text=reference_text, reference_navigation=navigation,
                active_items=group.items, prompt_layout=prompt_layout,
                prompt_profile=config.prompt_profile,
                role_directive=config.role_directive,
                item_catalog_style=config.item_catalog_style,
                metadata_style=config.metadata_style,
                output_mode=config.output_mode,
                visible_document_types=config.visible_document_types,
                v8_composite_merge_enabled=config.v8_composite_merge_enabled,
                v8_composite_merge_mode=config.v8_composite_merge_mode,
            )
            contexts = pipeline.contexts_for_record(record)
            if record is records[0]:
                for pass_index, context in enumerate(contexts, 1):
                    messages = pipeline.messages_for_context(record, context)
                    examples.append({"id": record["id"], "group": group.group_id, "items": list(group.items),
                                     "pass_index": pass_index, "token_count": token_counter(messages) if token_counter else None, "messages": messages})
            prediction = pipeline.predict(record)
            for item in group.items:
                merged[item] = prediction.judgment[item]
            group_results.append({
                "group": group.group_id, "items": list(group.items), "profile": route.profile if route else None,
                "bundle_path": str(bundle_path.relative_to(ROOT)) if bundle_path else None,
                "bundle_characters": len(reference_text) if reference_text else 0,
                "context_policy": context_policy,
                "judgment": {item: prediction.judgment[item] for item in group.items},
                "pass_judgments": list(prediction.pass_judgments), "raw_response": prediction.raw_response,
                "v8_observations": list(prediction.v8_observations),
                "parse_errors": list(prediction.parse_errors), "latency_seconds": prediction.latency_seconds,
                "usage": prediction.usage,
            })
        return {"id": record["id"], "row": judgment_to_row(record["id"], merged), "judgment": merged,
                "profile": route.profile if route else None, "groups": group_results, "input_examples": examples}

    pending = [record for record in records if record["id"] not in checkpoint]
    with checkpoint_path.open("a", encoding="utf-8") as handle:
        with ThreadPoolExecutor(max_workers=config.concurrency) as executor:
            futures = {executor.submit(predict_record, record): record for record in pending}
            for position, future in enumerate(as_completed(futures), 1):
                value = future.result()
                checkpoint[value["id"]] = value
                handle.write(json.dumps(value, ensure_ascii=False) + "\n")
                handle.flush()
                print(
                    f"[{position}/{len(pending)}] {value['id']} groups={len(value['groups'])}",
                    flush=True,
                )

    ordered = [checkpoint[record["id"]] for record in records]
    write_submission([value["row"] for value in ordered], output_dir / "submission.csv")
    validation = validate_submission(output_dir / "submission.csv", records)
    (output_dir / "validation.json").write_text(json.dumps({"passed": validation.passed, "errors": validation.errors, "warnings": validation.warnings}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not validation.passed:
        raise RuntimeError(f"submission validation failed: {validation.errors[:3]}")
    if config.data.labels_path:
        metrics, per_item, errors = evaluate_submission(output_dir / "submission.csv", config.data.labels_path, records)
        (output_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_rows(output_dir / "per_item_metrics.csv", per_item)
        write_rows(output_dir / "errors.csv", errors)
    examples = next((value["input_examples"] for value in ordered if value["input_examples"]), [])
    _write_input_examples_markdown(output_dir / "input_examples.md", examples)
    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
