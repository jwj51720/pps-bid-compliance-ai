"""Label-free v3 source-view morphology audit over organizer population data."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import inspect
import json
from pathlib import Path
import re
import time
from typing import Any, Iterable, Mapping, Sequence

from .config import CleanExperimentConfig
from .decisions.v3_monetary import parse_amount_won
from .domain import NoticeRecord
from .ingest import load_notice_records
from .preflight import compare_manifests
from .runtime.openrouter import atomic_json
from .views.v3_monetary import MONEY_PATTERN, build_v3_monetary_view


MORPHOLOGY_PATTERNS: dict[str, re.Pattern[str]] = {
    "qualification_surface": re.compile(
        r"입찰\s*참가|참가\s*자격|입찰\s*자격|자격.{0,20}(?:모두|충족)|"
        r"업체만\s*참가|실적\s*제한"
    ),
    "evaluation_surface": re.compile(r"평가|배점|적격\s*심사|신인도|정량"),
    "form_surface": re.compile(r"서식|양식|별지|작성\s*(?:요령|방법)"),
    "single_surface": re.compile(r"단일|1\s*건|한\s*건|건당"),
    "aggregate_surface": re.compile(r"합계|합산|누계|누적|총액|총\s*실적"),
}


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


def amount_relation(text: str, estimate: Any) -> tuple[str, str, int, int]:
    """Return source-only monetary morphology, never a v3 semantic decision."""
    surfaces = [match.group(0) for match in MONEY_PATTERN.finditer(text)]
    values = [value for surface in surfaces if (value := parse_amount_won(surface)) is not None]
    if not isinstance(estimate, (int, float)) or isinstance(estimate, bool) or estimate <= 0:
        return "missing_estimate", "missing_estimate", len(surfaces), len(values)
    if not values:
        return "no_parsed_amount", "no_parsed_amount", len(surfaces), 0
    above = [value > float(estimate) for value in values]
    if all(above):
        relation = "all_gt_estimate"
    elif any(above):
        relation = "mixed_le_and_gt_estimate"
    else:
        relation = "all_le_estimate"
    maximum_ratio = max(values) / float(estimate)
    if maximum_ratio < 0.5:
        band = "lt_0.5"
    elif maximum_ratio < 1.0:
        band = "0.5_to_lt_1.0"
    elif maximum_ratio == 1.0:
        band = "eq_1.0"
    elif maximum_ratio < 1.5:
        band = "gt_1.0_to_lt_1.5"
    else:
        band = "ge_1.5"
    return relation, band, len(surfaces), len(values)


def summarize_records(records: Iterable[NoticeRecord]) -> dict[str, Any]:
    record_count = 0
    document_count = 0
    candidate_count = 0
    money_surface_count = 0
    parsed_money_surface_count = 0
    notice_features: Counter[str] = Counter()
    candidate_features: Counter[str] = Counter()
    categorical = {
        "candidate_document_type": Counter(),
        "candidate_amount_relation": Counter(),
        "candidate_max_amount_ratio_band": Counter(),
    }
    active_ids: dict[str, list[str]] = defaultdict(list)

    for record in records:
        record_count += 1
        document_count += len(record.documents)
        view = build_v3_monetary_view(record.raw)
        if len(view["document_coverage"]) != len(record.documents):
            raise ValueError(f"{record.notice_id}: incomplete v3 document scan")
        candidates = list(view["candidates"])
        candidate_count += len(candidates)
        per_notice: set[str] = set()
        if candidates:
            per_notice.add("candidate_route")
        if len(candidates) > 1:
            per_notice.add("multi_candidate_route")
        if any(candidate.document_type != "공고문" for candidate in candidates):
            per_notice.add("attachment_candidate_route")

        estimate = record.metadata.get("입찰추정가격")
        for candidate in candidates:
            categorical["candidate_document_type"][candidate.document_type] += 1
            for feature, pattern in MORPHOLOGY_PATTERNS.items():
                if pattern.search(candidate.text):
                    candidate_features[feature] += 1
                    per_notice.add(f"any_{feature}")
            relation, band, surfaces, parsed = amount_relation(candidate.text, estimate)
            categorical["candidate_amount_relation"][relation] += 1
            categorical["candidate_max_amount_ratio_band"][band] += 1
            money_surface_count += surfaces
            parsed_money_surface_count += parsed
            if relation in {"all_gt_estimate", "mixed_le_and_gt_estimate"}:
                candidate_features["contains_amount_gt_estimate"] += 1
                per_notice.add("any_candidate_amount_gt_estimate")
            if (
                MORPHOLOGY_PATTERNS["aggregate_surface"].search(candidate.text)
                and not MORPHOLOGY_PATTERNS["single_surface"].search(candidate.text)
            ):
                candidate_features["aggregate_without_single_surface"] += 1
                per_notice.add("any_aggregate_without_single_surface")
            if (
                MORPHOLOGY_PATTERNS["qualification_surface"].search(candidate.text)
                and MORPHOLOGY_PATTERNS["form_surface"].search(candidate.text)
            ):
                candidate_features["qualification_and_form_surface"] += 1
                per_notice.add("any_qualification_and_form_surface")

        for feature in per_notice:
            notice_features[feature] += 1
            active_ids[feature].append(record.notice_id)

    if not record_count:
        raise ValueError("cannot audit an empty cohort")
    return {
        "records": record_count,
        "documents": document_count,
        "candidates": candidate_count,
        "money_surfaces": money_surface_count,
        "parsed_money_surfaces": parsed_money_surface_count,
        "notice_feature_counts": dict(notice_features),
        "candidate_feature_counts": dict(candidate_features),
        "categorical_counts": {
            name: dict(counter) for name, counter in categorical.items()
        },
        "active_ids": active_ids,
    }


def _rate_comparison(
    dev_counts: Mapping[str, int], population_counts: Mapping[str, int],
    dev_denominator: int, population_denominator: int,
    *, difference_gate: float, risk_ratio_low: float, risk_ratio_high: float,
) -> dict[str, dict[str, Any]]:
    result = {}
    for feature in sorted(set(dev_counts) | set(population_counts)):
        dev_rate = dev_counts.get(feature, 0) / dev_denominator if dev_denominator else 0.0
        population_rate = (
            population_counts.get(feature, 0) / population_denominator
            if population_denominator else 0.0
        )
        ratio = dev_rate / population_rate if population_rate else None
        large = abs(dev_rate - population_rate) >= difference_gate
        if ratio is None:
            large = large or dev_rate > 0
        else:
            large = large or ratio < risk_ratio_low or ratio > risk_ratio_high
        result[feature] = {
            "dev_count": dev_counts.get(feature, 0),
            "dev_denominator": dev_denominator,
            "dev_rate": dev_rate,
            "population_count": population_counts.get(feature, 0),
            "population_denominator": population_denominator,
            "population_rate": population_rate,
            "rate_difference_dev_minus_population": dev_rate - population_rate,
            "risk_ratio_dev_over_population": ratio,
            "large_shift": large,
        }
    return result


def _categorical_comparison(
    dev_counts: Mapping[str, int], population_counts: Mapping[str, int],
    dev_denominator: int, population_denominator: int,
) -> dict[str, Any]:
    keys = sorted(set(dev_counts) | set(population_counts))
    dev = {
        key: dev_counts.get(key, 0) / dev_denominator if dev_denominator else 0.0
        for key in keys
    }
    population = {
        key: population_counts.get(key, 0) / population_denominator
        if population_denominator else 0.0
        for key in keys
    }
    return {
        "dev": dev,
        "population": population,
        "total_variation": 0.5 * sum(abs(dev[key] - population[key]) for key in keys),
    }


def summarize_dev_observations(path: Path) -> dict[str, Any]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    role = Counter()
    basis = Counter()
    mandatory = Counter()
    triples = Counter()
    qualification_notice_ids: set[str] = set()
    aggregate_qualification_notice_ids: set[str] = set()
    valid = 0
    for notice in rows:
        diagnostic = notice.get("diagnostic") or {}
        valid += int(diagnostic.get("valid") is True)
        for observation in diagnostic.get("observations") or []:
            role_value = str(observation.get("role"))
            basis_value = str(observation.get("requirement_basis"))
            mandatory_value = str(observation.get("mandatory"))
            role[role_value] += 1
            basis[basis_value] += 1
            mandatory[mandatory_value] += 1
            triples[f"{role_value}|{basis_value}|{mandatory_value}"] += 1
            if role_value == "BID_QUALIFICATION" and mandatory_value == "YES":
                qualification_notice_ids.add(str(notice["id"]))
                if basis_value == "AGGREGATE":
                    aggregate_qualification_notice_ids.add(str(notice["id"]))
    return {
        "notices": len(rows),
        "valid_diagnostics": valid,
        "observations": sum(role.values()),
        "role_counts": dict(role),
        "basis_counts": dict(basis),
        "mandatory_counts": dict(mandatory),
        "role_basis_mandatory_counts": dict(triples),
        "qualification_notice_count": len(qualification_notice_ids),
        "aggregate_qualification_notice_count": len(aggregate_qualification_notice_ids),
        "aggregate_qualification_notice_ids": sorted(aggregate_qualification_notice_ids),
    }


class V3PopulationMorphologyAudit:
    def __init__(self, config: CleanExperimentConfig) -> None:
        self.config = config
        self.root = config.path.parents[2]
        self.output_dir = config.output_dir.resolve()
        policy = config.raw["v3_population_morphology_audit"]
        self.population_path = self.root / policy["population_input_path"]
        self.observations_path = self.root / policy["dev_observations_path"]
        self.basis_report_path = self.root / policy["basis_replay_report_path"]
        self.difference_gate = float(policy["large_shift_rate_difference"])
        self.rr_low = float(policy["large_shift_risk_ratio_low"])
        self.rr_high = float(policy["large_shift_risk_ratio_high"])
        self.sample_size = int(policy["sample_ids_per_shifted_feature"])

    def run(self) -> dict[str, Any]:
        started = time.perf_counter()
        manifest = compare_manifests(self.config.path, self.root)
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")
        for path in (self.population_path, self.observations_path, self.basis_report_path):
            if not path.is_file():
                raise FileNotFoundError(path)
        dev = summarize_records(load_notice_records(self.config.input_path))
        population = summarize_records(load_notice_records(self.population_path))
        notice_rates = _rate_comparison(
            dev["notice_feature_counts"], population["notice_feature_counts"],
            dev["records"], population["records"],
            difference_gate=self.difference_gate,
            risk_ratio_low=self.rr_low, risk_ratio_high=self.rr_high,
        )
        candidate_rates = _rate_comparison(
            dev["candidate_feature_counts"], population["candidate_feature_counts"],
            dev["candidates"], population["candidates"],
            difference_gate=self.difference_gate,
            risk_ratio_low=self.rr_low, risk_ratio_high=self.rr_high,
        )
        categorical = {
            name: _categorical_comparison(
                dev["categorical_counts"][name], population["categorical_counts"][name],
                dev["candidates"], population["candidates"],
            )
            for name in dev["categorical_counts"]
        }
        shifted_notice_features = [
            name for name, value in notice_rates.items() if value["large_shift"]
        ]
        samples = {
            feature: {
                "dev_active": _stable_ids(dev["active_ids"].get(feature, []), self.sample_size),
                "population_active": _stable_ids(
                    population["active_ids"].get(feature, []), self.sample_size,
                ),
            }
            for feature in shifted_notice_features
        }
        view_path = Path(inspect.getsourcefile(build_v3_monetary_view) or "")
        basis_report = json.loads(self.basis_report_path.read_text(encoding="utf-8"))
        report = {
            "status": (
                "PASS" if dev["records"] == 200 and population["records"] == 20_000
                else "FAIL"
            ),
            "mode": "label-free-v3-source-view-population-morphology",
            "inputs": {
                "dev": {"path": str(self.config.input_path), "sha256": _sha256(self.config.input_path)},
                "population": {
                    "path": str(self.population_path), "sha256": _sha256(self.population_path),
                },
                "dev_observations": {
                    "path": str(self.observations_path), "sha256": _sha256(self.observations_path),
                },
                "basis_replay_report": {
                    "path": str(self.basis_report_path), "sha256": _sha256(self.basis_report_path),
                },
                "view_module": {"path": str(view_path), "sha256": _sha256(view_path)},
            },
            "morphology_patterns": {
                name: pattern.pattern for name, pattern in MORPHOLOGY_PATTERNS.items()
            },
            "dev": {key: value for key, value in dev.items() if key != "active_ids"},
            "population": {
                key: value for key, value in population.items() if key != "active_ids"
            },
            "comparison": {
                "notice_feature_rates": notice_rates,
                "candidate_feature_rates": candidate_rates,
                "candidate_categorical": categorical,
            },
            "large_shift_notice_features": shifted_notice_features,
            "hash_selected_sample_ids": samples,
            "dev_stored_observations": summarize_dev_observations(self.observations_path),
            "basis_replay": {
                "status": basis_report.get("status"),
                "calls": basis_report.get("calls"),
                "v3_changes": basis_report.get("v3_changes"),
            },
            "calls": {"llm": 0, "embedding": 0},
            "final_prediction": False,
            "manifest_diff": manifest,
            "runtime_seconds": time.perf_counter() - started,
            "limitations": [
                "The 20,000-record population has no labels; rates are not accuracy or F1.",
                "Morphology patterns are descriptive lexical strata, not legal-role classifiers.",
                "Candidate monetary comparisons are upper bounds before amount-role validation.",
                "Dev Gemma observations have no population counterpart because no paid calls are made.",
            ],
        }
        self.output_dir.mkdir(parents=True, exist_ok=True)
        atomic_json(self.output_dir / "manifest.snapshot.json", self.config.raw)
        atomic_json(self.output_dir / "audit_report.json", report)
        return report


__all__ = [
    "MORPHOLOGY_PATTERNS",
    "V3PopulationMorphologyAudit",
    "amount_relation",
    "summarize_dev_observations",
    "summarize_records",
]
