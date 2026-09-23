"""Label-free v24 input-surface audit with dev error attribution."""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
import hashlib
import inspect
import json
from pathlib import Path
import time
from typing import Any, Iterable, Mapping, Sequence

from .config import CleanExperimentConfig
from .domain import NoticeRecord
from .ingest import load_notice_records
from .preflight import compare_manifests
from .runtime.openrouter import atomic_json
from .views.v24_multi_observation import AXIS_TERMS, build_v24_multi_observation_view


AXES = ("amount", "contract", "region", "industry")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_ids(ids: Sequence[str], limit: int) -> list[str]:
    return sorted(
        set(ids), key=lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest()
    )[:limit]


def _band(value: int) -> str:
    if value == 0:
        return "0"
    if value == 1:
        return "1"
    if value <= 3:
        return "2_3"
    return "4_plus"


def metadata_axis_available(meta: Mapping[str, Any], axis: str) -> bool:
    if axis == "amount":
        return any(meta.get(key) not in (None, "") for key in ("배정예산금액", "입찰추정가격"))
    if axis == "contract":
        return meta.get("계약방법") not in (None, "")
    if axis == "region":
        flag = meta.get("지역제한여부")
        return flag == "N" or (flag == "Y" and meta.get("제한지역코드목록") not in (None, ""))
    if axis == "industry":
        flag = meta.get("업종제한여부")
        return flag == "N" or (flag == "Y" and meta.get("면허업종제한목록") not in (None, ""))
    raise ValueError(f"unknown v24 axis: {axis}")


def notice_surface(record: NoticeRecord, max_axis_characters: int) -> dict[str, Any]:
    view = build_v24_multi_observation_view(
        record.raw, max_axis_characters=max_axis_characters,
    )
    if len(view["document_coverage"]) != len(record.documents):
        raise ValueError(f"{record.notice_id}: incomplete v24 document scan")
    meta = record.raw.get("meta") or {}
    features: set[str] = set()
    axis_rows: dict[str, dict[str, Any]] = {}
    for axis in AXES:
        candidates = list(view["candidates"][axis])
        coverage = list(view["axis_coverage"][axis])
        meta_available = metadata_axis_available(meta, axis)
        has_candidate = bool(candidates)
        multi = len(candidates) > 1
        attachment = any(candidate.document_type != "공고문" for candidate in candidates)
        unobserved = any(row["state"] == "UNOBSERVED" for row in coverage)
        comparable = meta_available and has_candidate
        values = {
            "meta_available": meta_available,
            "candidate_surface": has_candidate,
            "multi_candidate_surface": multi,
            "attachment_candidate_surface": attachment,
            "unobserved_surface": unobserved,
            "comparable_surface": comparable,
            "candidate_count": len(candidates),
            "candidate_count_band": _band(len(candidates)),
            "candidate_document_types": sorted({c.document_type for c in candidates}),
        }
        axis_rows[axis] = values
        for name, active in values.items():
            if isinstance(active, bool) and active:
                features.add(f"{axis}.{name}")
    if all(axis_rows[axis]["comparable_surface"] for axis in AXES):
        features.add("all_axes_comparable")
    if not any(axis_rows[axis]["comparable_surface"] for axis in AXES):
        features.add("no_axis_comparable")
    if any(axis_rows[axis]["multi_candidate_surface"] for axis in AXES):
        features.add("any_multi_candidate_surface")
    if any(axis_rows[axis]["attachment_candidate_surface"] for axis in AXES):
        features.add("any_attachment_candidate_surface")
    if any(axis_rows[axis]["unobserved_surface"] for axis in AXES):
        features.add("any_unobserved_surface")
    return {"id": record.notice_id, "features": features, "axes": axis_rows}


def summarize_records(
    records: Iterable[NoticeRecord], max_axis_characters: int,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    rows: dict[str, dict[str, Any]] = {}
    feature_counts: Counter[str] = Counter()
    active_ids: dict[str, list[str]] = defaultdict(list)
    bands = {axis: Counter() for axis in AXES}
    document_types = {axis: Counter() for axis in AXES}
    documents = 0
    for record in records:
        documents += len(record.documents)
        row = notice_surface(record, max_axis_characters)
        rows[record.notice_id] = row
        for feature in row["features"]:
            feature_counts[feature] += 1
            active_ids[feature].append(record.notice_id)
        for axis in AXES:
            values = row["axes"][axis]
            bands[axis][values["candidate_count_band"]] += 1
            document_types[axis].update(values["candidate_document_types"])
    if not rows:
        raise ValueError("cannot audit an empty cohort")
    return ({
        "records": len(rows),
        "documents": documents,
        "feature_counts": dict(feature_counts),
        "categorical_counts": {
            "candidate_count_band": {axis: dict(value) for axis, value in bands.items()},
            "candidate_document_type_presence": {
                axis: dict(value) for axis, value in document_types.items()
            },
        },
        "active_ids": active_ids,
    }, rows)


def _rates(
    left: Mapping[str, int], right: Mapping[str, int], left_n: int, right_n: int,
    *, difference_gate: float, rr_low: float, rr_high: float,
) -> dict[str, dict[str, Any]]:
    result = {}
    for feature in sorted(set(left) | set(right)):
        left_rate = left.get(feature, 0) / left_n
        right_rate = right.get(feature, 0) / right_n
        ratio = left_rate / right_rate if right_rate else None
        large = abs(left_rate - right_rate) >= difference_gate
        large = large or (ratio is None and left_rate > 0)
        large = large or (ratio is not None and (ratio < rr_low or ratio > rr_high))
        result[feature] = {
            "dev_count": left.get(feature, 0), "dev_rate": left_rate,
            "population_count": right.get(feature, 0), "population_rate": right_rate,
            "rate_difference_dev_minus_population": left_rate - right_rate,
            "risk_ratio_dev_over_population": ratio, "large_shift": large,
        }
    return result


def _tv(
    left: Mapping[str, int], right: Mapping[str, int], left_n: int, right_n: int,
) -> dict[str, Any]:
    keys = sorted(set(left) | set(right))
    left_rates = {key: left.get(key, 0) / left_n for key in keys}
    right_rates = {key: right.get(key, 0) / right_n for key in keys}
    return {
        "dev": left_rates, "population": right_rates,
        "total_variation": 0.5 * sum(abs(left_rates[k] - right_rates[k]) for k in keys),
    }


def _read_binary(path: Path, column: str) -> dict[str, int]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {str(row["id"]): int(row[column]) for row in csv.DictReader(handle)}


def _read_submission_v24(path: Path) -> tuple[dict[str, int], dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return (
        {str(row["id"]): int(row["v24"]) for row in rows},
        {str(row["id"]): str(row["e24"]) for row in rows},
    )


def evidence_axis_surface(text: str) -> list[str]:
    """Classify literal evidence surfaces without inferring their semantic role."""
    return [
        axis for axis, terms in AXIS_TERMS.items()
        if any(term.casefold() in text.casefold() for term in terms)
    ] or ["unclassified"]


def evidence_axis_strata(
    records: Iterable[NoticeRecord], labels: Mapping[str, int],
    predictions: Mapping[str, int], evidences: Mapping[str, str],
) -> dict[str, Any]:
    counts = {"TP": Counter(), "FP": Counter()}
    invalid: list[str] = []
    for record in records:
        notice_id = record.notice_id
        if predictions[notice_id] != 1:
            continue
        evidence = evidences[notice_id]
        if not evidence or len(evidence) > 500 or not any(
            evidence in document.text for document in record.documents
        ):
            invalid.append(notice_id)
        stratum = "TP" if labels[notice_id] == 1 else "FP"
        counts[stratum].update(evidence_axis_surface(evidence))
    return {
        "counts": {name: dict(value) for name, value in counts.items()},
        "invalid_evidence_ids": sorted(invalid),
    }


def binary_metrics(labels: Mapping[str, int], predictions: Mapping[str, int]) -> dict[str, Any]:
    tp = sum(labels[key] == 1 and predictions[key] == 1 for key in labels)
    fp = sum(labels[key] == 0 and predictions[key] == 1 for key in labels)
    fn = sum(labels[key] == 1 and predictions[key] == 0 for key in labels)
    denominator = 2 * tp + fp + fn
    return {"tp": tp, "fp": fp, "fn": fn, "f1": 2 * tp / denominator if denominator else 0.0}


def error_strata(
    surfaces: Mapping[str, Mapping[str, Any]], labels: Mapping[str, int],
    predictions: Mapping[str, int], sample_size: int,
) -> dict[str, Any]:
    strata: dict[str, list[str]] = {name: [] for name in ("TP", "FP", "FN", "TN")}
    for notice_id in sorted(surfaces):
        actual = labels[notice_id]
        predicted = predictions[notice_id]
        name = ("T" if actual == predicted else "F") + ("P" if predicted else "N")
        strata[name].append(notice_id)
    feature_counts: dict[str, Counter[str]] = {}
    for name, ids in strata.items():
        feature_counts[name] = Counter(
            feature for notice_id in ids for feature in surfaces[notice_id]["features"]
        )
    features = sorted(set().union(*(set(value) for value in feature_counts.values())))

    def enrichment(numerator: str, denominator: str) -> dict[str, Any]:
        values = {}
        for feature in features:
            a = feature_counts[numerator][feature] / len(strata[numerator]) if strata[numerator] else 0.0
            b = feature_counts[denominator][feature] / len(strata[denominator]) if strata[denominator] else 0.0
            values[feature] = {
                "numerator_rate": a, "denominator_rate": b,
                "risk_ratio": a / b if b else None,
            }
        return values

    return {
        "counts": {name: len(ids) for name, ids in strata.items()},
        "feature_counts": {name: dict(value) for name, value in feature_counts.items()},
        "fp_vs_tn": enrichment("FP", "TN"),
        "fn_vs_tp": enrichment("FN", "TP"),
        "hash_selected_ids": {name: _stable_ids(ids, sample_size) for name, ids in strata.items()},
    }


class V24OperationalSurfaceAudit:
    def __init__(self, config: CleanExperimentConfig) -> None:
        self.config = config
        self.root = config.path.parents[2]
        self.output_dir = config.output_dir.resolve()
        policy = config.raw["v24_operational_surface_audit"]
        self.population_path = self.root / policy["population_input_path"]
        self.submission_path = self.root / policy["final_submission_path"]
        self.max_axis_characters = int(policy["max_axis_characters"])
        self.difference_gate = float(policy["large_shift_rate_difference"])
        self.rr_low = float(policy["large_shift_risk_ratio_low"])
        self.rr_high = float(policy["large_shift_risk_ratio_high"])
        self.sample_size = int(policy["sample_ids_per_stratum"])

    def run(self) -> dict[str, Any]:
        started = time.perf_counter()
        manifest = compare_manifests(self.config.path, self.root)
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")
        dev, dev_rows = summarize_records(
            load_notice_records(self.config.input_path), self.max_axis_characters,
        )
        population, _ = summarize_records(
            load_notice_records(self.population_path), self.max_axis_characters,
        )
        comparison = _rates(
            dev["feature_counts"], population["feature_counts"],
            dev["records"], population["records"],
            difference_gate=self.difference_gate, rr_low=self.rr_low, rr_high=self.rr_high,
        )
        categories = {"candidate_count_band": {}}
        for axis in AXES:
            categories["candidate_count_band"][axis] = _tv(
                dev["categorical_counts"]["candidate_count_band"][axis],
                population["categorical_counts"]["candidate_count_band"][axis],
                dev["records"], population["records"],
            )
        labels = _read_binary(self.config.labels_path, "v24")
        predictions, evidences = _read_submission_v24(self.submission_path)
        if set(labels) != set(dev_rows) or set(predictions) != set(dev_rows):
            raise ValueError("v24 dev IDs are not aligned")
        errors = error_strata(dev_rows, labels, predictions, self.sample_size)
        evidence_surfaces = evidence_axis_strata(
            load_notice_records(self.config.input_path), labels, predictions, evidences,
        )
        strict_predictions = dict(predictions)
        for notice_id in evidence_surfaces["invalid_evidence_ids"]:
            strict_predictions[notice_id] = 0
        strict_evidence = {
            "initial": binary_metrics(labels, predictions),
            "strict": binary_metrics(labels, strict_predictions),
            "changed_ids": evidence_surfaces["invalid_evidence_ids"],
        }
        strict_evidence["macro_delta"] = (
            strict_evidence["strict"]["f1"] - strict_evidence["initial"]["f1"]
        ) / 24
        large = [key for key, value in comparison.items() if value["large_shift"]]
        report = {
            "status": "PASS",
            "mode": "label-free-v24-surface-plus-dev-error-attribution",
            "inputs": {
                "dev": {"path": str(self.config.input_path), "sha256": _sha256(self.config.input_path)},
                "population": {"path": str(self.population_path), "sha256": _sha256(self.population_path)},
                "labels": {"path": str(self.config.labels_path), "sha256": _sha256(self.config.labels_path)},
                "submission": {"path": str(self.submission_path), "sha256": _sha256(self.submission_path)},
                "view_module": {
                    "path": inspect.getsourcefile(build_v24_multi_observation_view),
                    "sha256": _sha256(Path(inspect.getsourcefile(build_v24_multi_observation_view) or "")),
                },
            },
            "dev": {key: value for key, value in dev.items() if key != "active_ids"},
            "population": {key: value for key, value in population.items() if key != "active_ids"},
            "comparison": comparison,
            "large_shift_features": large,
            "categorical_comparison": categories,
            "dev_error_strata": errors,
            "positive_evidence_axis_surfaces": evidence_surfaces,
            "strict_evidence_counterfactual": strict_evidence,
            "hash_selected_population_ids": {
                feature: _stable_ids(population["active_ids"][feature], self.sample_size)
                for feature in large
            },
            "calls": {"llm": 0, "embedding": 0},
            "final_prediction": False,
            "manifest_diff": manifest,
            "runtime_seconds": time.perf_counter() - started,
            "limitations": [
                "Population source morphology is not v24 accuracy or a pseudo-label.",
                "Candidate surfaces do not establish semantic field roles or value mismatches.",
                "Dev error strata are adaptive-development evidence.",
            ],
        }
        self.output_dir.mkdir(parents=True, exist_ok=True)
        atomic_json(self.output_dir / "audit_report.json", report)
        return report
