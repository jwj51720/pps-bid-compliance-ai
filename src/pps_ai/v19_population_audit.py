"""Label-free v19 source morphology and stored-owner utility audit."""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
import hashlib
import inspect
import json
from pathlib import Path
import re
import time
from typing import Any, Iterable, Mapping, Sequence

from .config import CleanExperimentConfig
from .domain import NoticeRecord
from .ingest import load_notice_records
from .owner_stage_attribution import stage_attribution
from .preflight import compare_manifests
from .runtime.openrouter import atomic_json
from .views.v19_requirements import build_v19_requirement_view


MORPHOLOGY_PATTERNS: dict[str, re.Pattern[str]] = {
    "external_issuer_surface": re.compile(
        r"제조사|제조업체|공급사|공급업체|기술\s*지원사|총판|대리점"
    ),
    "supply_or_tech_surface": re.compile(
        r"물품\s*공급|공급\s*확약|기술\s*지원|기술지원\s*확약"
    ),
    "bid_submission_surface": re.compile(
        r"입찰\s*(?:서|참가|제출)|제안서|제출\s*서류|마감일"
    ),
    "post_award_surface": re.compile(
        r"낙찰|계약\s*(?:체결|시|후)|착수|이행\s*단계"
    ),
    "self_promise_surface": re.compile(
        r"청렴|보안|안전|서약|각서|근로|인권|개인정보|준수"
    ),
    "form_surface": re.compile(r"서식|양식|별지|붙임"),
    "status_or_authenticity_surface": re.compile(
        r"정품|인증|제조자\s*증명|대리점\s*증명|공급\s*증명"
    ),
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


def morphology_features(text: str) -> set[str]:
    features = {
        name for name, pattern in MORPHOLOGY_PATTERNS.items() if pattern.search(text)
    }
    external_supply = {
        "external_issuer_surface", "supply_or_tech_surface",
    } <= features
    if external_supply:
        features.add("external_and_supply_surface")
        if "bid_submission_surface" in features:
            features.add("external_supply_and_bid_surface")
    if (
        {"self_promise_surface", "form_surface"} & features
        and not external_supply
    ):
        features.add("self_or_form_without_external_supply")
    if "post_award_surface" in features and "bid_submission_surface" not in features:
        features.add("post_award_without_bid_surface")
    return features


def _candidate_count_band(count: int) -> str:
    if count == 0:
        return "0"
    if count <= 3:
        return str(count)
    return "4_plus"


def summarize_records(records: Iterable[NoticeRecord]) -> dict[str, Any]:
    record_count = 0
    document_count = 0
    candidate_count = 0
    notice_features: Counter[str] = Counter()
    candidate_features: Counter[str] = Counter()
    document_types: Counter[str] = Counter()
    candidate_count_bands: Counter[str] = Counter()
    active_ids: dict[str, list[str]] = defaultdict(list)
    for record in records:
        record_count += 1
        document_count += len(record.documents)
        view = build_v19_requirement_view(record.raw)
        if len(view["document_coverage"]) != len(record.documents):
            raise ValueError(f"{record.notice_id}: incomplete v19 document scan")
        candidates = list(view["candidates"])
        candidate_count += len(candidates)
        candidate_count_bands[_candidate_count_band(len(candidates))] += 1
        per_notice: set[str] = set()
        if candidates:
            per_notice.add("candidate_route")
        if len(candidates) > 1:
            per_notice.add("multi_candidate_route")
        if any(candidate.document_type != "공고문" for candidate in candidates):
            per_notice.add("attachment_candidate_route")
        for candidate in candidates:
            document_types[candidate.document_type] += 1
            for feature in morphology_features(candidate.text):
                candidate_features[feature] += 1
                per_notice.add(f"any_{feature}")
        for feature in per_notice:
            notice_features[feature] += 1
            active_ids[feature].append(record.notice_id)
    if not record_count:
        raise ValueError("cannot audit an empty cohort")
    return {
        "records": record_count,
        "documents": document_count,
        "candidates": candidate_count,
        "notice_feature_counts": dict(notice_features),
        "candidate_feature_counts": dict(candidate_features),
        "categorical_counts": {
            "candidate_document_type": dict(document_types),
            "candidate_count_band": dict(candidate_count_bands),
        },
        "active_ids": active_ids,
    }


def _compare_rates(
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


def _compare_categories(
    dev_counts: Mapping[str, int], population_counts: Mapping[str, int],
    dev_denominator: int, population_denominator: int,
) -> dict[str, Any]:
    keys = sorted(set(dev_counts) | set(population_counts))
    dev = {key: dev_counts.get(key, 0) / dev_denominator for key in keys}
    population = {
        key: population_counts.get(key, 0) / population_denominator for key in keys
    }
    return {
        "dev": dev,
        "population": population,
        "total_variation": 0.5 * sum(abs(dev[key] - population[key]) for key in keys),
    }


def summarize_dev_observations(path: Path) -> dict[str, Any]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    roles = Counter()
    kinds = Counter()
    pairs = Counter()
    fallback_reasons = Counter()
    positive_notices: set[str] = set()
    observation_count = 0
    for notice in rows:
        diagnostic = notice.get("diagnostic") or {}
        if diagnostic.get("fallback"):
            fallback_reasons[str(diagnostic.get("reason") or "<UNKNOWN>")] += 1
        for observation in diagnostic.get("observations") or []:
            observation_count += 1
            role = str(observation.get("requirement_role"))
            kind = str(observation.get("document_kind"))
            roles[role] += 1
            kinds[kind] += 1
            pairs[f"{role}|{kind}"] += 1
            if observation.get("positive_predicate") is True:
                positive_notices.add(str(notice["id"]))
    return {
        "notices": len(rows),
        "observations": observation_count,
        "role_counts": dict(roles),
        "kind_counts": dict(kinds),
        "role_kind_counts": dict(pairs),
        "positive_predicate_notice_count": len(positive_notices),
        "positive_predicate_notice_ids": sorted(positive_notices),
        "fallback_reason_counts": dict(fallback_reasons),
    }


def _read_item(path: Path, item: str) -> dict[str, int]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {str(row["id"]): int(row[item]) for row in csv.DictReader(handle)}


def _usage(path: Path) -> tuple[int, int]:
    value = json.loads(path.read_text(encoding="utf-8"))
    usage = value.get("usage") or {}
    return int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0)


class V19PopulationMorphologyAudit:
    def __init__(self, config: CleanExperimentConfig) -> None:
        self.config = config
        self.root = config.path.parents[2]
        self.output_dir = config.output_dir.resolve()
        policy = config.raw["v19_population_morphology_audit"]
        self.population_path = self.root / policy["population_input_path"]
        self.observations_path = self.root / policy["dev_observations_path"]
        self.native_response_dir = self.root / policy["native_response_dir"]
        self.base_response_dir = self.root / policy["base_b_response_dir"]
        self.native_report_path = self.root / policy["native_run_report_path"]
        self.base_submission_path = self.root / policy["base_submission_path"]
        self.final_submission_path = self.root / policy["final_submission_path"]
        self.difference_gate = float(policy["large_shift_rate_difference"])
        self.rr_low = float(policy["large_shift_risk_ratio_low"])
        self.rr_high = float(policy["large_shift_risk_ratio_high"])
        self.sample_size = int(policy["sample_ids_per_shifted_feature"])
        self.test_records = int(policy["test_record_count"])

    def run(self) -> dict[str, Any]:
        started = time.perf_counter()
        manifest = compare_manifests(self.config.path, self.root)
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")
        required = (
            self.population_path, self.observations_path, self.native_report_path,
            self.base_submission_path, self.final_submission_path,
        )
        if any(not path.is_file() for path in required):
            raise FileNotFoundError("required v19 audit input is missing")

        dev = summarize_records(load_notice_records(self.config.input_path))
        population = summarize_records(load_notice_records(self.population_path))
        notice_rates = _compare_rates(
            dev["notice_feature_counts"], population["notice_feature_counts"],
            dev["records"], population["records"],
            difference_gate=self.difference_gate,
            risk_ratio_low=self.rr_low, risk_ratio_high=self.rr_high,
        )
        candidate_rates = _compare_rates(
            dev["candidate_feature_counts"], population["candidate_feature_counts"],
            dev["candidates"], population["candidates"],
            difference_gate=self.difference_gate,
            risk_ratio_low=self.rr_low, risk_ratio_high=self.rr_high,
        )
        categorical = {
            "candidate_document_type": _compare_categories(
                dev["categorical_counts"]["candidate_document_type"],
                population["categorical_counts"]["candidate_document_type"],
                dev["candidates"], population["candidates"],
            ),
            "candidate_count_band": _compare_categories(
                dev["categorical_counts"]["candidate_count_band"],
                population["categorical_counts"]["candidate_count_band"],
                dev["records"], population["records"],
            ),
        }
        shifted = [name for name, value in notice_rates.items() if value["large_shift"]]
        samples = {
            feature: {
                "dev_active": _stable_ids(dev["active_ids"].get(feature, []), self.sample_size),
                "population_active": _stable_ids(
                    population["active_ids"].get(feature, []), self.sample_size,
                ),
            }
            for feature in shifted
        }

        base = _read_item(self.base_submission_path, "v19")
        final = _read_item(self.final_submission_path, "v19")
        truth = _read_item(self.config.labels_path, "v19")
        owner_transition = stage_attribution(base, final, truth)

        candidate_ids = set(dev["active_ids"].get("candidate_route", []))
        native_prompt = native_completion = base_prompt = base_completion = 0
        for notice_id in candidate_ids:
            native_paths = sorted(self.native_response_dir.glob(f"{notice_id}__p*.json"))
            if len(native_paths) != 1:
                raise ValueError(f"{notice_id}: native response coverage differs")
            p, c = _usage(native_paths[0])
            native_prompt += p
            native_completion += c
            p, c = _usage(self.base_response_dir / f"{notice_id}.json")
            base_prompt += p
            base_completion += c
        route_rate = population["notice_feature_counts"].get("candidate_route", 0) / population["records"]
        token_comparison = {
            "candidate_tasks": len(candidate_ids),
            "native": {"prompt": native_prompt, "completion": native_completion,
                       "total": native_prompt + native_completion},
            "base_B_same_notices": {"prompt": base_prompt, "completion": base_completion,
                                    "total": base_prompt + base_completion},
            "native_minus_base_B": {
                "prompt": native_prompt - base_prompt,
                "completion": native_completion - base_completion,
                "total": native_prompt + native_completion - base_prompt - base_completion,
            },
            "expected_test_native_tasks": route_rate * self.test_records,
            "expected_test_B_tasks": (1 - route_rate) * self.test_records,
            "total_v19_owner_tasks": self.test_records,
            "native_replaces_B_not_adds_call": True,
        }

        view_path = Path(inspect.getsourcefile(build_v19_requirement_view) or "")
        report = {
            "status": (
                "PASS" if dev["records"] == 200 and population["records"] == 20_000
                and len(candidate_ids) == 165 else "FAIL"
            ),
            "mode": "label-free-v19-population-morphology-and-stored-owner-utility",
            "inputs": {
                "dev": {"path": str(self.config.input_path), "sha256": _sha256(self.config.input_path)},
                "population": {"path": str(self.population_path), "sha256": _sha256(self.population_path)},
                "observations": {"path": str(self.observations_path), "sha256": _sha256(self.observations_path)},
                "native_report": {"path": str(self.native_report_path), "sha256": _sha256(self.native_report_path)},
                "base_submission": {"path": str(self.base_submission_path), "sha256": _sha256(self.base_submission_path)},
                "final_submission": {"path": str(self.final_submission_path), "sha256": _sha256(self.final_submission_path)},
                "view_module": {"path": str(view_path), "sha256": _sha256(view_path)},
            },
            "morphology_patterns": {
                name: pattern.pattern for name, pattern in MORPHOLOGY_PATTERNS.items()
            },
            "dev": {key: value for key, value in dev.items() if key != "active_ids"},
            "population": {key: value for key, value in population.items() if key != "active_ids"},
            "comparison": {
                "notice_feature_rates": notice_rates,
                "candidate_feature_rates": candidate_rates,
                "categorical": categorical,
            },
            "large_shift_notice_features": shifted,
            "hash_selected_sample_ids": samples,
            "dev_stored_observations": summarize_dev_observations(self.observations_path),
            "base_to_native_owner_transition": owner_transition,
            "stored_token_comparison": token_comparison,
            "calls": {"llm": 0, "embedding": 0},
            "final_prediction": False,
            "manifest_diff": manifest,
            "runtime_seconds": time.perf_counter() - started,
            "limitations": [
                "Unlabeled population morphology is not accuracy, precision, recall, or F1.",
                "Lexical morphology features are source-review strata, not v19 decisions.",
                "Stored OpenRouter token counts are not evaluator vLLM wall-time measurements.",
                "Dev owner transitions are adaptive-development evidence.",
            ],
        }
        self.output_dir.mkdir(parents=True, exist_ok=True)
        atomic_json(self.output_dir / "manifest.snapshot.json", self.config.raw)
        atomic_json(self.output_dir / "audit_report.json", report)
        return report


__all__ = [
    "MORPHOLOGY_PATTERNS",
    "V19PopulationMorphologyAudit",
    "morphology_features",
    "summarize_dev_observations",
    "summarize_records",
]
