"""Label-free input and specialist-route shift audit."""

from __future__ import annotations

from collections import Counter
import math
from statistics import fmean
from typing import Any, Iterable, Mapping

from .domain import NoticeRecord
from .views.v3_monetary import build_v3_monetary_view
from .views.v19_requirements import build_v19_requirement_view


CATEGORICAL_META = {
    "contract_law": "적용계약법",
    "work_type": "업무구분",
    "contract_method": "계약방법",
    "award_method": "낙찰방법",
}


def _category(value: Any) -> str:
    if value is None or value == "":
        return "<MISSING>"
    return str(value)


def price_band(value: Any) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return "<MISSING>"
    amount = float(value)
    boundaries = (
        (100_000_000, "lt_100m"),
        (150_000_000, "100m_to_lt_150m"),
        (230_000_000, "150m_to_lt_230m"),
        (330_000_000, "230m_to_lt_330m"),
        (350_000_000, "330m_to_lt_350m"),
        (500_000_000, "350m_to_lt_500m"),
    )
    for boundary, label in boundaries:
        if amount < boundary:
            return label
    return "ge_500m"


def summarize_records(records: Iterable[NoticeRecord]) -> dict[str, Any]:
    categories = {name: Counter() for name in CATEGORICAL_META}
    categories.update({
        "estimated_price_band": Counter(),
        "document_type_signature": Counter(),
    })
    continuous = {"document_count": [], "document_chars": [],
                  "v3_candidate_count": [], "v19_candidate_count": []}
    binary = {"attachment_presence": 0, "v3_candidate_route": 0,
              "v19_candidate_route": 0}
    record_count = document_count = 0
    for record in records:
        record_count += 1
        document_count += len(record.documents)
        for name, key in CATEGORICAL_META.items():
            categories[name][_category(record.metadata.get(key))] += 1
        categories["estimated_price_band"][price_band(
            record.metadata.get("입찰추정가격")
        )] += 1
        signature = " > ".join(document.document_type for document in record.documents)
        categories["document_type_signature"][signature] += 1
        chars = sum(len(document.text) for document in record.documents)
        continuous["document_count"].append(float(len(record.documents)))
        continuous["document_chars"].append(float(chars))
        binary["attachment_presence"] += int(len(record.documents) > 1)
        raw = dict(record.raw)
        v3_count = len(build_v3_monetary_view(raw)["candidates"])
        v19_count = len(build_v19_requirement_view(raw)["candidates"])
        continuous["v3_candidate_count"].append(float(v3_count))
        continuous["v19_candidate_count"].append(float(v19_count))
        binary["v3_candidate_route"] += int(v3_count > 0)
        binary["v19_candidate_route"] += int(v19_count > 0)
    if not record_count:
        raise ValueError("cannot audit an empty cohort")
    return {
        "records": record_count,
        "documents": document_count,
        "categorical_counts": {name: dict(counter) for name, counter in categories.items()},
        "continuous_values": continuous,
        "binary_counts": binary,
    }


def _distribution(counts: Mapping[str, int], total: int) -> dict[str, float]:
    return {key: value / total for key, value in sorted(counts.items())}


def _total_variation(left: Mapping[str, float], right: Mapping[str, float]) -> float:
    keys = set(left) | set(right)
    return 0.5 * sum(abs(left.get(key, 0.0) - right.get(key, 0.0)) for key in keys)


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _variance(values: list[float], mean: float) -> float:
    return sum((value - mean) ** 2 for value in values) / len(values)


def compare_cohorts(
    dev: Mapping[str, Any], population: Mapping[str, Any],
    *, rate_difference_gate: float, risk_ratio_low: float, risk_ratio_high: float,
) -> dict[str, Any]:
    dev_n = int(dev["records"])
    population_n = int(population["records"])
    categorical: dict[str, Any] = {}
    for name in dev["categorical_counts"]:
        left = _distribution(dev["categorical_counts"][name], dev_n)
        right = _distribution(population["categorical_counts"][name], population_n)
        categorical[name] = {
            "dev": left, "population": right,
            "total_variation": _total_variation(left, right),
        }
    continuous: dict[str, Any] = {}
    for name, dev_values in dev["continuous_values"].items():
        population_values = population["continuous_values"][name]
        dev_mean = fmean(dev_values)
        population_mean = fmean(population_values)
        pooled_sd = math.sqrt(
            (_variance(dev_values, dev_mean) + _variance(population_values, population_mean)) / 2
        )
        continuous[name] = {
            "dev": {"mean": dev_mean, "median": _quantile(dev_values, 0.5),
                    "p90": _quantile(dev_values, 0.9), "p99": _quantile(dev_values, 0.99)},
            "population": {"mean": population_mean,
                           "median": _quantile(population_values, 0.5),
                           "p90": _quantile(population_values, 0.9),
                           "p99": _quantile(population_values, 0.99)},
            "standardized_mean_difference": (
                (dev_mean - population_mean) / pooled_sd if pooled_sd else 0.0
            ),
        }
    binary: dict[str, Any] = {}
    for name, dev_count in dev["binary_counts"].items():
        population_count = population["binary_counts"][name]
        dev_rate = dev_count / dev_n
        population_rate = population_count / population_n
        ratio = dev_rate / population_rate if population_rate else None
        large = abs(dev_rate - population_rate) >= rate_difference_gate
        if ratio is not None:
            large = large or ratio < risk_ratio_low or ratio > risk_ratio_high
        binary[name] = {
            "dev_count": dev_count, "dev_rate": dev_rate,
            "population_count": population_count, "population_rate": population_rate,
            "difference_percentage_points": 100 * (dev_rate - population_rate),
            "risk_ratio": ratio, "large_shift": large,
        }
    return {"categorical": categorical, "continuous": continuous, "binary": binary}
