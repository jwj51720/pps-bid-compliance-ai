"""Zero-call attribution of frozen Python owner stage transitions."""

from __future__ import annotations

import csv
import hashlib
import importlib
import json
from pathlib import Path
import time
from typing import Any, Mapping, Sequence

from .config import CleanExperimentConfig
from .ingest import load_notice_records
from .preflight import compare_manifests
from .reference.frozen import FrozenL41Reference
from .runtime.openrouter import atomic_json


POPULATION_FUNNEL_STAGE = {
    "v10": "r2_initial_v10",
    "v11": "r2_initial_v11",
    "v16": "v16_survives_no_bge",
    "v17": "v17_survives_no_bge",
    "v18": "v18_survives_no_bge",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_binary_csv(path: Path) -> dict[str, dict[str, int]]:
    with path.open(encoding="utf-8", newline="") as handle:
        result = {}
        for row in csv.DictReader(handle):
            result[str(row["id"])] = {
                f"v{index}": int(row[f"v{index}"]) for index in range(1, 25)
            }
    return result


def binary_metrics(predictions: Mapping[str, int], truth: Mapping[str, int]) -> dict[str, Any]:
    if set(predictions) != set(truth):
        raise ValueError("prediction/truth ID coverage differs")
    tp = sum(predictions[key] == 1 and truth[key] == 1 for key in truth)
    fp = sum(predictions[key] == 1 and truth[key] == 0 for key in truth)
    fn = sum(predictions[key] == 0 and truth[key] == 1 for key in truth)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": precision, "recall": recall, "f1": f1,
        "predicted_positive": tp + fp,
    }


def stage_attribution(
    initial: Mapping[str, int], final: Mapping[str, int], truth: Mapping[str, int],
) -> dict[str, Any]:
    if set(initial) != set(final) or set(initial) != set(truth):
        raise ValueError("stage ID coverage differs")
    before = binary_metrics(initial, truth)
    after = binary_metrics(final, truth)
    additions = [key for key in truth if initial[key] == 0 and final[key] == 1]
    removals = [key for key in truth if initial[key] == 1 and final[key] == 0]
    added_true = sum(truth[key] == 1 for key in additions)
    added_false = len(additions) - added_true
    removed_false = sum(truth[key] == 0 for key in removals)
    removed_true = len(removals) - removed_false
    expansion_precision = added_true / len(additions) if additions else None
    improvement_threshold = before["f1"] / 2
    return {
        "initial": before,
        "final": after,
        "transitions": {
            "changed": len(additions) + len(removals),
            "zero_to_one": len(additions),
            "zero_to_one_true": added_true,
            "zero_to_one_false": added_false,
            "one_to_zero": len(removals),
            "one_to_zero_corrected_false_positive": removed_false,
            "one_to_zero_lost_true_positive": removed_true,
        },
        "expansion_precision": expansion_precision,
        "f1_improvement_precision_threshold": improvement_threshold,
        "expansion_margin_over_threshold": (
            expansion_precision - improvement_threshold
            if expansion_precision is not None else None
        ),
        "single_item_rollback_macro_delta": (before["f1"] - after["f1"]) / 24,
        "changed_ids": {
            "zero_to_one": additions,
            "one_to_zero": removals,
        },
    }


class PythonOwnerStageAttributionAudit:
    def __init__(self, config: CleanExperimentConfig) -> None:
        self.config = config
        self.root = config.path.parents[2]
        self.output_dir = config.output_dir.resolve()
        policy = config.raw["python_owner_stage_attribution_audit"]
        self.final_path = self.root / policy["final_submission_path"]
        self.population_report_path = self.root / policy["population_funnel_report_path"]
        self.initial_items = tuple(str(item) for item in policy["items_with_initial_stage"])
        self.zero_items = tuple(str(item) for item in policy["items_without_alternative_owner"])

    def run(self) -> dict[str, Any]:
        started = time.perf_counter()
        manifest = compare_manifests(self.config.path, self.root)
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")
        for path in (self.final_path, self.population_report_path):
            if not path.is_file():
                raise FileNotFoundError(path)
        records = load_notice_records(self.config.input_path)
        labels = _read_binary_csv(self.config.labels_path)
        final_rows = _read_binary_csv(self.final_path)
        ids = {record.notice_id for record in records}
        if len(records) != 200 or set(labels) != ids or set(final_rows) != ids:
            raise ValueError("unexpected dev attribution coverage")

        reference = FrozenL41Reference(
            self.config.reference_zip, self.config.reference_zip_sha256,
        )
        r2 = importlib.import_module("dev.run_r2_deterministic_absence_experiment")
        scanner_module = importlib.import_module("dev.r2_exact_product_context")
        builder = reference.builder(self.config.data_dir)
        scanner = scanner_module.ExactDocumentProductScanner(builder.catalog)
        initial: dict[str, dict[str, int]] = {item: {} for item in self.initial_items}
        for record in records:
            raw = dict(record.raw)
            facts = builder.build(raw)
            exact_product = scanner.build(raw)
            values = r2.predict(raw, facts, "meta_or_document_exact", exact_product)
            if set(self.initial_items) - set(values):
                raise ValueError("frozen initial owner coverage differs")
            for item in self.initial_items:
                value = values[item]
                if type(value) is not int or value not in (0, 1):
                    raise ValueError("frozen initial owner returned non-binary value")
                initial[item][record.notice_id] = value

        population_report = json.loads(
            self.population_report_path.read_text(encoding="utf-8")
        )
        attribution = {}
        for item in self.initial_items:
            final = {notice_id: final_rows[notice_id][item] for notice_id in ids}
            truth = {notice_id: labels[notice_id][item] for notice_id in ids}
            result = stage_attribution(initial[item], final, truth)
            funnel_name = POPULATION_FUNNEL_STAGE[item]
            result["population_funnel"] = {
                "predicate": funnel_name,
                **population_report["rates"][funnel_name],
                "is_final_activation": item == "v11",
                "limitation": (
                    "BGE bridge was not run; r2_initial_v10 is not final v10 activation"
                    if item == "v10" else (
                        "BGE was not run; survives_no_bge is an upper-bound funnel"
                        if item in {"v16", "v17", "v18"} else None
                    )
                ),
            }
            attribution[item] = result

        zero_counterfactual = {}
        zeros = {notice_id: 0 for notice_id in ids}
        for item in self.zero_items:
            final = {notice_id: final_rows[notice_id][item] for notice_id in ids}
            truth = {notice_id: labels[notice_id][item] for notice_id in ids}
            zero_counterfactual[item] = stage_attribution(zeros, final, truth)

        transition_integrity = all(
            value["initial"]["predicted_positive"]
            + value["transitions"]["zero_to_one"]
            - value["transitions"]["one_to_zero"]
            == value["final"]["predicted_positive"]
            for value in [*attribution.values(), *zero_counterfactual.values()]
        )
        report = {
            "status": "PASS" if transition_integrity else "FAIL",
            "mode": "zero-call-frozen-python-owner-stage-attribution",
            "records": len(records),
            "inputs": {
                "dev": {"path": str(self.config.input_path), "sha256": _sha256(self.config.input_path)},
                "labels": {"path": str(self.config.labels_path), "sha256": _sha256(self.config.labels_path)},
                "final_submission": {"path": str(self.final_path), "sha256": _sha256(self.final_path)},
                "population_funnel_report": {
                    "path": str(self.population_report_path),
                    "sha256": _sha256(self.population_report_path),
                },
                "reference_zip_sha256": self.config.reference_zip_sha256,
                "reference_script_sha256": reference.script_sha256,
            },
            "initial_to_final_attribution": attribution,
            "zero_owner_counterfactual": zero_counterfactual,
            "transition_integrity": transition_integrity,
            "calls": {"llm": 0, "embedding": 0},
            "final_prediction": False,
            "manifest_diff": manifest,
            "runtime_seconds": time.perf_counter() - started,
            "limitations": [
                "Dev labels are adaptive development evidence, not independent validation.",
                "Population funnel rates are unlabeled and cannot estimate precision or F1.",
                "v16/v17/v18 population survivors omit BGE and are upper bounds.",
                "v12/v13/v14 zero-owner rows are extreme removal counterfactuals, not alternatives.",
            ],
        }
        self.output_dir.mkdir(parents=True, exist_ok=True)
        atomic_json(self.output_dir / "manifest.snapshot.json", self.config.raw)
        atomic_json(self.output_dir / "audit_report.json", report)
        return report


__all__ = [
    "PythonOwnerStageAttributionAudit",
    "binary_metrics",
    "stage_attribution",
]
