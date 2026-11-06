"""Post-stratified stress test for adaptive dev metrics."""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Iterable, Mapping

from .config import CleanExperimentConfig
from .domain import NoticeRecord
from .ingest import load_notice_records
from .preflight import compare_manifests
from .runtime.openrouter import atomic_json


ITEMS = tuple(f"v{index}" for index in range(1, 25))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fixed_stratum(
    record: NoticeRecord, *, amount_threshold: int = 100_000_000,
    direct_substring: str = "수의", document_threshold: int = 2,
) -> str:
    contract = (
        "direct" if direct_substring in str(record.metadata.get("계약방법") or "")
        else "competitive"
    )
    raw_amount = record.metadata.get("입찰추정가격")
    try:
        amount = int(raw_amount or 0)
    except (TypeError, ValueError):
        amount = 0
    amount_band = "lt100m" if amount < amount_threshold else "ge100m"
    structure = "attachment" if len(record.documents) >= document_threshold else "notice_only"
    return f"{contract}|{amount_band}|{structure}"


def stratum_counts(
    records: Iterable[NoticeRecord], *, amount_threshold: int,
    direct_substring: str, document_threshold: int,
) -> tuple[Counter[str], dict[str, str]]:
    counts: Counter[str] = Counter()
    by_id: dict[str, str] = {}
    for record in records:
        value = fixed_stratum(
            record, amount_threshold=amount_threshold,
            direct_substring=direct_substring,
            document_threshold=document_threshold,
        )
        counts[value] += 1
        by_id[record.notice_id] = value
    return counts, by_id


def poststratification_weights(
    dev_counts: Mapping[str, int], population_counts: Mapping[str, int],
) -> tuple[dict[str, float], dict[str, Any]]:
    unsupported = {
        key: count for key, count in population_counts.items()
        if count and dev_counts.get(key, 0) == 0
    }
    supported_population = sum(population_counts.values()) - sum(unsupported.values())
    dev_total = sum(dev_counts.values())
    if not supported_population or not dev_total:
        raise ValueError("empty supported population or dev cohort")
    weights = {
        key: (population_counts.get(key, 0) / supported_population) / (count / dev_total)
        for key, count in dev_counts.items()
        if count
    }
    mean_weight = sum(dev_counts[key] * value for key, value in weights.items()) / dev_total
    expanded = [weights[key] for key, count in dev_counts.items() for _ in range(count)]
    ess = sum(expanded) ** 2 / sum(value * value for value in expanded)
    return weights, {
        "unsupported_population_counts": unsupported,
        "unsupported_population_mass": sum(unsupported.values()) / sum(population_counts.values()),
        "supported_population_records": supported_population,
        "mean_dev_record_weight": mean_weight,
        "effective_sample_size": ess,
    }


def _read_items(path: Path) -> dict[str, dict[str, int]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {
            str(row["id"]): {item: int(row[item]) for item in ITEMS}
            for row in csv.DictReader(handle)
        }


def confusion(
    labels: Mapping[str, Mapping[str, int]], predictions: Mapping[str, Mapping[str, int]],
    item: str, record_weights: Mapping[str, float], strata: Mapping[str, str],
) -> dict[str, Any]:
    tp = fp = fn = 0.0
    error_by_stratum: defaultdict[str, float] = defaultdict(float)
    for notice_id, truth in labels.items():
        weight = record_weights[notice_id]
        predicted = predictions[notice_id][item]
        actual = truth[item]
        if actual == 1 and predicted == 1:
            tp += weight
        elif actual == 0 and predicted == 1:
            fp += weight
            error_by_stratum[strata[notice_id]] += weight
        elif actual == 1 and predicted == 0:
            fn += weight
            error_by_stratum[strata[notice_id]] += weight
    denominator = 2 * tp + fp + fn
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "f1": 2 * tp / denominator if denominator else 0.0,
        "largest_weighted_error_strata": [
            {"stratum": key, "weighted_error": value}
            for key, value in sorted(error_by_stratum.items(), key=lambda row: (-row[1], row[0]))[:3]
        ],
    }


def stress_metrics(
    labels: Mapping[str, Mapping[str, int]], predictions: Mapping[str, Mapping[str, int]],
    strata: Mapping[str, str], stratum_weights: Mapping[str, float],
) -> dict[str, Any]:
    if set(labels) != set(predictions) or set(labels) != set(strata):
        raise ValueError("stress metric IDs are not aligned")
    raw_weights = {notice_id: 1.0 for notice_id in labels}
    record_weights = {notice_id: stratum_weights[strata[notice_id]] for notice_id in labels}
    items = {}
    for item in ITEMS:
        raw = confusion(labels, predictions, item, raw_weights, strata)
        weighted = confusion(labels, predictions, item, record_weights, strata)
        items[item] = {
            "raw": raw, "weighted": weighted,
            "f1_delta_weighted_minus_raw": weighted["f1"] - raw["f1"],
        }
    return {
        "raw_macro": sum(value["raw"]["f1"] for value in items.values()) / len(ITEMS),
        "weighted_macro": sum(value["weighted"]["f1"] for value in items.values()) / len(ITEMS),
        "items": items,
    }


class CovariateShiftStressAudit:
    def __init__(self, config: CleanExperimentConfig) -> None:
        self.config = config
        self.root = config.path.parents[2]
        self.output_dir = config.output_dir.resolve()
        policy = config.raw["covariate_shift_stress_audit"]
        self.population_path = self.root / policy["population_input_path"]
        self.submission_path = self.root / policy["final_submission_path"]
        self.v3_revert_path = self.root / policy["v3_revert_submission_path"]
        self.v19_base_path = self.root / policy["v19_base_submission_path"]
        self.stage_report_path = self.root / policy["stage_attribution_report_path"]
        self.amount_threshold = int(policy["amount_threshold_won"])
        self.direct_substring = str(policy["contract_direct_substring"])
        self.document_threshold = int(policy["document_structure_threshold"])

    def run(self) -> dict[str, Any]:
        started = time.perf_counter()
        manifest = compare_manifests(self.config.path, self.root)
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")
        dev_counts, strata = stratum_counts(
            load_notice_records(self.config.input_path),
            amount_threshold=self.amount_threshold,
            direct_substring=self.direct_substring,
            document_threshold=self.document_threshold,
        )
        population_counts, _ = stratum_counts(
            load_notice_records(self.population_path),
            amount_threshold=self.amount_threshold,
            direct_substring=self.direct_substring,
            document_threshold=self.document_threshold,
        )
        weights, support = poststratification_weights(dev_counts, population_counts)
        labels = _read_items(self.config.labels_path)
        predictions = _read_items(self.submission_path)
        metrics = stress_metrics(labels, predictions, strata, weights)
        v3_revert = _read_items(self.v3_revert_path)
        v19_base = _read_items(self.v19_base_path)
        comparator_metrics = {
            "v3": {
                "s001_specialist": metrics["items"]["v3"],
                "reverted_r10": stress_metrics(labels, v3_revert, strata, weights)["items"]["v3"],
            },
            "v19": {
                "s001_native": metrics["items"]["v19"],
                "base_B": stress_metrics(labels, v19_base, strata, weights)["items"]["v19"],
            },
        }
        comparator_metrics["v3"]["weighted_f1_specialist_minus_revert"] = (
            comparator_metrics["v3"]["s001_specialist"]["weighted"]["f1"]
            - comparator_metrics["v3"]["reverted_r10"]["weighted"]["f1"]
        )
        comparator_metrics["v19"]["weighted_f1_native_minus_base"] = (
            comparator_metrics["v19"]["s001_native"]["weighted"]["f1"]
            - comparator_metrics["v19"]["base_B"]["weighted"]["f1"]
        )
        stage_report = json.loads(self.stage_report_path.read_text(encoding="utf-8"))
        python_stage_comparators = {}
        for item, attribution in stage_report["initial_to_final_attribution"].items():
            initial_rows = {notice_id: dict(values) for notice_id, values in predictions.items()}
            for notice_id in attribution["changed_ids"]["zero_to_one"]:
                initial_rows[notice_id][item] = 0
            for notice_id in attribution["changed_ids"]["one_to_zero"]:
                initial_rows[notice_id][item] = 1
            initial_metric = stress_metrics(labels, initial_rows, strata, weights)["items"][item]
            final_metric = metrics["items"][item]
            python_stage_comparators[item] = {
                "initial": initial_metric,
                "final": final_metric,
                "weighted_f1_final_minus_initial": (
                    final_metric["weighted"]["f1"] - initial_metric["weighted"]["f1"]
                ),
            }
        report = {
            "status": "PASS",
            "mode": "fixed-strata-poststratification-stress-not-public-estimate",
            "inputs": {
                "dev": {"path": str(self.config.input_path), "sha256": _sha256(self.config.input_path)},
                "population": {"path": str(self.population_path), "sha256": _sha256(self.population_path)},
                "labels": {"path": str(self.config.labels_path), "sha256": _sha256(self.config.labels_path)},
                "submission": {"path": str(self.submission_path), "sha256": _sha256(self.submission_path)},
                "v3_revert_submission": {
                    "path": str(self.v3_revert_path), "sha256": _sha256(self.v3_revert_path),
                },
                "v19_base_submission": {
                    "path": str(self.v19_base_path), "sha256": _sha256(self.v19_base_path),
                },
                "stage_attribution_report": {
                    "path": str(self.stage_report_path), "sha256": _sha256(self.stage_report_path),
                },
            },
            "stratum_definition": {
                "contract": f"contains {self.direct_substring!r} vs other",
                "amount_threshold_won": self.amount_threshold,
                "document_structure_threshold": self.document_threshold,
            },
            "dev_counts": dict(dev_counts),
            "population_counts": dict(population_counts),
            "stratum_weights": weights,
            "support": support,
            "metrics": metrics,
            "one_change_comparators": comparator_metrics,
            "python_stage_comparators": python_stage_comparators,
            "largest_negative_item_shifts": sorted(
                ({"item": item, "delta": value["f1_delta_weighted_minus_raw"]}
                 for item, value in metrics["items"].items()),
                key=lambda row: (row["delta"], row["item"]),
            )[:10],
            "largest_positive_item_shifts": sorted(
                ({"item": item, "delta": value["f1_delta_weighted_minus_raw"]}
                 for item, value in metrics["items"].items()),
                key=lambda row: (-row["delta"], row["item"]),
            )[:10],
            "calls": {"llm": 0, "embedding": 0},
            "final_prediction": False,
            "manifest_diff": manifest,
            "runtime_seconds": time.perf_counter() - started,
            "limitations": [
                "Post-stratification assumes stable conditional error within each coarse stratum.",
                "Adaptive dev labels and predictions are not independent validation evidence.",
                "The organizer unlabeled population is a distribution proxy, not public labels.",
            ],
        }
        if abs(metrics["raw_macro"] - 0.8151465658) > 1e-9:
            raise ValueError("raw S001 Macro does not match the stored regression value")
        if abs(support["mean_dev_record_weight"] - 1.0) > 1e-12:
            raise ValueError("post-stratification weights do not average to one")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        atomic_json(self.output_dir / "audit_report.json", report)
        return report
