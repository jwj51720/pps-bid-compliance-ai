"""Label-blind population funnel audit for frozen deterministic item owners."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import importlib
from pathlib import Path
import time
from typing import Any, Mapping, Sequence

from .config import CleanExperimentConfig
from .preflight import compare_manifests
from .reference.frozen import FrozenL41Reference
from .runtime.openrouter import atomic_json


def compare_binary_rates(
    dev_counts: Mapping[str, int], population_counts: Mapping[str, int],
    dev_size: int, population_size: int,
) -> dict[str, dict[str, Any]]:
    result = {}
    for name in sorted(set(dev_counts) | set(population_counts)):
        dev_rate = dev_counts.get(name, 0) / dev_size
        population_rate = population_counts.get(name, 0) / population_size
        risk_ratio = dev_rate / population_rate if population_rate else None
        result[name] = {
            "dev_count": dev_counts.get(name, 0),
            "dev_rate": dev_rate,
            "population_count": population_counts.get(name, 0),
            "population_rate": population_rate,
            "rate_difference_dev_minus_population": dev_rate - population_rate,
            "risk_ratio_dev_over_population": risk_ratio,
        }
    return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_ids(ids: Sequence[str], limit: int) -> list[str]:
    return sorted(set(ids), key=lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest())[:limit]


class PythonOwnerPopulationAudit:
    def __init__(self, config: CleanExperimentConfig) -> None:
        self.config = config
        self.root = config.path.parents[2]
        self.output_dir = config.output_dir.resolve()
        policy = config.raw["python_owner_population_funnel_audit"]
        self.population_path = self.root / policy["population_input_path"]
        self.rate_threshold = float(policy["large_shift_rate_difference"])
        self.rr_low = float(policy["large_shift_risk_ratio_low"])
        self.rr_high = float(policy["large_shift_risk_ratio_high"])
        self.sample_size = int(policy["sample_ids_per_shifted_predicate"])

    @staticmethod
    def _features(
        record: Mapping[str, Any], builder: Any, scanner: Any, modules: Mapping[str, Any],
    ) -> dict[str, bool]:
        meta = record.get("meta") or {}
        estimate = meta.get("입찰추정가격")
        amount_ok = isinstance(estimate, (int, float)) and not isinstance(estimate, bool)
        work_type = str(meta.get("업무구분") or "")
        contract_method = str(meta.get("계약방법") or "")
        award_method = str(meta.get("낙찰방법") or "")
        clause = str(meta.get("조항호내용") or "")
        organizer_broad_scope = clause == "[판로지원법 시행령] 중기업,소기업,소상공인 제한"
        organizer_small_scope = clause == "[판로지원법 시행령] 소기업,소상공인제한"
        facts = builder.build(record)
        exact_product = scanner.build(record)
        r2 = modules["r2"].predict(record, facts, "meta_or_document_exact", exact_product)
        scope = modules["scope"].scope_hits_v2(record)
        complete = modules["scope"].complete_observation(record)
        empty_ranking = {"id": record["id"], "query": "", "ranked": []}
        product = modules["v14"].hybrid_competitive(
            record, empty_ranking, builder, scanner,
        )
        no_bge_competitive = bool(product["confirmed"] or product["lexical_codes"])
        explicit_exception = modules["v16"].explicit_exception(
            record, compact=True, allow_authority=True,
        )

        direct_hits = modules["v12"].direct_hard_hits_same_line(record)
        f3 = facts["facts"]["F3"]
        meta_noncatalog = any(
            row.get("catalog_listed") is False and row.get("code")
            for row in f3.get("meta_items") or []
        )
        catalog_codes = [
            code for hit in direct_hits for code in modules["v12"].digit_runs(hit)
            if code in builder.catalog
        ]
        amount_failure = any(
            modules["v12"].recognized_amount_failure(
                (builder.catalog[code].get("특이사항") or "").strip() or None,
                estimate,
            )
            for code in catalog_codes
        )
        v12_aux = meta_noncatalog or amount_failure

        v13_product = modules["v13"].catalog_notice_exact(exact_product, estimate)
        v13_scope = bool(modules["v13"].small_scope_hits_v3(record))
        small_quote = "수의" in contract_method and (
            "소액수의" in award_method or "견적" in award_method
        )
        v13_special = modules["v13"].has_v13_special_exception(record)

        v14_scope = modules["v14"].scope_hits(record)
        v14_scoped = bool(v14_scope["broad"] or v14_scope["small"])
        v14_amount = bool(
            amount_ok and "공사" not in work_type
            and estimate >= modules["v14"].amount_cap(record)
        )
        v14_exception = any(
            term in modules["baseline"].full_text(dict(record))
            for term in modules["v14"].EXPLICIT_EXCEPTION_TERMS
        )

        nonconstruction = "공사" not in work_type
        no_scope = not scope["broad"] and not scope["small"]
        limited_complete = nonconstruction and contract_method == "제한경쟁" and complete
        cross_competitive = bool(r2["v10"] or r2["v11"])
        v16_band = amount_ok and 100_000_000 <= estimate < 230_000_000
        v18_band = amount_ok and estimate < 100_000_000
        v16_pre = bool(limited_complete and no_scope and v16_band)
        v18_pre = bool(limited_complete and no_scope and v18_band)
        absence_survives = not no_bge_competitive and not cross_competitive and not explicit_exception

        v17_pre = bool(
            amount_ok and estimate < 100_000_000 and nonconstruction
            and scope["broad"] and not scope["small"]
        )
        has_attachments = any(doc.get("type") != "공고문" for doc in record.get("docs") or [])
        return {
            "amount_lt_100m": bool(amount_ok and estimate < 100_000_000),
            "amount_100m_to_230m": bool(amount_ok and 100_000_000 <= estimate < 230_000_000),
            "amount_ge_230m": bool(amount_ok and estimate >= 230_000_000),
            "small_quote": small_quote,
            "has_attachments": has_attachments,
            "complete_observation": bool(complete),
            "scope_broad": bool(scope["broad"]),
            "scope_small": bool(scope["small"]),
            "organizer_clause_broad_scope": organizer_broad_scope,
            "organizer_clause_small_scope": organizer_small_scope,
            "scope_detector_misses_organizer_broad": bool(
                organizer_broad_scope and not scope["broad"]
            ),
            "scope_detector_misses_organizer_small": bool(
                organizer_small_scope and not scope["small"]
            ),
            "product_confirmed_without_bge": no_bge_competitive,
            "r2_initial_v10": bool(r2["v10"]),
            "r2_initial_v11": bool(r2["v11"]),
            "v12_direct_same_line": bool(direct_hits),
            "v12_aux_nonapplicable": bool(v12_aux),
            "v12_candidate": bool(direct_hits and v12_aux),
            "v13_product_exact": bool(v13_product),
            "v13_small_scope": v13_scope,
            "v13_pre_exception": bool(v13_product and v13_scope),
            "v13_candidate": bool(v13_product and v13_scope and not small_quote and not v13_special),
            "v13_candidate_conflicts_organizer_broad": bool(
                v13_product and v13_scope and not small_quote and not v13_special
                and organizer_broad_scope
            ),
            "v14_amount_scope_pre": bool(v14_amount and v14_scoped),
            "v14_survives_no_bge": bool(
                v14_amount and v14_scoped and not no_bge_competitive and not v14_exception
            ),
            "v16_absence_pre_product": v16_pre,
            "v16_survives_no_bge": bool(v16_pre and absence_survives),
            "v16_survivor_conflicts_organizer_broad": bool(
                v16_pre and absence_survives and organizer_broad_scope
            ),
            "v18_absence_pre_product": v18_pre,
            "v18_survives_no_bge": bool(v18_pre and absence_survives),
            "v18_survivor_conflicts_organizer_small": bool(
                v18_pre and absence_survives and organizer_small_scope
            ),
            "v17_broad_pre_product": v17_pre,
            "v17_survives_no_bge": bool(
                v17_pre and not no_bge_competitive and not cross_competitive
            ),
        }

    def _scan(
        self, path: Path, reference: FrozenL41Reference, modules: Mapping[str, Any],
    ) -> dict[str, Any]:
        records = reference.baseline.iter_records(str(path))
        builder = reference.builder(self.config.data_dir)
        scanner = modules["scanner"].ExactDocumentProductScanner(builder.catalog)
        counts: Counter[str] = Counter()
        positive_ids: dict[str, list[str]] = defaultdict(list)
        record_count = document_count = 0
        for record in records:
            record_count += 1
            document_count += len(record.get("docs") or [])
            features = self._features(record, builder, scanner, modules)
            for name, active in features.items():
                if active:
                    counts[name] += 1
                    positive_ids[name].append(str(record["id"]))
        return {
            "path": str(path.relative_to(self.root)),
            "sha256": _sha256(path),
            "records": record_count,
            "documents": document_count,
            "counts": dict(counts),
            "positive_ids": positive_ids,
        }

    def run(self) -> dict[str, Any]:
        started = time.perf_counter()
        manifest = compare_manifests(self.config.path, self.root)
        if manifest["status"] != "PASS":
            raise ValueError("manifest policy diff failed")
        reference = FrozenL41Reference(
            self.config.reference_zip, self.config.reference_zip_sha256,
        )
        modules = {
            "baseline": reference.baseline,
            "r2": importlib.import_module("dev.run_r2_deterministic_absence_experiment"),
            "scanner": importlib.import_module("dev.r2_exact_product_context"),
            "scope": importlib.import_module("dev.run_sme_amount_router_experiment"),
            "v12": importlib.import_module("dev.run_v12_general_direct_production_experiment"),
            "v13": importlib.import_module("dev.run_v13_catalog_small_scope_experiment"),
            "v14": importlib.import_module("dev.run_v14_hybrid_sme_limit_experiment"),
            "v16": importlib.import_module("dev.run_v16_v18_absence_experiment"),
        }
        dev = self._scan(self.config.input_path, reference, modules)
        population = self._scan(self.population_path, reference, modules)
        rates = compare_binary_rates(
            dev["counts"], population["counts"], dev["records"], population["records"],
        )
        shifted = []
        samples = {}
        for name, value in rates.items():
            ratio = value["risk_ratio_dev_over_population"]
            large = (
                abs(value["rate_difference_dev_minus_population"]) >= self.rate_threshold
                or ratio is None
                or ratio < self.rr_low
                or ratio > self.rr_high
            )
            value["large_shift"] = large
            if large:
                shifted.append(name)
                samples[name] = {
                    "dev_active": _stable_ids(dev["positive_ids"].get(name, []), self.sample_size),
                    "population_active": _stable_ids(
                        population["positive_ids"].get(name, []), self.sample_size,
                    ),
                }
        report = {
            "status": "PASS" if dev["records"] == 200 and population["records"] == 20000 else "FAIL",
            "mode": "label-blind-frozen-python-owner-funnel",
            "reference_zip_sha256": self.config.reference_zip_sha256,
            "reference_script_sha256": reference.script_sha256,
            "dev": {key: value for key, value in dev.items() if key != "positive_ids"},
            "population": {key: value for key, value in population.items() if key != "positive_ids"},
            "rates": rates,
            "large_shift_predicates": shifted,
            "hash_selected_sample_ids": samples,
            "llm_calls": 0,
            "embedding_calls": 0,
            "final_prediction": False,
            "runtime_seconds": time.perf_counter() - started,
            "manifest_diff": manifest,
            "limitations": [
                "Unlabeled population rates are not accuracy or F1 estimates.",
                "BGE and Gemma stages are not run; survives_no_bge is an upper-bound funnel stage.",
                "Frozen predicates are measured, not endorsed as organizer truth conditions.",
            ],
        }
        self.output_dir.mkdir(parents=True, exist_ok=True)
        atomic_json(self.output_dir / "audit_report.json", report)
        return report
